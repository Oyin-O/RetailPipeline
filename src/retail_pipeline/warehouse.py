"""DuckDB warehouse: exposes silver Parquet as views and builds the SQL models over them."""

from importlib import resources
from pathlib import Path

import duckdb

# Silver datasets each model reads from, as view name -> directory under silver/.
SILVER_SOURCES = {"silver_users": "users"}

# Models run in this order; each is a file in retail_pipeline/sql.
MODELS = ["dim_users"]


def connect(path: Path | str = ":memory:", read_only: bool = False) -> duckdb.DuckDBPyConnection:
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path), read_only=read_only)


def register_silver(con: duckdb.DuckDBPyConnection, silver_dir: Path) -> None:
    for view, folder in SILVER_SOURCES.items():
        pattern = str(Path(silver_dir) / folder / "*.parquet").replace("'", "''")
        con.execute(
            f"CREATE OR REPLACE TEMP VIEW {view} AS SELECT * FROM read_parquet('{pattern}')"
        )


def run_models(con: duckdb.DuckDBPyConnection) -> list[str]:
    """Build every model. Expects the silver views (or same-named tables) to exist."""
    for model in MODELS:
        statement = resources.files("retail_pipeline").joinpath("sql", f"{model}.sql").read_text()
        con.execute(statement)
    return list(MODELS)
