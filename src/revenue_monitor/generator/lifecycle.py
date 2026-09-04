"""Customers and subscription state, with a Stripe-style event for every change.

Every mutation of a subscription goes through ``SubscriptionState`` so that the event stream
(``customer.subscription.created/updated/deleted`` with full snapshots) is the complete history.
dbt rebuilds SCD2 subscription versions from those snapshots.
"""

import copy
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from revenue_monitor.generator.catalog import (
    COUNTRY_WEIGHTS,
    COUPONS,
    EMPLOYEE_BANDS,
    INDUSTRIES,
    NAME_PREFIXES,
    NAME_SUFFIXES,
    TIER_KEYS,
    Catalog,
)
from revenue_monitor.generator.ids import IdFactory

DAY = 86_400
TRIAL_DAYS = 14
TRIAL_SHARE = 0.60
COUPON_WEIGHTS = {"LAUNCH20": 0.12, "PARTNER10": 0.04}


def add_months(ts: int, months: int) -> int:
    """Shift a timestamp by whole months, keeping time of day.

    Days past the 28th clamp to the 28th so every month has the anniversary, which is how
    billing anchors behave for short months.
    """
    moment = datetime.fromtimestamp(ts, UTC)
    month_index = moment.month - 1 + months
    shifted = moment.replace(
        year=moment.year + month_index // 12, month=month_index % 12 + 1, day=min(moment.day, 28)
    )
    return int(shifted.timestamp())


def weighted_choice(rng: random.Random, weights: dict[str, float]) -> str:
    """Pick a key with probability proportional to its weight."""
    keys = list(weights)
    return rng.choices(keys, weights=[weights[key] for key in keys])[0]


@dataclass
class Recorder:
    """Collects every generated object; the single sink for the simulation."""

    ids: IdFactory
    customers: list[dict[str, Any]] = field(default_factory=list)
    subscriptions: list["SubscriptionState"] = field(default_factory=list)
    invoices: list[dict[str, Any]] = field(default_factory=list)
    charges: list[dict[str, Any]] = field(default_factory=list)
    refunds: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)


class SubscriptionState:
    """A live subscription payload plus the operations that change it."""

    def __init__(self, recorder: Recorder, data: dict[str, Any]) -> None:
        self._recorder = recorder
        self.data = data
        recorder.subscriptions.append(self)
        self._emit("customer.subscription.created", data["created"], None)

    @property
    def id(self) -> str:
        return str(self.data["id"])

    @property
    def status(self) -> str:
        return str(self.data["status"])

    @property
    def item(self) -> dict[str, Any]:
        # Reason: the generator only creates single-item subscriptions; dbt tests assert it.
        item: dict[str, Any] = self.data["items"]["data"][0]
        return item

    @property
    def price(self) -> dict[str, Any]:
        price: dict[str, Any] = self.item["price"]
        return price

    @property
    def quantity(self) -> int:
        return int(self.item["quantity"])

    @property
    def is_annual(self) -> bool:
        return bool(self.price["recurring"]["interval"] == "year")

    def percent_off_at(self, ts: int) -> float:
        """Discount percentage in force at a moment, 0 when none."""
        for discount in self.data["discounts"]:
            end = discount["end"]
            if discount["start"] <= ts and (end is None or ts < end):
                return float(discount["coupon"]["percent_off"])
        return 0.0

    def activate(self, ts: int) -> None:
        """Trial conversion or recovery from past_due."""
        self._update(ts, status="active")

    def mark_past_due(self, ts: int) -> None:
        self._update(ts, status="past_due")

    def change_price(self, ts: int, price: dict[str, Any]) -> None:
        self._update_item(ts, price=price)

    def change_quantity(self, ts: int, quantity: int) -> None:
        self._update_item(ts, quantity=max(1, quantity))

    def schedule_cancel(self, ts: int) -> None:
        """Customer asks to cancel at period end, as the Stripe portal does."""
        self._update(ts, cancel_at_period_end=True, canceled_at=ts)

    def cancel(self, ts: int, reason: str) -> None:
        """End the subscription immediately."""
        previous = {
            key: self.data[key]
            for key in ("status", "ended_at", "canceled_at", "cancellation_details")
        }
        self.data["status"] = "canceled"
        self.data["ended_at"] = ts
        self.data["canceled_at"] = self.data["canceled_at"] or ts
        self.data["cancellation_details"] = {"reason": reason}
        self._emit("customer.subscription.deleted", ts, previous)

    def _update(self, ts: int, **changes: Any) -> None:
        previous = {key: self.data[key] for key in changes}
        self.data.update(changes)
        self._emit("customer.subscription.updated", ts, previous)

    def _update_item(self, ts: int, **changes: Any) -> None:
        previous = {"items": copy.deepcopy(self.data["items"])}
        self.item.update(changes)
        self._emit("customer.subscription.updated", ts, previous)

    def _emit(self, event_type: str, ts: int, previous: dict[str, Any] | None) -> None:
        self._recorder.events.append(
            {
                "id": self._recorder.ids.new("evt"),
                "object": "event",
                "type": event_type,
                "created": ts,
                "data": {"object": copy.deepcopy(self.data), "previous_attributes": previous},
            }
        )


