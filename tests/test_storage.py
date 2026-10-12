from datetime import UTC, date, datetime

from retail_pipeline.storage import (
    USERS_SCHEMA,
    latest_per_key,
    read_parquet,
    read_parquet_dir,
    write_parquet,
)


def ts(hour):
    return datetime(2025, 1, 1, hour, tzinfo=UTC)


def user_row(user_id="u-1", updated_at=None, **overrides):
    row = {
        "user_id": user_id,
        "email": f"{user_id}@example.com",
        "country": "US",
        "signup_date": date(2025, 1, 1),
        "is_active": True,
        "updated_at": updated_at or ts(1),
    }
    row.update(overrides)
    return row


def test_parquet_round_trip_preserves_values(tmp_path):
    rows = [user_row("u-1"), user_row("u-2", is_active=False)]

    path = write_parquet(rows, tmp_path / "nested" / "users.parquet", USERS_SCHEMA)

    assert read_parquet(path) == rows


def test_write_parquet_replaces_existing_file_and_leaves_no_temp_file(tmp_path):
    path = tmp_path / "users.parquet"
    write_parquet([user_row("u-1"), user_row("u-2")], path, USERS_SCHEMA)

    write_parquet([user_row("u-3")], path, USERS_SCHEMA)

    assert [row["user_id"] for row in read_parquet(path)] == ["u-3"]
    assert [p.name for p in tmp_path.iterdir()] == ["users.parquet"]


def test_write_parquet_with_schema_allows_empty_dataset(tmp_path):
    path = write_parquet([], tmp_path / "users.parquet", USERS_SCHEMA)

    assert read_parquet(path) == []


def test_read_parquet_dir_concatenates_files_in_name_order(tmp_path):
    write_parquet([user_row("u-2")], tmp_path / "extract_2.parquet")
    write_parquet([user_row("u-1")], tmp_path / "extract_1.parquet")

    assert [row["user_id"] for row in read_parquet_dir(tmp_path)] == ["u-1", "u-2"]


def test_read_parquet_dir_of_missing_directory_is_empty(tmp_path):
    assert read_parquet_dir(tmp_path / "nope") == []


def test_latest_per_key_keeps_newest_version():
    rows = [
        user_row("u-1", ts(1), email="old@example.com"),
        user_row("u-2", ts(1)),
        user_row("u-1", ts(3), email="new@example.com"),
        user_row("u-1", ts(2), email="middle@example.com"),
    ]

    result = latest_per_key(rows, key="user_id")

    assert [row["user_id"] for row in result] == ["u-1", "u-2"]
    assert result[0]["email"] == "new@example.com"


def test_latest_per_key_later_row_wins_a_tie():
    rows = [user_row("u-1", ts(1), email="first@example.com"), user_row("u-1", ts(1))]

    assert latest_per_key(rows, key="user_id")[0]["email"] == "u-1@example.com"
