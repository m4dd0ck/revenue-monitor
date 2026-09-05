"""Invoices, charges and refunds for subscription billing periods.

No proration: an invoice is issued at each period start for the plan in force at that moment.
Mid-period plan changes affect MRR immediately but are not billed until the next period.
"""

import random
from typing import Any

from revenue_monitor.generator.lifecycle import DAY, Recorder, SubscriptionState

REFUND_RATE = 0.01
FAILURE_CODES = ("card_declined", "insufficient_funds", "expired_card")


class Biller:
    """Issues invoices and records payment attempts against them."""

    def __init__(self, rng: random.Random, recorder: Recorder, end: int) -> None:
        self._rng = rng
        self._recorder = recorder
        self._end = end

    def open_invoice(
        self, state: SubscriptionState, period_start: int, period_end: int, reason: str
    ) -> dict[str, Any]:
        """Create an open invoice for the plan in force at ``period_start``."""
        gross = state.price["unit_amount"] * state.quantity
        amount_due = round(gross * (1 - state.percent_off_at(period_start) / 100))
        invoice: dict[str, Any] = {
            "id": self._recorder.ids.new("in"),
            "object": "invoice",
            "customer": state.data["customer"],
            "subscription": state.id,
            "created": period_start,
            "period_start": period_start,
            "period_end": period_end,
            "status": "open",
            "amount_due": amount_due,
            "amount_paid": 0,
            "attempt_count": 0,
            "billing_reason": reason,
        }
        self._recorder.invoices.append(invoice)
        return invoice

    def pay(self, invoice: dict[str, Any], ts: int) -> None:
        """Successful charge; occasionally refunded later."""
        charge = self._charge(invoice, ts, succeeded=True)
        invoice["status"] = "paid"
        invoice["amount_paid"] = invoice["amount_due"]
        if self._rng.random() < REFUND_RATE:
            self._refund(charge)

    def fail(self, invoice: dict[str, Any], ts: int) -> None:
        """Declined charge; the invoice stays open."""
        self._charge(invoice, ts, succeeded=False)

    def write_off(self, invoice: dict[str, Any]) -> None:
        """Dunning gave up; Stripe marks the invoice uncollectible."""
        invoice["status"] = "uncollectible"

    def _charge(self, invoice: dict[str, Any], ts: int, succeeded: bool) -> dict[str, Any]:
        invoice["attempt_count"] += 1
        charge: dict[str, Any] = {
            "id": self._recorder.ids.new("ch"),
            "object": "charge",
            "customer": invoice["customer"],
            "created": ts,
            "amount": invoice["amount_due"],
            "currency": "usd",
            "status": "succeeded" if succeeded else "failed",
            "failure_code": None if succeeded else self._rng.choice(FAILURE_CODES),
            "metadata": {"invoice": invoice["id"]},
        }
        self._recorder.charges.append(charge)
        return charge

    def _refund(self, charge: dict[str, Any]) -> None:
        refunded_at = charge["created"] + self._rng.randint(1, 20) * DAY
        if refunded_at >= self._end or charge["amount"] == 0:
            return
        is_full = self._rng.random() < 0.7
        amount = (
            charge["amount"] if is_full else round(charge["amount"] * self._rng.uniform(0.1, 0.6))
        )
        self._recorder.refunds.append(
            {
                "id": self._recorder.ids.new("re"),
                "object": "refund",
                "charge": charge["id"],
                "created": refunded_at,
                "amount": amount,
                "reason": "requested_by_customer",
            }
        )
