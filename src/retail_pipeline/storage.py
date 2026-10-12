"""Parquet I/O for the bronze, silver and rejects layers."""

import os
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

USERS_SCHEMA = pa.schema(
    [
        ("user_id", pa.string()),
        ("email", pa.string()),
        ("country", pa.string()),
        ("signup_date", pa.date32()),
        ("is_active", pa.bool_()),
        ("updated_at", pa.timestamp("us", tz="UTC")),
    ]
)

REJECTS_SCHEMA = pa.schema(
    [
        ("source", pa.string()),
        ("key", pa.string()),
        ("error", pa.string()),
        ("raw", pa.string()),
    ]
)


def write_parquet(
    rows: Iterable[Mapping[str, Any]], path: Path, schema: pa.Schema | None = None
) -> Path:
    """Write rows to a Parquet file atomically, replacing any existing file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist([dict(row) for row in rows], schema=schema)
    tmp = path.with_name(path.name + ".tmp")
    pq.write_table(table, tmp)
    os.replace(tmp, path)
    return path


def read_parquet(path: Path) -> list[dict]:
    return pq.read_table(path).to_pylist()


def read_parquet_dir(directory: Path) -> list[dict]:
    """Read every Parquet file in a directory, oldest file name first."""
    directory = Path(directory)
    if not directory.exists():
        return []
    rows: list[dict] = []
    for path in sorted(directory.glob("*.parquet")):
        rows.extend(read_parquet(path))
    return rows


def latest_per_key(
    rows: Iterable[Mapping[str, Any]], key: str, order_by: str = "updated_at"
) -> list[dict]:
    """Collapse row versions to the newest one per key; later rows win ties."""
    latest: dict[Any, dict] = {}
    for row in rows:
        current = latest.get(row[key])
        if current is None or row[order_by] >= current[order_by]:
            latest[row[key]] = dict(row)
    return sorted(latest.values(), key=lambda row: row[key])
