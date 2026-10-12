import json

from retail_pipeline.domain import User
from retail_pipeline.ingestion import ingest_users, validate_rows

GOOD = {
    "user_id": "u-1",
    "email": "a@example.com",
    "country": "US",
    "signup_date": "2025-01-01",
    "is_active": "true",
}
BAD_EMAIL = {**GOOD, "user_id": "u-2", "email": "not-an-email"}
MISSING_COUNTRY = {"user_id": "u-3", "email": "c@example.com", "signup_date": "2025-01-01"}


def test_validate_rows_splits_valid_and_rejected():
    valid, rejected = validate_rows(
        [GOOD, BAD_EMAIL, MISSING_COUNTRY], User, source="users", key="user_id"
    )

    assert [row["user_id"] for row in valid] == ["u-1"]
    assert [row["key"] for row in rejected] == ["u-2", "u-3"]


def test_rejects_carry_reason_and_raw_row():
    _, rejected = validate_rows([BAD_EMAIL, MISSING_COUNTRY], User, source="users", key="user_id")

    assert rejected[0]["source"] == "users"
    assert "email" in rejected[0]["error"]
    assert json.loads(rejected[0]["raw"]) == BAD_EMAIL
    assert "country" in rejected[1]["error"]
    assert "is_active" in rejected[1]["error"]


def test_reject_without_key_has_null_key():
    _, rejected = validate_rows([{"email": "x@example.com"}], User, source="users", key="user_id")

    assert rejected[0]["key"] is None


def test_ingest_users_leaves_out_invalid_rows():
    result = ingest_users([GOOD, BAD_EMAIL])

    assert [row["user_id"] for row in result] == ["u-1"]


def test_ingest_users_keeps_last_version_of_duplicate_user():
    updated = {**GOOD, "is_active": "false"}

    result = ingest_users([GOOD, updated])

    assert len(result) == 1
    assert result[0]["is_active"] is False
