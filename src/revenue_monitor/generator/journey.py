"""Customer journeys: signups, trial outcomes, plan changes, churn and reactivation.

Probabilities are monthly unless stated. They were tuned so the output lands in a plausible
range for a small B2B SaaS: 1-4% monthly logo churn, net revenue retention near 100%.
"""

import math
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from revenue_monitor.generator.billing import Biller
from revenue_monitor.generator.catalog import SEASONALITY, TIER_KEYS, Catalog
from revenue_monitor.generator.lifecycle import (
    DAY,
    Company,
    Recorder,
    SubscriptionState,
    add_months,
    new_customer,
    start_subscription,
)

BASE_SIGNUPS_PER_MONTH = 25.0
MONTHLY_GROWTH = 1.04
TRIAL_CONVERSION = 0.55
MONTHLY_CHURN = {"starter": 0.030, "growth": 0.020, "scale": 0.012}
ANNUAL_RENEWAL_CHURN = 0.15
SWITCH_TO_ANNUAL = 0.005
PAYMENT_FAILURE = 0.035
PAYMENT_RECOVERY = 0.60
DUNNING_DAYS = 21
REACTIVATION = 0.08
# (change, probability) — at most one change per subscription per month
MONTHLY_CHANGES = (
    ("seats_up", 0.040),
    ("seats_down", 0.020),
    ("upgrade", 0.015),
    ("downgrade", 0.008),
)


@dataclass(frozen=True)
class Ending:
    """How a subscription ended."""

    at: int
    is_voluntary: bool


def poisson(rng: random.Random, expected: float) -> int:
    """Knuth's method; fine for the small means used here and needs only ``rng``."""
    threshold = math.exp(-expected)
    count, product = 0, rng.random()
    while product > threshold:
        count += 1
        product *= rng.random()
    return count


def simulate(
    rng: random.Random, recorder: Recorder, catalog: Catalog, start: int, end: int
) -> None:
    """Generate every customer who signs up between ``start`` and ``end``."""
    biller = Biller(rng, recorder, end)
    month_start, month_index = start, 0
    while month_start < end:
        month_end = add_months(month_start, 1)
        month = datetime.fromtimestamp(month_start, UTC).month
        expected = BASE_SIGNUPS_PER_MONTH * MONTHLY_GROWTH**month_index * SEASONALITY[month]
        for _ in range(poisson(rng, expected)):
            signup_at = rng.randrange(month_start, min(month_end, end))
            run_customer(rng, recorder, catalog, biller, signup_at, end)
        month_start, month_index = month_end, month_index + 1


def run_customer(
    rng: random.Random, recorder: Recorder, catalog: Catalog, biller: Biller, ts: int, end: int
) -> None:
    """One customer from signup to the end of the simulation, including any comebacks."""
    company = new_customer(rng, recorder, ts)
    state = start_subscription(rng, recorder, catalog, company, ts)
    while True:
        ending = live_subscription(rng, catalog, biller, company, state, end)
        if ending is None or not ending.is_voluntary or rng.random() >= REACTIVATION:
            return
        comeback_at = ending.at + rng.randint(30, 180) * DAY
        if comeback_at >= end:
            return
        state = start_subscription(rng, recorder, catalog, company, comeback_at, allow_trial=False)


def live_subscription(
    rng: random.Random,
    catalog: Catalog,
    biller: Biller,
    company: Company,
    state: SubscriptionState,
    end: int,
) -> Ending | None:
    """Walk a subscription month by month. Returns how it ended, or None if still live."""
    anchor = state.data["created"]
    if state.status == "trialing":
        trial_end = state.data["trial_end"]
        if trial_end >= end:
            return None
        if rng.random() >= TRIAL_CONVERSION:
            state.cancel(trial_end, "cancellation_requested")
            return None  # never paid, so it is not churn and not eligible for reactivation
        state.activate(trial_end)
        anchor = trial_end

    months_into_anchor = 0
    while True:
        period_start = add_months(anchor, months_into_anchor)
        if period_start >= end:
            return None
        if not state.is_annual or months_into_anchor % 12 == 0:
            if months_into_anchor > 0 and churns_at_renewal(rng, state):
                requested_at = period_start - rng.randint(2, 20) * DAY
                state.schedule_cancel(max(requested_at, state.last_event_at + 1))
                state.cancel(period_start, "cancellation_requested")
                return Ending(period_start, is_voluntary=True)
            if months_into_anchor > 0 and not state.is_annual and rng.random() < SWITCH_TO_ANNUAL:
                tier = state.price["product"]
                state.change_price(period_start, annual_price_for(catalog, tier))
                anchor, months_into_anchor = period_start, 0
            ending = bill_period(rng, biller, state, period_start, months_into_anchor, end)
            if ending is not None or state.status == "past_due":
                return ending
        next_start = add_months(anchor, months_into_anchor + 1)
        maybe_change_plan(rng, catalog, state, period_start, next_start, end)
        months_into_anchor += 1


