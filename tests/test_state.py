from datetime import UTC, datetime

import pytest

from retail_pipeline.state import WatermarkStore


def test_unknown_table_has_no_watermark(tmp_path):
    assert WatermarkStore(tmp_path / "state" / "watermarks.json").get("users") is None


def test_watermark_round_trips_with_microseconds_across_instances(tmp_path):
    path = tmp_path / "state" / "watermarks.json"
    mark = datetime(2025, 2, 13, 10, 30, 15, 123456, tzinfo=UTC)

    WatermarkStore(path).set("users", mark)

    assert WatermarkStore(path).get("users") == mark


def test_watermarks_are_tracked_per_table(tmp_path):
    store = WatermarkStore(tmp_path / "watermarks.json")
    users_mark = datetime(2025, 1, 1, tzinfo=UTC)
    orders_mark = datetime(2025, 1, 2, tzinfo=UTC)

    store.set("users", users_mark)
    store.set("orders", orders_mark)

    assert store.get("users") == users_mark
    assert store.get("orders") == orders_mark


def test_naive_watermark_is_refused(tmp_path):
    with pytest.raises(ValueError):
        WatermarkStore(tmp_path / "watermarks.json").set("users", datetime(2025, 1, 1))
