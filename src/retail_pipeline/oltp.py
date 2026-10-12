"""Connections to the OLTP Postgres database."""

from pathlib import Path

import psycopg
from psycopg.rows import dict_row

DEFAULT_SCHEMA_PATH = Path("oltp/schema.sql")


def connect(dsn: str, read_only: bool = False) -> psycopg.Connection:
    """Open an autocommit connection that returns rows as dicts with UTC timestamps.

    With read_only, Postgres refuses any write on the session; extraction uses this so a
    bug in the pipeline cannot modify the application database.
    """
    options = "-c timezone=UTC"
    if read_only:
        options += " -c default_transaction_read_only=on"
    return psycopg.connect(dsn, autocommit=True, row_factory=dict_row, options=options)


def apply_schema(conn: psycopg.Connection, schema_path: Path = DEFAULT_SCHEMA_PATH) -> None:
    conn.execute(Path(schema_path).read_text())
