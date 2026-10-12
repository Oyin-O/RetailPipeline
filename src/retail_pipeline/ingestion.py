"""Row validation and cleaning. Pure functions: rows in, rows out, no I/O."""

import json
from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import BaseModel, ValidationError

from retail_pipeline.domain import User

Row = Mapping[str, Any]


def _error_summary(exc: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(part) for part in err['loc']) or 'row'}: {err['msg']}"
        for err in exc.errors()
    )


def validate_rows(
    rows: Iterable[Row], model: type[BaseModel], *, source: str, key: str
) -> tuple[list[dict], list[dict]]:
    """Split rows into validated records and rejects.

    Rejects keep the raw row as JSON and the reason it failed, ready to be quarantined.
    """
    valid: list[dict] = []
    rejected: list[dict] = []
    for row in rows:
        try:
            valid.append(model.model_validate(dict(row)).model_dump())
        except ValidationError as exc:
            rejected.append(
                {
                    "source": source,
                    "key": None if row.get(key) is None else str(row.get(key)),
                    "error": _error_summary(exc),
                    "raw": json.dumps(dict(row), default=str, sort_keys=True),
                }
            )
    return valid, rejected


def _last_per_key(rows: list[dict], key: str) -> list[dict]:
    """Keep the last occurrence of each key, in order of first appearance."""
    latest: dict[Any, dict] = {}
    for row in rows:
        latest[row[key]] = row
    return list(latest.values())


def ingest_users(rows: Iterable[Row]) -> list[dict]:
    """Return clean user records; invalid rows are left out, duplicates collapse to the last."""
    valid, _ = validate_rows(rows, User, source="users", key="user_id")
    return _last_per_key(valid, "user_id")
