from datetime import date

import pytest
from pydantic import ValidationError

from retail_pipeline.domain import User


def make_user(**overrides):
    fields = {
        "user_id": "u-1001",
        "email": "zoe@example.com",
        "country": "US",
        "signup_date": "2025-01-15",
        "is_active": True,
    }
    fields.update(overrides)
    return User(**fields)


def test_user_parses_signup_date_string():
    assert make_user().signup_date == date(2025, 1, 15)


def test_user_normalises_email_and_country_case():
    user = make_user(email="  Zoe@Example.COM ", country="us")

    assert user.email == "zoe@example.com"
    assert user.country == "US"


@pytest.mark.parametrize("raw, expected", [("true", True), ("false", False), (True, True)])
def test_user_coerces_is_active(raw, expected):
    assert make_user(is_active=raw).is_active is expected


@pytest.mark.parametrize(
    "overrides",
    [
        {"email": "zoe.example.com"},
        {"email": "zoe@example"},
        {"country": "USA"},
        {"country": ""},
        {"country": "1!"},
        {"user_id": ""},
        {"signup_date": "15/01/2025"},
        {"is_active": "maybe"},
    ],
)
def test_user_rejects_invalid_fields(overrides):
    with pytest.raises(ValidationError):
        make_user(**overrides)
