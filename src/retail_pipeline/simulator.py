"""Seeded simulator of application activity in the OLTP database.

Generation is pure and deterministic for a given seed and day; applying it to Postgres is
kept separate so the generated data can be tested without a database.
"""

import random
from dataclasses import dataclass
from datetime import date, timedelta

import psycopg

COUNTRIES = ["US", "GB", "NG", "DE", "FR", "CA", "IN", "BR"]
EMAIL_DOMAINS = ["example.com", "mail.test", "shop.example.org"]
DEFAULT_START_DATE = date(2025, 1, 1)


@dataclass(frozen=True)
class DaySummary:
    day: date
    users_created: int
    users_updated: int


def day_rng(seed: int, day: date) -> random.Random:
    return random.Random(f"{seed}:{day.isoformat()}")


def user_id_for(index: int) -> str:
    return f"u-{index:06d}"


def generate_users(
    rng: random.Random, day: date, start_index: int, count: int, dirty_rate: float = 0.0
) -> list[dict]:
    """New signups for a day. A dirty row has a malformed email or country code."""
    users = []
    for index in range(start_index, start_index + count):
        user_id = user_id_for(index)
        email = f"user{index}@{rng.choice(EMAIL_DOMAINS)}"
        country = rng.choice(COUNTRIES)
        if rng.random() < dirty_rate:
            if rng.random() < 0.5:
                email = f"user{index}.{rng.choice(EMAIL_DOMAINS)}"
            else:
                country = rng.choice(["USA", "??", ""])
        users.append(
            {
                "user_id": user_id,
                "email": email,
                "country": country,
                "signup_date": day,
                "is_active": True,
            }
        )
    return users


def plan_user_updates(rng: random.Random, existing_ids: list[str], count: int) -> list[dict]:
    """Pick existing users to change: either a new email or a deactivation."""
    chosen = rng.sample(existing_ids, min(count, len(existing_ids)))
    updates = []
    for user_id in chosen:
        if rng.random() < 0.5:
            updates.append({"user_id": user_id, "is_active": False})
        else:
            local = user_id.replace("-", "")
            updates.append(
                {"user_id": user_id, "email": f"{local}.new@{rng.choice(EMAIL_DOMAINS)}"}
            )
    return updates


def simulate_day(
    conn: psycopg.Connection,
    day: date,
    seed: int = 42,
    new_users: int = 20,
    updates: int = 3,
    dirty_rate: float = 0.05,
) -> DaySummary:
    rng = day_rng(seed, day)
    with conn.transaction():
        existing_ids = [
            row["user_id"]
            for row in conn.execute("SELECT user_id FROM users ORDER BY user_id").fetchall()
        ]
        planned = plan_user_updates(rng, existing_ids, updates)
        for update in planned:
            if "email" in update:
                conn.execute(
                    "UPDATE users SET email = %(email)s WHERE user_id = %(user_id)s", update
                )
            else:
                conn.execute(
                    "UPDATE users SET is_active = %(is_active)s WHERE user_id = %(user_id)s",
                    update,
                )

        created = generate_users(rng, day, len(existing_ids) + 1, new_users, dirty_rate)
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO users (user_id, email, country, signup_date, is_active) "
                "VALUES (%(user_id)s, %(email)s, %(country)s, %(signup_date)s, %(is_active)s)",
                created,
            )
    return DaySummary(day=day, users_created=len(created), users_updated=len(planned))


def next_day(conn: psycopg.Connection) -> date:
    """The day after the latest simulated signup, or the default start for an empty database."""
    latest = conn.execute("SELECT max(signup_date) AS latest FROM users").fetchone()["latest"]
    return DEFAULT_START_DATE if latest is None else latest + timedelta(days=1)


def simulate(
    conn: psycopg.Connection,
    days: int,
    seed: int = 42,
    new_users: int = 20,
    updates: int = 3,
    dirty_rate: float = 0.05,
) -> list[DaySummary]:
    start = next_day(conn)
    return [
        simulate_day(conn, start + timedelta(days=offset), seed, new_users, updates, dirty_rate)
        for offset in range(days)
    ]
