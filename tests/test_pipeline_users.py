"""Bronze -> silver -> warehouse for users, without Postgres: bronze files are written directly."""

from datetime import UTC, date, datetime

import pytest

from retail_pipeline import pipeline, warehouse
from retail_pipeline.config import Settings
from retail_pipeline.storage import read_parquet, write_parquet


def ts(hour):
    return datetime(2025, 1, 1, hour, tzinfo=UTC)


def oltp_user(user_id, updated_at, **overrides):
    row = {
        "user_id": user_id,
        "email": f"{user_id}@example.com",
        "country": "US",
        "signup_date": date(2025, 1, 1),
        "is_active": True,
        "created_at": ts(1),
        "updated_at": updated_at,
    }
    row.update(overrides)
    return row


@pytest.fixture
def settings(tmp_path):
    return Settings(oltp_dsn="unused", data_dir=tmp_path)


def write_bronze(settings, name, rows):
    write_parquet(rows, settings.bronze_dir / "users" / f"{name}.parquet")


def dim_users(settings):
    with warehouse.connect(settings.warehouse_path, read_only=True) as con:
        return con.execute(
            "SELECT user_id, email, is_active FROM dim_users ORDER BY user_id"
        ).fetchall()


def test_users_flow_from_bronze_to_warehouse(settings):
    write_bronze(
        settings,
        "extract_1",
        [oltp_user("u-1", ts(1)), oltp_user("u-2", ts(1)), oltp_user("u-3", ts(1), country="USA")],
    )

    result = pipeline.build_silver_users(settings)
    pipeline.build_warehouse(settings)

    assert (result.valid, result.rejected) == (2, 1)
    assert dim_users(settings) == [
        ("u-1", "u-1@example.com", True),
        ("u-2", "u-2@example.com", True),
    ]
    rejects = read_parquet(settings.rejects_dir / "users" / "rejects.parquet")
    assert [(row["key"], "country" in row["error"]) for row in rejects] == [("u-3", True)]
    assert all(check.passed for check in pipeline.run_checks(settings))


def test_later_extract_replaces_older_version_of_a_user(settings):
    write_bronze(settings, "extract_1", [oltp_user("u-1", ts(1)), oltp_user("u-2", ts(1))])
    write_bronze(settings, "extract_2", [oltp_user("u-1", ts(5), is_active=False)])

    result = pipeline.build_silver_users(settings)
    pipeline.build_warehouse(settings)

    assert result.valid == 2
    assert dim_users(settings) == [
        ("u-1", "u-1@example.com", False),
        ("u-2", "u-2@example.com", True),
    ]


def test_user_fixed_in_source_leaves_the_rejects(settings):
    write_bronze(settings, "extract_1", [oltp_user("u-1", ts(1), email="broken")])
    assert pipeline.build_silver_users(settings).rejected == 1

    write_bronze(settings, "extract_2", [oltp_user("u-1", ts(2), email="fixed@example.com")])
    result = pipeline.build_silver_users(settings)

    assert (result.valid, result.rejected) == (1, 0)
    assert read_parquet(settings.rejects_dir / "users" / "rejects.parquet") == []


def test_rebuilding_is_idempotent(settings):
    write_bronze(settings, "extract_1", [oltp_user("u-1", ts(1)), oltp_user("u-2", ts(1))])

    for _ in range(2):
        pipeline.build_silver_users(settings)
        pipeline.build_warehouse(settings)

    assert len(dim_users(settings)) == 2


def test_empty_bronze_builds_an_empty_warehouse(settings):
    result = pipeline.build_silver_users(settings)
    pipeline.build_warehouse(settings)

    assert (result.valid, result.rejected) == (0, 0)
    assert dim_users(settings) == []
