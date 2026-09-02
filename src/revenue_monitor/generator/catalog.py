"""Fixed product catalog and reference data for the fictional SaaS.

The company sells per-seat plans in three tiers. Annual prices are ten times the monthly
price (two months free), which is the most common SaaS annual discount.
"""

from dataclasses import dataclass
from typing import Any

from revenue_monitor.generator.ids import IdFactory
from revenue_monitor.models import Coupon, Price, Product, Recurring


@dataclass(frozen=True)
class Tier:
    """A plan tier and its monthly per-seat price in cents."""

    key: str
    name: str
    monthly_seat_cents: int


TIERS: tuple[Tier, ...] = (
    Tier("starter", "Starter", 2900),
    Tier("growth", "Growth", 5900),
    Tier("scale", "Scale", 9900),
)
TIER_KEYS: tuple[str, ...] = tuple(tier.key for tier in TIERS)
INTERVALS: tuple[str, ...] = ("month", "year")
ANNUAL_MULTIPLIER = 10

COUPONS: dict[str, Coupon] = {
    "LAUNCH20": Coupon(id="LAUNCH20", percent_off=20, duration="repeating", duration_in_months=3),
    "PARTNER10": Coupon(id="PARTNER10", percent_off=10, duration="forever"),
}

# Signup volume multiplier by calendar month: strong January and September, quiet summer
# and December, which is typical for B2B software buying cycles.
SEASONALITY: dict[int, float] = {
    1: 1.15, 2: 1.05, 3: 1.10, 4: 1.00, 5: 1.00, 6: 0.95,
    7: 0.85, 8: 0.85, 9: 1.10, 10: 1.05, 11: 0.95, 12: 0.75,
}  # fmt: skip

COUNTRY_WEIGHTS: dict[str, float] = {
    "US": 0.58, "GB": 0.10, "CA": 0.08, "DE": 0.07, "AU": 0.05,
    "FR": 0.04, "NL": 0.03, "SE": 0.02, "IE": 0.02, "NZ": 0.01,
}  # fmt: skip

INDUSTRIES: tuple[str, ...] = (
    "Software", "Agency", "E-commerce", "Healthcare", "Finance",
    "Education", "Logistics", "Real Estate", "Manufacturing", "Nonprofit",
)  # fmt: skip

# (band label, weight, min seats, max seats, tier weights starter/growth/scale)
EMPLOYEE_BANDS: tuple[tuple[str, float, int, int, tuple[float, float, float]], ...] = (
    ("1-10", 0.45, 1, 5, (0.75, 0.22, 0.03)),
    ("11-50", 0.35, 3, 15, (0.55, 0.35, 0.10)),
    ("51-200", 0.15, 8, 40, (0.35, 0.45, 0.20)),
    ("201-1000", 0.05, 20, 80, (0.20, 0.45, 0.35)),
)

NAME_PREFIXES: tuple[str, ...] = (
    "Blue", "North", "Bright", "Iron", "Silver", "Clear", "Summit", "Harbor", "Pine", "Cedar",
    "Vector", "Signal", "Lumen", "Atlas", "Nimbus", "Copper", "Orbit", "Maple", "Granite", "Kite",
    "Rapid", "Quiet", "Golden", "Crimson", "Delta", "Echo", "Beacon", "Field", "Stone", "River",
)  # fmt: skip
NAME_SUFFIXES: tuple[str, ...] = (
    "Labs", "Works", "Systems", "Health", "Logistics", "Studio", "Partners", "Analytics",
    "Foods", "Robotics", "Media", "Supply", "Energy", "Capital", "Learning", "Craft", "Group",
    "Digital", "Freight", "Clinic", "Outdoors", "Legal", "Homes", "Retail", "Bio",
)  # fmt: skip


@dataclass
class Catalog:
    """Products and prices, keyed for lookup during simulation."""

    products: list[dict[str, Any]]
    prices: dict[tuple[str, str], dict[str, Any]]  # (tier key, interval) → price payload

    def price(self, tier_key: str, interval: str) -> dict[str, Any]:
        """Return the price payload for a tier at a billing interval."""
        return self.prices[(tier_key, interval)]


def build_catalog(ids: IdFactory, created: int) -> Catalog:
    """Create the three products and six prices.

    Args:
        ids: ID factory, so catalog IDs come from the same seeded stream as everything else.
        created: Unix timestamp to stamp on every catalog object.

    Returns:
        Catalog with validated product and price payloads.
    """
    products: list[dict[str, Any]] = []
    prices: dict[tuple[str, str], dict[str, Any]] = {}
    for tier in TIERS:
        product = Product(
            id=ids.new("prod"), created=created, name=tier.name, metadata={"tier": tier.key}
        )
        products.append(product.model_dump(mode="json"))
        for interval in INTERVALS:
            multiplier = ANNUAL_MULTIPLIER if interval == "year" else 1
            price = Price(
                id=ids.new("price"),
                created=created,
                product=product.id,
                unit_amount=tier.monthly_seat_cents * multiplier,
                recurring=Recurring.model_validate({"interval": interval}),
                nickname=f"{tier.name} {'Annual' if interval == 'year' else 'Monthly'}",
            )
            prices[(tier.key, interval)] = price.model_dump(mode="json")
    return Catalog(products=products, prices=prices)
