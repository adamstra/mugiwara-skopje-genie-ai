from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
import duckdb

class TabularParser:
    """Parses tabular datasets (CSV, Excel) and registers them with DuckDB."""

    def __init__(self, db_conn: Optional[duckdb.DuckDBPyConnection] = None):
        self.conn = db_conn or duckdb.connect(database=":memory:")

    def parse_and_register(self, file_path: Path, source_id: Optional[str] = None) -> List[Dict[str, Any]]:
        file_path = Path(file_path)
        source_name = source_id or file_path.stem
        # sanitize table name for duckdb
        table_base = "".join([c if c.isalnum() else "_" for c in source_name]).strip("_")

        records = []
        suffix = file_path.suffix.lower()

        if suffix in [".csv", ".tsv", ".txt"]:
            sep = "\t" if suffix == ".tsv" else ","
            try:
                df = pd.read_csv(file_path, sep=sep, low_memory=False)
            except Exception:
                df = pd.read_csv(file_path, sep=None, engine="python")
            
            table_name = f"tbl_{table_base}"
            self.conn.register(table_name, df)
            
            summary = self._generate_summary(df, table_name, file_path.name, source_name)
            records.append(summary)

        elif suffix in [".xlsx", ".xls"]:
            excel_file = pd.ExcelFile(file_path)
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                clean_sheet = "".join([c if c.isalnum() else "_" for c in sheet_name]).strip("_")
                table_name = f"tbl_{table_base}_{clean_sheet}"
                self.conn.register(table_name, df)
                
                summary = self._generate_summary(
                    df, table_name, file_path.name, source_name, sheet_name=sheet_name
                )
                records.append(summary)

        return records

    def _generate_summary(
        self, df: pd.DataFrame, table_name: str, filename: str, source_id: str, sheet_name: Optional[str] = None
    ) -> Dict[str, Any]:
        columns = list(df.columns)
        shape = df.shape
        preview_rows = df.head(3).to_dict(orient="records")
        col_types = {col: str(dtype) for col, dtype in df.dtypes.items()}

        summary_text = (
            f"Table: {table_name}\n"
            f"Source ID: {source_id}\n"
            f"File: {filename}" + (f" (Sheet: {sheet_name})" if sheet_name else "") + "\n"
            f"Dimensions: {shape[0]} rows, {shape[1]} columns\n"
            f"Columns: {', '.join(columns)}\n"
            f"Preview: {preview_rows}\n"
        )

        return {
            "source_id": source_id,
            "filename": filename,
            "sheet_name": sheet_name,
            "table_name": table_name,
            "columns": columns,
            "dtypes": col_types,
            "num_rows": shape[0],
            "num_cols": shape[1],
            "text": summary_text,
            "content_type": "tabular",
        }