@dataclass(frozen=True)
class Company:
    """Firmographics that drive plan choice."""

    customer_id: str
    employee_band: str
    seat_range: tuple[int, int]
    tier_weights: dict[str, float]


def new_customer(rng: random.Random, recorder: Recorder, ts: int) -> Company:
    """Create a customer record and return the attributes plan choice depends on."""
    band, _, min_seats, max_seats, tier_weights = rng.choices(
        EMPLOYEE_BANDS, weights=[band[1] for band in EMPLOYEE_BANDS]
    )[0]
    name = f"{rng.choice(NAME_PREFIXES)} {rng.choice(NAME_SUFFIXES)}"
    customer_id = recorder.ids.new("cus")
    domain = name.lower().replace(" ", "") + rng.choice((".com", ".io", ".co"))
    recorder.customers.append(
        {
            "id": customer_id,
            "object": "customer",
            "created": ts,
            "email": f"billing@{domain}",
            "name": name,
            "metadata": {
                "country": weighted_choice(rng, COUNTRY_WEIGHTS),
                "industry": rng.choice(INDUSTRIES),
                "employee_band": band,
            },
        }
    )
    return Company(
        customer_id=customer_id,
        employee_band=band,
        seat_range=(min_seats, max_seats),
        tier_weights=dict(zip(TIER_KEYS, tier_weights, strict=True)),
    )


def start_subscription(
    rng: random.Random,
    recorder: Recorder,
    catalog: Catalog,
    company: Company,
    ts: int,
    allow_trial: bool = True,
) -> SubscriptionState:
    """Open a subscription: pick tier, interval, seats, coupon and trial.

    Args:
        rng: Seeded random source.
        recorder: Output sink.
        catalog: Products and prices.
        company: The customer the subscription belongs to.
        ts: Creation time.
        allow_trial: False for reactivations, which skip the trial.

    Returns:
        The new subscription, already recorded with its ``created`` event.
    """
    tier = weighted_choice(rng, company.tier_weights)
    interval = "year" if rng.random() < 0.25 else "month"
    seats = rng.randint(*company.seat_range)
    has_trial = allow_trial and rng.random() < TRIAL_SHARE
    trial_end = ts + TRIAL_DAYS * DAY if has_trial else None

    discounts = []
    coupon_key = weighted_choice(rng, {**COUPON_WEIGHTS, "": 1 - sum(COUPON_WEIGHTS.values())})
    if coupon_key:
        coupon = COUPONS[coupon_key]
        start = trial_end or ts
        months = coupon.duration_in_months
        discounts.append(
            {
                "id": recorder.ids.new("di"),
                "coupon": coupon.model_dump(mode="json"),
                "start": start,
                "end": add_months(start, months) if months else None,
            }
        )

    data: dict[str, Any] = {
        "id": recorder.ids.new("sub"),
        "object": "subscription",
        "customer": company.customer_id,
        "created": ts,
        "start_date": ts,
        "status": "trialing" if has_trial else "active",
        "items": {
            "object": "list",
            "data": [
                {
                    "id": recorder.ids.new("si"),
                    "price": catalog.price(tier, interval),
                    "quantity": seats,
                }
            ],
        },
        "trial_start": ts if has_trial else None,
        "trial_end": trial_end,
        "cancel_at_period_end": False,
        "canceled_at": None,
        "ended_at": None,
        "cancellation_details": {"reason": None},
        "discounts": discounts,
    }
    return SubscriptionState(recorder, data)
