import json
import sqlite3
import hashlib
from typing import Dict, Any, Iterable, Optional, Generator, Tuple
import zstandard as zstd


def _zstd_compress_bytes(b: bytes, level: int = 12) -> bytes:
    return zstd.ZstdCompressor(level=level).compress(b)

def _zstd_decompress_bytes(b: bytes) -> bytes:
    return zstd.ZstdDecompressor().decompress(b)

def _to_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def _from_json_bytes(b: bytes) -> Any:
    return json.loads(b.decode("utf-8"))

def _ordered_index_list(cat: Dict[str, Any]) -> Iterable[str]:
    idx = cat.get("index")
    if isinstance(idx, list):
        return idx
    if isinstance(idx, dict):
        return [k for k, _ in sorted(idx.items(), key=lambda kv: kv[1])]
    labels = cat.get("label")
    if isinstance(labels, dict):
        return list(labels.keys())
    return []

def _fingerprint_dimension(dim_name: str, index_list: Iterable[str], labels: Optional[Dict[str, str]]) -> str:
    payload = {"dimension": dim_name, "index": list(index_list), "labels": labels or None}
    return hashlib.sha1(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")).hexdigest()


class JSONStatArchiveDB:
    """
    Single-file JSON-Stat archive using SQLite + Zstd.

    Tables:
      - datasets(table_id TEXT PRIMARY KEY, json_zst BLOB, timestamp TEXT, dim_map_json TEXT)
      - registry(fingerprint TEXT PRIMARY KEY, entry_json_zst BLOB)
    Each dataset JSON is strict JSON-Stat (labels stripped). 'dim_map_json' maps dimension -> registry key.
    """

    def __init__(self, compression_level: int = 12):
        self.level = compression_level

    # ---------- PUBLIC API ----------

    def write(self, db_path: str, tables: Dict[str, Dict[str, Any]]) -> None:
        """
        Write/replace datasets into a single SQLite file.

        Args:
            db_path: path to archive sqlite file (created if missing).
            tables: {
              "table_id": { "data": <json-stat dataset>, "timestamp": "..." },
              ...
            }
        """
        conn = sqlite3.connect(db_path)
        try:
            self._init_schema(conn)

            # use a write transaction (fast + consistent)
            with conn:
                for table_id, payload in tables.items():
                    dataset = payload["data"]
                    timestamp = payload.get("timestamp")

                    compact_ds, dim_map, reg_updates = self._compact_and_registry(dataset)

                    # upsert registry entries
                    for fp, entry in reg_updates.items():
                        self._upsert_registry(conn, fp, entry)

                    json_bytes = _to_json_bytes(compact_ds)
                    comp = _zstd_compress_bytes(json_bytes, level=self.level)
                    dim_map_json = json.dumps(dim_map, separators=(",", ":"))
                    conn.execute(
                        """INSERT INTO datasets(table_id, json_zst, timestamp, dim_map_json)
                           VALUES(?,?,?,?)
                           ON CONFLICT(table_id) DO UPDATE SET
                             json_zst=excluded.json_zst,
                             timestamp=excluded.timestamp,
                             dim_map_json=excluded.dim_map_json""",
                        (table_id, comp, timestamp, dim_map_json),
                    )
        finally:
            conn.close()

    def read(
        self,
        db_path: str,
        table_id: Optional[str] = None,
        with_labels: bool = True,
    ) -> Generator[Tuple[str, Dict[str, Any], Optional[str]], None, None]:
        """
        Iterate datasets from the archive.

        Args:
            db_path: path to sqlite archive
            table_id: if provided, only that table; else iterate all
            with_labels: reattach labels from registry

        Yields:
            (table_id, json_stat_dataset, timestamp)
        """
        conn = sqlite3.connect(db_path)
        try:
            if table_id:
                rows = conn.execute(
                    "SELECT table_id, json_zst, timestamp, dim_map_json FROM datasets WHERE table_id=?",
                    (table_id,),
                )
            else:
                rows = conn.execute(
                    "SELECT table_id, json_zst, timestamp, dim_map_json FROM datasets ORDER BY table_id"
                )

            for tid, json_zst, ts, dim_map_json in rows:
                ds = _from_json_bytes(_zstd_decompress_bytes(json_zst))
                if with_labels and self._looks_like_dataset(ds):
                    dim_map = json.loads(dim_map_json) if dim_map_json else {}
                    ds = self._rehydrate(conn, ds, dim_map)
                yield tid, ds, ts
        finally:
            conn.close()

    # ---------- INTERNALS ----------

    def _init_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS datasets(
                   table_id TEXT PRIMARY KEY,
                   json_zst BLOB NOT NULL,
                   timestamp TEXT,
                   dim_map_json TEXT
               )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS registry(
                   fingerprint TEXT PRIMARY KEY,
                   entry_json_zst BLOB NOT NULL
               )"""
        )

    def _upsert_registry(self, conn: sqlite3.Connection, fp: str, entry: Dict[str, Any]) -> None:
        # Only insert if missing (registry is immutable for a given fp)
        cur = conn.execute("SELECT 1 FROM registry WHERE fingerprint=?", (fp,))
        if cur.fetchone() is None:
            conn.execute(
                "INSERT INTO registry(fingerprint, entry_json_zst) VALUES (?, ?)",
                (fp, _zstd_compress_bytes(_to_json_bytes(entry), level=self.level)),
            )

    def _looks_like_dataset(self, ds: Dict[str, Any]) -> bool:
        return ds.get("class") == "dataset" and isinstance(ds.get("dimension"), dict)

    def _compact_and_registry(
        self, ds: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, str], Dict[str, Dict[str, Any]]]:
        """
        Produce compact dataset (labels stripped) + registry updates.
        Returns (compact_ds, dim_map, registry_updates)
        """
        if not self._looks_like_dataset(ds):
            # Non-dataset (e.g., collection) → store as-is, no registry mapping.
            return ds, {}, {}

        dims = ds["dimension"]
        dim_ids = dims.get("id", [])
        reg_updates: Dict[str, Dict[str, Any]] = {}
        dim_map: Dict[str, str] = {}

        # deep copy
        compact = json.loads(json.dumps(ds))
        c_dims = compact["dimension"]

        for dim_name in dim_ids:
            d = dims.get(dim_name, {})
            cat = d.get("category", {}) or {}
            index_list = list(_ordered_index_list(cat))
            labels = cat.get("label") if isinstance(cat.get("label"), dict) else None

            fp = _fingerprint_dimension(dim_name, index_list, labels)
            dim_map[dim_name] = fp
            if fp not in reg_updates:
                reg_updates[fp] = {
                    "dimension": dim_name,
                    "index": index_list,
                    "labels": labels,  # may be None
                    "dimension_label": d.get("label"),
                }

            # strip labels in the compact dataset
            c_d = c_dims.get(dim_name, {})
            c_cat = c_d.get("category", {}) or {}
            c_cat["index"] = index_list
            if "label" in c_cat:
                del c_cat["label"]
            c_d["category"] = c_cat
            if "label" in c_d:
                del c_d["label"]
            c_dims[dim_name] = c_d

        compact["dimension"] = c_dims
        return compact, dim_map, reg_updates

    def _rehydrate(self, conn: sqlite3.Connection, ds: Dict[str, Any], dim_map: Dict[str, str]) -> Dict[str, Any]:
        out = json.loads(json.dumps(ds))
        dims = out["dimension"]
        dim_ids = dims.get("id", [])

        # prepare statement
        q = "SELECT entry_json_zst FROM registry WHERE fingerprint=?"

        for dim_name in dim_ids:
            fp = dim_map.get(dim_name)
            if not fp:
                continue
            row = conn.execute(q, (fp,)).fetchone()
            if not row:
                continue
            reg = _from_json_bytes(_zstd_decompress_bytes(row[0]))

            d = dims.get(dim_name, {})
            cat = d.get("category", {}) or {}

            stored_index = reg.get("index") or []
            if stored_index:
                cat["index"] = stored_index

            labels = reg.get("labels")
            if labels:
                cat["label"] = labels

            dim_label = reg.get("dimension_label")
            if dim_label:
                d["label"] = dim_label

            d["category"] = cat
            dims[dim_name] = d

        out["dimension"] = dims
        return out