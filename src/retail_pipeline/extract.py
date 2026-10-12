"""Incremental extraction from the OLTP database into bronze Parquet files."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from psycopg import sql

from retail_pipeline.state import WatermarkStore
from retail_pipeline.storage import write_parquet


@dataclass(frozen=True)
class TableSpec:
    name: str
    key: str


TABLES: dict[str, TableSpec] = {
    "users": TableSpec(name="users", key="user_id"),
}


@dataclass(frozen=True)
class ExtractResult:
    table: str
    row_count: int
    low: datetime | None
    high: datetime
    path: Path | None


def _normalise(row: dict) -> dict:
    return {
        column: value.astimezone(UTC) if isinstance(value, datetime) else value
        for column, value in row.items()
    }


def extract_table(
    conn: psycopg.Connection, spec: TableSpec, bronze_dir: Path, watermarks: WatermarkStore
) -> ExtractResult:
    """Pull rows with low < updated_at <= high and advance the watermark to high.

    The upper bound comes from the database clock and is fixed before the query runs. The
    watermark is only advanced after the Parquet file is in place, so a failed run pulls the
    same window again. Bronze may therefore hold several versions of a row; silver keeps the
    newest. A transaction that stays open across an extraction can commit rows stamped below
    the new watermark, and hard deletes are never seen.
    """
    low = watermarks.get(spec.name)
    high = conn.execute("SELECT clock_timestamp() AS high").fetchone()["high"].astimezone(UTC)

    query = sql.SQL("SELECT * FROM {} WHERE updated_at <= %(high)s").format(
        sql.Identifier(spec.name)
    )
    if low is not None:
        query += sql.SQL(" AND updated_at > %(low)s")
    query += sql.SQL(" ORDER BY updated_at, {}").format(sql.Identifier(spec.key))
    rows = [_normalise(row) for row in conn.execute(query, {"low": low, "high": high}).fetchall()]

    path = None
    if rows:
        path = bronze_dir / spec.name / f"extract_{high:%Y%m%dT%H%M%S%f}.parquet"
        write_parquet(rows, path)
    watermarks.set(spec.name, high)
    return ExtractResult(table=spec.name, row_count=len(rows), low=low, high=high, path=path)
