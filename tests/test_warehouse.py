from datetime import date

import pytest

from retail_pipeline import quality, warehouse


@pytest.fixture
def con():
    with warehouse.connect() as connection:
        connection.execute(
            """
            CREATE TABLE silver_users (
                user_id VARCHAR, email VARCHAR, country VARCHAR,
                signup_date DATE, is_active BOOLEAN, updated_at TIMESTAMPTZ
            )
            """
        )
        connection.execute(
            """
            INSERT INTO silver_users VALUES
                ('u-1', 'a@example.com', 'US', DATE '2025-01-01', true, '2025-01-01 10:00:00+00'),
                ('u-2', 'b@shop.test', 'GB', DATE '2025-01-05', false, '2025-01-06 09:00:00+00')
            """
        )
        yield connection


def test_dim_users_has_one_row_per_user_with_email_domain(con):
    warehouse.run_models(con)

    rows = con.execute(
        "SELECT user_id, email_domain, country, signup_date, is_active "
        "FROM dim_users ORDER BY user_id"
    ).fetchall()

    assert rows == [
        ("u-1", "example.com", "US", date(2025, 1, 1), True),
        ("u-2", "shop.test", "GB", date(2025, 1, 5), False),
    ]


def test_run_models_is_repeatable(con):
    warehouse.run_models(con)
    warehouse.run_models(con)

    assert con.execute("SELECT count(*) FROM dim_users").fetchone()[0] == 2


def test_checks_pass_on_clean_warehouse(con):
    warehouse.run_models(con)

    assert all(result.passed for result in quality.run_checks(con))


def test_checks_report_duplicates_nulls_and_future_signups(con):
    warehouse.run_models(con)
    con.execute("INSERT INTO dim_users SELECT * FROM dim_users WHERE user_id = 'u-1'")
    con.execute(
        "INSERT INTO dim_users (user_id, email, country, signup_date, is_active) "
        "VALUES ('u-3', NULL, 'US', current_date + 1, true)"
    )

    failing = {result.name: result.failing_rows for result in quality.run_checks(con)}

    assert failing == {
        "dim_users_unique_user_id": 1,
        "dim_users_required_not_null": 1,
        "dim_users_signup_not_in_future": 1,
    }
