import os
from datetime import date

import psycopg
import pytest
from psycopg import sql

from retail_pipeline import extract as extract_module
from retail_pipeline import oltp, simulator
from retail_pipeline.domain import User
from retail_pipeline.extract import TABLES, extract_table
from retail_pipeline.ingestion import validate_rows
from retail_pipeline.state import WatermarkStore
from retail_pipeline.storage import latest_per_key, read_parquet, read_parquet_dir

pytestmark = pytest.mark.integration

USERS = TABLES["users"]


@pytest.fixture
def bronze_dir(tmp_path):
    return tmp_path / "bronze"


@pytest.fixture
def watermarks(tmp_path):
    return WatermarkStore(tmp_path / "state" / "watermarks.json")


def insert_user(conn, user_id, email=None, country="US"):
    conn.execute(
        "INSERT INTO users (user_id, email, country, signup_date) VALUES (%s, %s, %s, %s)",
        (user_id, email or f"{user_id}@example.com", country, date(2025, 1, 1)),
    )


def test_first_extract_pulls_every_row(oltp_conn, bronze_dir, watermarks):
    insert_user(oltp_conn, "u-1")
    insert_user(oltp_conn, "u-2")

    result = extract_table(oltp_conn, USERS, bronze_dir, watermarks)

    assert result.row_count == 2
    assert result.low is None
    assert [row["user_id"] for row in read_parquet(result.path)] == ["u-1", "u-2"]
    assert watermarks.get("users") == result.high


def test_second_extract_with_no_changes_pulls_nothing(oltp_conn, bronze_dir, watermarks):
    insert_user(oltp_conn, "u-1")
    first = extract_table(oltp_conn, USERS, bronze_dir, watermarks)

    second = extract_table(oltp_conn, USERS, bronze_dir, watermarks)

    assert second.row_count == 0
    assert second.path is None
    assert second.low == first.high
    assert len(list((bronze_dir / "users").glob("*.parquet"))) == 1


def test_only_new_and_changed_rows_are_pulled(oltp_conn, bronze_dir, watermarks):
    insert_user(oltp_conn, "u-1")
    insert_user(oltp_conn, "u-2")
    extract_table(oltp_conn, USERS, bronze_dir, watermarks)

    oltp_conn.execute("UPDATE users SET is_active = false WHERE user_id = 'u-1'")
    insert_user(oltp_conn, "u-3")
    result = extract_table(oltp_conn, USERS, bronze_dir, watermarks)

    assert sorted(row["user_id"] for row in read_parquet(result.path)) == ["u-1", "u-3"]


def test_updated_user_replaces_old_version_downstream(oltp_conn, bronze_dir, watermarks):
    insert_user(oltp_conn, "u-1")
    extract_table(oltp_conn, USERS, bronze_dir, watermarks)
    oltp_conn.execute("UPDATE users SET email = 'changed@example.com' WHERE user_id = 'u-1'")
    extract_table(oltp_conn, USERS, bronze_dir, watermarks)

    bronze = read_parquet_dir(bronze_dir / "users")
    current = latest_per_key(bronze, key="user_id")

    assert len(bronze) == 2
    assert [row["email"] for row in current] == ["changed@example.com"]


def test_failed_write_leaves_watermark_so_the_window_is_pulled_again(
    oltp_conn, bronze_dir, watermarks, monkeypatch
):
    insert_user(oltp_conn, "u-1")

    def boom(*args, **kwargs):
        raise OSError("disk full")

    with monkeypatch.context() as patch:
        patch.setattr(extract_module, "write_parquet", boom)
        with pytest.raises(OSError):
            extract_table(oltp_conn, USERS, bronze_dir, watermarks)

    assert watermarks.get("users") is None
    assert extract_table(oltp_conn, USERS, bronze_dir, watermarks).row_count == 1


def test_read_only_connection_refuses_writes(oltp_conn):
    schema = oltp_conn.execute("SELECT current_schema() AS name").fetchone()["name"]
    insert_user(oltp_conn, "u-1")

    with oltp.connect(os.environ["OLTP_DSN"], read_only=True) as reader:
        reader.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        assert reader.execute("SELECT count(*) AS n FROM users").fetchone()["n"] == 1
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            reader.execute("DELETE FROM users")


def test_simulated_days_extract_incrementally_and_validate(oltp_conn, bronze_dir, watermarks):
    simulator.simulate(oltp_conn, days=2, seed=7, new_users=10, updates=2, dirty_rate=0.3)
    first = extract_table(oltp_conn, USERS, bronze_dir, watermarks)

    days = simulator.simulate(oltp_conn, days=1, seed=7, new_users=5, updates=2, dirty_rate=0.3)
    second = extract_table(oltp_conn, USERS, bronze_dir, watermarks)

    assert first.row_count == 20
    assert days[0].day == date(2025, 1, 3)
    assert second.row_count == 5 + 2
    current = latest_per_key(read_parquet_dir(bronze_dir / "users"), key="user_id")
    valid, rejected = validate_rows(current, User, source="users", key="user_id")
    assert len(current) == 25
    assert len(valid) + len(rejected) == 25
    assert rejected
