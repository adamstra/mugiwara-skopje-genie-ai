from typing import Dict, Any, List, Optional
import duckdb
import pandas as pd

class SQLTool:
    """Executes SQL queries against DuckDB for structured tabular datasets."""

    def __init__(self, conn: Optional[duckdb.DuckDBPyConnection] = None):
        self.conn = conn or duckdb.connect(database=":memory:")

    def execute_query(self, query: str) -> Dict[str, Any]:
        """Executes a SQL query and returns column headers and rows."""
        try:
            rel = self.conn.sql(query)
            if rel is None:
                return {"success": True, "columns": [], "rows": [], "row_count": 0}
            
            df = rel.df()
            return {
                "success": True,
                "columns": list(df.columns),
                "rows": df.to_dict(orient="records"),
                "row_count": len(df),
                "dataframe": df
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "columns": [],
                "rows": [],
                "row_count": 0
            }

    def list_tables(self) -> List[str]:
        """Returns list of registered table names."""
        res = self.conn.execute("SHOW TABLES").fetchall()
        return [r[0] for r in res]

    def describe_table(self, table_name: str) -> List[Dict[str, Any]]:
        """Describes columns and types of a table."""
        res = self.conn.execute(f"DESCRIBE {table_name}").fetchall()
        return [{"column_name": r[0], "column_type": r[1], "null": r[2]} for r in res]
