"""Pipeline stages, wiring the pure logic to Postgres, Parquet and DuckDB."""

from dataclasses import dataclass

from retail_pipeline import oltp, quality, warehouse
from retail_pipeline.config import Settings
from retail_pipeline.domain import User
from retail_pipeline.extract import TABLES, ExtractResult, extract_table
from retail_pipeline.ingestion import validate_rows
from retail_pipeline.state import WatermarkStore
from retail_pipeline.storage import (
    REJECTS_SCHEMA,
    USERS_SCHEMA,
    latest_per_key,
    read_parquet_dir,
    write_parquet,
)


@dataclass(frozen=True)
class IngestResult:
    dataset: str
    valid: int
    rejected: int


def extract_all(settings: Settings, tables: list[str] | None = None) -> list[ExtractResult]:
    watermarks = WatermarkStore(settings.state_path)
    with oltp.connect(settings.oltp_dsn, read_only=True) as conn:
        return [
            extract_table(conn, TABLES[name], settings.bronze_dir, watermarks)
            for name in (tables or list(TABLES))
        ]


def build_silver_users(settings: Settings) -> IngestResult:
    """Rebuild silver users and their rejects from everything in bronze."""
    bronze = read_parquet_dir(settings.bronze_dir / "users")
    current = latest_per_key(bronze, key="user_id")
    valid, rejected = validate_rows(current, User, source="users", key="user_id")
    write_parquet(valid, settings.silver_dir / "users" / "users.parquet", USERS_SCHEMA)
    write_parquet(rejected, settings.rejects_dir / "users" / "rejects.parquet", REJECTS_SCHEMA)
    return IngestResult(dataset="users", valid=len(valid), rejected=len(rejected))


def build_warehouse(settings: Settings) -> list[str]:
    with warehouse.connect(settings.warehouse_path) as con:
        warehouse.register_silver(con, settings.silver_dir)
        return warehouse.run_models(con)


def run_checks(settings: Settings) -> list[quality.CheckResult]:
    with warehouse.connect(settings.warehouse_path, read_only=True) as con:
        return quality.run_checks(con)
