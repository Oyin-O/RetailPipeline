"""Post-load data quality checks. Each check is a query counting offending rows."""

from dataclasses import dataclass

import duckdb

CHECKS: dict[str, str] = {
    "dim_users_unique_user_id": """
        SELECT count(*) FROM (
            SELECT user_id FROM dim_users GROUP BY user_id HAVING count(*) > 1
        )
    """,
    "dim_users_required_not_null": """
        SELECT count(*) FROM dim_users
        WHERE user_id IS NULL OR email IS NULL OR country IS NULL
           OR signup_date IS NULL OR is_active IS NULL
    """,
    "dim_users_signup_not_in_future": """
        SELECT count(*) FROM dim_users WHERE signup_date > current_date
    """,
}


@dataclass(frozen=True)
class CheckResult:
    name: str
    failing_rows: int

    @property
    def passed(self) -> bool:
        return self.failing_rows == 0


def run_checks(con: duckdb.DuckDBPyConnection) -> list[CheckResult]:
    return [
        CheckResult(name=name, failing_rows=con.execute(query).fetchone()[0])
        for name, query in CHECKS.items()
    ]
