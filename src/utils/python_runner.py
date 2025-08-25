import io
import sys
import traceback
from typing import Dict, Any


def run_python_safely(code: str) -> Dict[str, Any]:
    """
    Minimal sandbox runner. In production: isolate with subprocess, container, time & mem limits.
    Returns {"stdout": str, "error": {"type":, "message":, "trace":}} on failure.
    """
    stdout_capture = io.StringIO()
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout = stdout_capture
    sys.stderr = stdout_capture  # co-mingle
    globals_dict = {"__name__": "__main__"}
    try:
        exec(code, globals_dict, globals_dict)
        out = stdout_capture.getvalue()
        return {"stdout": out}
    except Exception as e:
        err = {"type": e.__class__.__name__, "message": str(e), "trace": traceback.format_exc()}
        return {"stdout": stdout_capture.getvalue(), "error": err}
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr