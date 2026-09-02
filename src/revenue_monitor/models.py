"""Pydantic models for the Stripe billing objects this project reads.

Models cover only the fields the pipeline relies on. Extra fields are kept (``extra="allow"``)
because the real API returns far more than we model, and the raw layer stores full payloads.
"""

from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

SubscriptionStatus = Literal[
    "trialing",
    "active",
    "past_due",
    "canceled",
    "unpaid",
    "incomplete",
    "incomplete_expired",
    "paused",
]
CancellationReason = Literal["cancellation_requested", "payment_failed", "payment_disputed"]
InvoiceStatus = Literal["draft", "open", "paid", "uncollectible", "void"]


class StripeModel(BaseModel):
    """Base for top-level Stripe objects."""

    model_config = ConfigDict(extra="allow")


class Customer(StripeModel):
    """A paying (or trialing) company."""

    id: str = Field(pattern=r"^cus_")
    object: Literal["customer"] = "customer"
    created: int
    email: str
    name: str
    metadata: dict[str, str] = Field(default_factory=dict)


class Product(StripeModel):
    """A plan tier, e.g. Starter."""

    id: str = Field(pattern=r"^prod_")
    object: Literal["product"] = "product"
    created: int
    name: str
    metadata: dict[str, str] = Field(default_factory=dict)


class Recurring(BaseModel):
    """Billing cadence of a price."""

    interval: Literal["month", "year"]
    interval_count: int = 1


class Price(StripeModel):
    """Per-seat price for a product at one billing interval."""

    id: str = Field(pattern=r"^price_")
    object: Literal["price"] = "price"
    created: int
    product: str
    unit_amount: int = Field(ge=0)
    currency: str = "usd"
    recurring: Recurring
    nickname: str | None = None


class Coupon(BaseModel):
    """Percent-off coupon. Amount-off coupons are not generated."""

    model_config = ConfigDict(extra="allow")

    id: str
    percent_off: float = Field(gt=0, le=100)
    duration: Literal["once", "repeating", "forever"]
    duration_in_months: int | None = None

    @model_validator(mode="after")
    def repeating_needs_months(self) -> Self:
        if (self.duration == "repeating") != (self.duration_in_months is not None):
            raise ValueError("duration_in_months is required for, and only for, repeating coupons")
        return self


class Discount(BaseModel):
    """A coupon applied to a subscription over a time window."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(pattern=r"^di_")
    coupon: Coupon
    start: int
    end: int | None = None


class SubscriptionItem(BaseModel):
    """One priced line of a subscription. Stripe embeds the full price object."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(pattern=r"^si_")
    price: Price
    quantity: int = Field(ge=1)


class ItemList(BaseModel):
    """Stripe list wrapper around subscription items."""

    model_config = ConfigDict(extra="allow")

    object: Literal["list"] = "list"
    data: list[SubscriptionItem]


class CancellationDetails(BaseModel):
    """Why a subscription ended."""

    model_config = ConfigDict(extra="allow")

    reason: CancellationReason | None = None


class Subscription(StripeModel):
    """A customer's recurring plan."""

    id: str = Field(pattern=r"^sub_")
    object: Literal["subscription"] = "subscription"
    customer: str
    created: int
    start_date: int
    status: SubscriptionStatus
    items: ItemList
    trial_start: int | None = None
    trial_end: int | None = None
    cancel_at_period_end: bool = False
    canceled_at: int | None = None
    ended_at: int | None = None
    cancellation_details: CancellationDetails = Field(default_factory=CancellationDetails)
    discounts: list[Discount] = Field(default_factory=list)

    @model_validator(mode="after")
    def status_fields_are_consistent(self) -> Self:
        if self.status == "canceled" and (self.canceled_at is None or self.ended_at is None):
            raise ValueError("canceled subscriptions need canceled_at and ended_at")
        if self.status == "trialing" and self.trial_end is None:
            raise ValueError("trialing subscriptions need trial_end")
        return self


class Invoice(StripeModel):
    """Bill for one subscription period."""

    id: str = Field(pattern=r"^in_")
    object: Literal["invoice"] = "invoice"
    customer: str
    subscription: str | None = None
    created: int
    period_start: int
    period_end: int
    status: InvoiceStatus
    amount_due: int = Field(ge=0)
    amount_paid: int = Field(ge=0)
    attempt_count: int = Field(ge=0)
    billing_reason: str | None = None


class Charge(StripeModel):
    """A card payment attempt."""

    id: str = Field(pattern=r"^ch_")
    object: Literal["charge"] = "charge"
    customer: str | None = None
    created: int
    amount: int = Field(ge=0)
    currency: str = "usd"
    status: Literal["succeeded", "failed", "pending"]
    failure_code: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class Refund(StripeModel):
    """Money returned against a charge."""

    id: str = Field(pattern=r"^re_")
    object: Literal["refund"] = "refund"
    charge: str | None = None
    created: int
    amount: int = Field(ge=0)
    reason: str | None = None


class EventData(BaseModel):
    """Snapshot of the object at event time, plus the fields that changed."""

    model_config = ConfigDict(extra="allow")

    object: dict[str, Any]
    previous_attributes: dict[str, Any] | None = None


class Event(StripeModel):
    """A change notification. Subscription events are the source of history."""

    id: str = Field(pattern=r"^evt_")
    object: Literal["event"] = "event"
    type: str
    created: int
    data: EventData


MODEL_BY_OBJECT: dict[str, type[StripeModel]] = {
    "customers": Customer,
    "products": Product,
    "prices": Price,
    "subscriptions": Subscription,
    "invoices": Invoice,
    "charges": Charge,
    "refunds": Refund,
    "events": Event,
}
