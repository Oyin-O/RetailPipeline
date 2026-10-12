"""Validated models for the cleaned (silver) layer."""

import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_COUNTRY_RE = re.compile(r"^[A-Z]{2}$")


class User(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: str = Field(min_length=1)
    email: str
    country: str
    signup_date: date
    is_active: bool
    updated_at: datetime | None = None

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        value = value.lower()
        if not _EMAIL_RE.match(value):
            raise ValueError("not a valid email address")
        return value

    @field_validator("country")
    @classmethod
    def _valid_country(cls, value: str) -> str:
        value = value.upper()
        if not _COUNTRY_RE.match(value):
            raise ValueError("must be a 2-letter country code")
        return value
