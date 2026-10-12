from datetime import date

from retail_pipeline.ingestion import ingest_users
from retail_pipeline.simulator import day_rng, generate_users, plan_user_updates

DAY = date(2025, 1, 1)


def test_generate_users_is_deterministic_for_a_seed_and_day():
    first = generate_users(day_rng(42, DAY), DAY, start_index=1, count=50, dirty_rate=0.2)
    second = generate_users(day_rng(42, DAY), DAY, start_index=1, count=50, dirty_rate=0.2)

    assert first == second


def test_generate_users_differs_between_seeds():
    first = generate_users(day_rng(1, DAY), DAY, start_index=1, count=50)
    second = generate_users(day_rng(2, DAY), DAY, start_index=1, count=50)

    assert first != second


def test_generate_users_assigns_sequential_unique_ids_and_signup_day():
    users = generate_users(day_rng(42, DAY), DAY, start_index=8, count=3)

    assert [user["user_id"] for user in users] == ["u-000008", "u-000009", "u-000010"]
    assert {user["signup_date"] for user in users} == {DAY}


def test_clean_users_all_pass_validation():
    users = generate_users(day_rng(42, DAY), DAY, start_index=1, count=100, dirty_rate=0.0)

    assert len(ingest_users(users)) == 100


def test_dirty_users_fail_validation():
    users = generate_users(day_rng(42, DAY), DAY, start_index=1, count=100, dirty_rate=1.0)

    assert ingest_users(users) == []


def test_plan_user_updates_targets_distinct_existing_users():
    existing = [f"u-{i:06d}" for i in range(1, 11)]

    updates = plan_user_updates(day_rng(42, DAY), existing, count=4)

    ids = [update["user_id"] for update in updates]
    assert len(set(ids)) == 4
    assert set(ids) <= set(existing)
    assert all(("email" in update) != ("is_active" in update) for update in updates)


def test_plan_user_updates_is_capped_by_existing_users():
    assert plan_user_updates(day_rng(42, DAY), [], count=3) == []
    assert len(plan_user_updates(day_rng(42, DAY), ["u-000001"], count=3)) == 1