def churns_at_renewal(rng: random.Random, state: SubscriptionState) -> bool:
    """Voluntary churn decision, taken only when a plan comes up for renewal."""
    if state.is_annual:
        return rng.random() < ANNUAL_RENEWAL_CHURN
    tier = tier_of(state)
    return rng.random() < MONTHLY_CHURN[tier]


def bill_period(
    rng: random.Random,
    biller: Biller,
    state: SubscriptionState,
    period_start: int,
    months_into_anchor: int,
    end: int,
) -> Ending | None:
    """Invoice one period and play out a failed payment if one happens.

    Leaves the subscription ``past_due`` (and returns None) when dunning is still running at
    the end of the simulation.
    """
    period_end = add_months(period_start, 12 if state.is_annual else 1)
    reason = "subscription_create" if months_into_anchor == 0 else "subscription_cycle"
    invoice = biller.open_invoice(state, period_start, period_end, reason)
    if rng.random() >= PAYMENT_FAILURE:
        biller.pay(invoice, period_start)
        return None

    biller.fail(invoice, period_start)
    state.mark_past_due(period_start + 3600)
    if rng.random() < PAYMENT_RECOVERY:
        recovered_at = period_start + rng.randint(3, 14) * DAY
        if recovered_at < end:
            biller.pay(invoice, recovered_at)
            state.activate(recovered_at)
        return None
    gave_up_at = period_start + DUNNING_DAYS * DAY
    if gave_up_at >= end:
        return None
    biller.write_off(invoice)
    state.cancel(gave_up_at, "payment_failed")
    return Ending(gave_up_at, is_voluntary=False)


def maybe_change_plan(
    rng: random.Random,
    catalog: Catalog,
    state: SubscriptionState,
    month_start: int,
    next_month_start: int,
    end: int,
) -> None:
    """Apply at most one seat or tier change on a random day inside the month."""
    change_at = rng.randint(month_start + DAY, next_month_start - DAY)
    roll = rng.random()
    for change, probability in MONTHLY_CHANGES:
        if roll >= probability:
            roll -= probability
            continue
        if change_at >= end or change_at <= state.last_event_at:
            return
        tier_index = TIER_KEYS.index(tier_of(state))
        interval = "year" if state.is_annual else "month"
        if change == "seats_up":
            state.change_quantity(change_at, state.quantity + rng.randint(1, 3))
        elif change == "seats_down" and state.quantity > 1:
            state.change_quantity(change_at, state.quantity - rng.randint(1, 2))
        elif change == "upgrade" and tier_index < len(TIER_KEYS) - 1:
            state.change_price(change_at, catalog.price(TIER_KEYS[tier_index + 1], interval))
        elif change == "downgrade" and tier_index > 0:
            state.change_price(change_at, catalog.price(TIER_KEYS[tier_index - 1], interval))
        return


def tier_of(state: SubscriptionState) -> str:
    """Tier key from the price nickname, e.g. ``Growth Monthly`` → ``growth``."""
    return str(state.price["nickname"]).split()[0].lower()


def annual_price_for(catalog: Catalog, product_id: str) -> dict[str, Any]:
    """The annual price of the same product."""
    for (tier, interval), price in catalog.prices.items():
        if price["product"] == product_id and interval == "year":
            return catalog.price(tier, interval)
    raise KeyError(f"No annual price for product {product_id}")
