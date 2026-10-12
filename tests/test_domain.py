from decimal import Decimal

from retail_pipeline.domain import User, Purchase, ReturnEvent, Discount


def test_user_model_tracks_profile_fields():
    user = User(
        user_id="u-1001",
        email="zoe@example.com",
        country="US",
        signup_date="2025-01-15",
        is_active=True,
    )

    assert user.user_id == "u-1001"
    assert user.email == "zoe@example.com"
    assert user.country == "US"
    assert user.is_active is True


def test_purchase_and_return_events_are_valid():
    purchase = Purchase(
        transaction_id="t-5001",
        user_id="u-1001",
        order_id="o-9001",
        product_id="p-220",
        quantity=2,
        unit_price=Decimal("49.99"),
        currency="USD",
        event_date="2025-02-13",
    )

    return_event = ReturnEvent(
        transaction_id="t-5002",
        user_id="u-1001",
        order_id="o-9001",
        product_id="p-220",
        quantity=1,
        refund_amount=Decimal("24.99"),
        currency="USD",
        event_date="2025-02-18",
    )

    assert purchase.total_amount == Decimal("99.98")
    assert return_event.refund_amount == Decimal("24.99")


def test_discount_model_tracks_coupon_amount():
    discount = Discount(
        transaction_id="t-5001",
        user_id="u-1001",
        coupon_code="SAVE10",
        discount_amount=Decimal("9.99"),
        currency="USD",
        event_date="2025-02-13",
    )

    assert discount.discount_amount == Decimal("9.99")
    assert discount.coupon_code == "SAVE10"
