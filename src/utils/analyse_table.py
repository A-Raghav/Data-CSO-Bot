import gc
import pandas as pd


def create_table_analysis(df: pd.DataFrame, table_id: str) -> dict:
    """
    Analyzes the table and returns a dictionary with the analysis results.

    Args:
        df (pd.DataFrame): The DataFrame containing the CSO data.

    Returns:
        dict: A dictionary containing the analysis results.
    """
    csv_fp = f"cache/{table_id}.csv"

    try:
        table_shape = df.shape
        table_sample = pd.concat([df.head(5), df.tail(5)]) if len(df) > 10 else df
        
        table_info_df = pd.DataFrame({
            "columns": df.columns,
            "dtypes": [str(df[col].dtype) for col in df.columns],
            "nunique": [df[col].nunique() if df[col].nunique() <= 50 else '>50' for col in df.columns],
            "nulls": [df[col].isnull().sum() for col in df.columns]
        })

        context_list = [
            f"**Table ID:** {table_id}",
            f"- **CSV File Path**: {csv_fp}",
            f"- **Table Shape**: {table_shape}",
            "- **Table Info**:",
            table_info_df.to_string(index=False),
            "- **Table Sample (first and last 5 rows)**:",
            table_sample.to_string(index=False),
        ]
        del table_info_df
        gc.collect()

    except Exception as e:
        context_list = []

    return context_list