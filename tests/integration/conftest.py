"""Fixtures for tests that need the OLTP Postgres database.

Each test runs in its own throwaway Postgres schema, so pointing OLTP_DSN at a database
that already holds simulated data is safe.
"""

import os
import uuid
from pathlib import Path

import pytest
from psycopg import sql

from retail_pipeline import oltp

SCHEMA_SQL = Path(__file__).resolve().parents[2] / "oltp" / "schema.sql"


@pytest.fixture
def oltp_conn():
    dsn = os.environ.get("OLTP_DSN")
    if not dsn:
        pytest.skip("OLTP_DSN is not set")
    schema = sql.Identifier(f"test_{uuid.uuid4().hex[:12]}")
    with oltp.connect(dsn) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(schema))
        conn.execute(sql.SQL("SET search_path TO {}").format(schema))
        try:
            oltp.apply_schema(conn, SCHEMA_SQL)
            yield conn
        finally:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(schema))
