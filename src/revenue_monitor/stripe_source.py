"""Extract billing objects from a Stripe test-mode account into the raw layout.

Incremental by ``created``: each resource remembers the newest ``created`` it has seen and only
asks for newer objects next run. Objects that change after creation (subscriptions, invoices)
are therefore tracked through ``events``, which Stripe keeps for 30 days only.
"""

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from revenue_monitor.models import MODEL_BY_OBJECT
from revenue_monitor.raw_io import RAW_OBJECTS, write_jsonl

TEST_KEY_PREFIXES = ("sk_test_", "rk_test_")
STATE_FILE = "_stripe_state.json"

# Extra list parameters per resource. Subscriptions default to non-canceled only, and
# discounts come back as IDs unless expanded.
RESOURCE_PARAMS: dict[str, dict[str, Any]] = {
    "customers": {},
    "products": {},
    "prices": {"type": "recurring"},
    "subscriptions": {"status": "all", "expand": ["data.discounts"]},
    "invoices": {},
    "charges": {},
    "refunds": {},
    "events": {
        "types": [
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        ]
    },
}


class LiveKeyError(ValueError):
    """Raised for anything that is not a Stripe test-mode key."""


class Page(Protocol):
    def auto_paging_iter(self) -> Iterator[Any]: ...


class ListableResource(Protocol):
    def list(self, params: dict[str, Any]) -> Page: ...


def require_test_key(api_key: str) -> None:
    """Refuse live keys so this can never read a real business's billing data by mistake."""
    if not api_key.startswith(TEST_KEY_PREFIXES):
        raise LiveKeyError("Only Stripe test-mode keys (sk_test_ / rk_test_) are accepted")


def extract(api: Any, raw_dir: Path) -> dict[str, int]:
    """Pull new objects for every raw resource and write them as JSONL.

    Args:
        api: Object exposing one ``ListableResource`` per name, e.g. ``StripeClient(...).v1``.
        raw_dir: Raw directory; files land in ``<raw_dir>/<object>/stripe_<run>.jsonl``.

    Returns:
        Number of new records per resource.

    Raises:
        pydantic.ValidationError: If Stripe returns an object the models reject.
    """
    state_path = raw_dir / STATE_FILE
    state: dict[str, int] = json.loads(state_path.read_text()) if state_path.exists() else {}
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    counts: dict[str, int] = {}

    for name in RAW_OBJECTS:
        resource: ListableResource = getattr(api, name)
        params: dict[str, Any] = {"limit": 100, **RESOURCE_PARAMS[name]}
        if name in state:
            params["created"] = {"gt": state[name]}

        records = []
        for stripe_object in resource.list(params=params).auto_paging_iter():
            payload: dict[str, Any] = stripe_object.to_dict()
            MODEL_BY_OBJECT[name].model_validate(payload)
            records.append(payload)

        if records:
            write_jsonl(raw_dir / name / f"stripe_{run_id}.jsonl", records)
            state[name] = max(record["created"] for record in records)
        counts[name] = len(records)

    raw_dir.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True))
    return counts
