from retail_pipeline.ingestion import ingest_users, ingest_transactions, summarize_transactions


def test_ingest_users_creates_clean_records():
    raw_rows = [
        {
            "user_id": "u-1",
            "email": "a@example.com",
            "country": "US",
            "signup_date": "2025-01-01",
            "is_active": "true",
        },
        {
            "user_id": "u-2",
            "email": "b@example.com",
            "country": "GB",
            "signup_date": "2025-01-05",
            "is_active": "false",
        },
    ]

    result = ingest_users(raw_rows)

    assert len(result) == 2
    assert result[0]["is_active"] is True
    assert result[1]["is_active"] is False


def test_ingest_transactions_handles_purchase_return_and_discount_events():
    raw_rows = [
        {
            "transaction_id": "t-1",
            "user_id": "u-1",
            "order_id": "o-1",
            "product_id": "p-1",
            "event_type": "purchase",
            "quantity": "2",
            "unit_price": "49.99",
            "currency": "USD",
            "event_date": "2025-02-13",
        },
        {
            "transaction_id": "t-2",
            "user_id": "u-1",
            "order_id": "o-1",
            "product_id": "p-1",
            "event_type": "return",
            "quantity": "1",
            "refund_amount": "24.99",
            "currency": "USD",
            "event_date": "2025-02-18",
        },
        {
            "transaction_id": "t-3",
            "user_id": "u-1",
            "order_id": "o-1",
            "product_id": "p-1",
            "event_type": "discount",
            "coupon_code": "SAVE10",
            "discount_amount": "9.99",
            "currency": "USD",
            "event_date": "2025-02-13",
        },
    ]

    result = ingest_transactions(raw_rows)

    assert len(result) == 3
    assert result[0]["event_type"] == "purchase"
    assert result[1]["event_type"] == "return"
    assert result[2]["event_type"] == "discount"


def test_summarize_transactions_reports_event_totals():
    rows = [
        {"event_type": "purchase", "quantity": 2, "unit_price": "49.99"},
        {"event_type": "return", "quantity": 1, "refund_amount": "24.99"},
        {"event_type": "discount", "discount_amount": "9.99"},
    ]

    summary = summarize_transactions(rows)

    assert summary["purchase_count"] == 1
    assert summary["return_count"] == 1
    assert summary["discount_count"] == 1
    assert summary["total_revenue"] == 99.98
