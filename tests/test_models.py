from typing import Any

import pytest
from pydantic import ValidationError

from revenue_monitor.models import Coupon, Subscription


def make_subscription(**overrides: Any) -> dict[str, Any]:
    subscription: dict[str, Any] = {
        "id": "sub_abc",
        "customer": "cus_abc",
        "created": 1_700_000_000,
        "start_date": 1_700_000_000,
        "status": "active",
        "items": {
            "object": "list",
            "data": [
                {
                    "id": "si_abc",
                    "quantity": 3,
                    "price": {
                        "id": "price_abc",
                        "created": 1_690_000_000,
                        "product": "prod_abc",
                        "unit_amount": 2900,
                        "recurring": {"interval": "month"},
                    },
                }
            ],
        },
    }
    subscription.update(overrides)
    return subscription


class TestSubscription:
    def test_valid_subscription_parses(self) -> None:
        subscription = Subscription.model_validate(make_subscription())
        assert subscription.items.data[0].price.unit_amount == 2900

    def test_canceled_without_end_raises(self) -> None:
        with pytest.raises(ValidationError, match="canceled_at and ended_at"):
            Subscription.model_validate(make_subscription(status="canceled"))

    def test_trialing_without_trial_end_raises(self) -> None:
        with pytest.raises(ValidationError, match="trial_end"):
            Subscription.model_validate(make_subscription(status="trialing"))

    def test_extra_fields_are_preserved(self) -> None:
        subscription = Subscription.model_validate(make_subscription(livemode=False))
        assert subscription.model_dump()["livemode"] is False


class TestCoupon:
    def test_repeating_coupon_without_months_raises(self) -> None:
        with pytest.raises(ValidationError, match="duration_in_months"):
            Coupon(id="X", percent_off=20, duration="repeating")

    def test_forever_coupon_with_months_raises(self) -> None:
        with pytest.raises(ValidationError, match="duration_in_months"):
            Coupon(id="X", percent_off=20, duration="forever", duration_in_months=3)
