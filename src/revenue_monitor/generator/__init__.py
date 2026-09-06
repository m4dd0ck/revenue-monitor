"""Seeded generator for Stripe-shaped billing data."""

import random
import shutil
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from revenue_monitor.generator.catalog import build_catalog
from revenue_monitor.generator.ids import IdFactory
from revenue_monitor.generator.journey import simulate
from revenue_monitor.generator.lifecycle import DAY, Recorder
from revenue_monitor.models import MODEL_BY_OBJECT
from revenue_monitor.raw_io import RAW_OBJECTS, write_jsonl

GENERATED_FILE = "generated.jsonl"


def generate(seed: int, start: date, end: date, out_dir: Path) -> dict[str, int]:
    """Simulate the business and write one JSONL file per Stripe object.

    Args:
        seed: RNG seed. The same seed and dates always produce identical files.
        start: First day signups can happen.
        end: Last day of the simulation (inclusive).
        out_dir: Raw directory; ``<out_dir>/<object>/`` is cleared before writing.

    Returns:
        Record count per object.

    Raises:
        ValueError: If ``end`` is not after ``start`` or a record fails validation.
    """
    if end <= start:
        raise ValueError(f"end ({end}) must be after start ({start})")
    start_ts = int(datetime.combine(start, time(), UTC).timestamp())
    end_ts = int(datetime.combine(end + timedelta(days=1), time(), UTC).timestamp()) - 1

    rng = random.Random(seed)
    ids = IdFactory(rng)
    recorder = Recorder(ids)
    catalog = build_catalog(ids, start_ts - 30 * DAY)
    simulate(rng, recorder, catalog, start_ts, end_ts)

    records: dict[str, list[dict[str, Any]]] = {
        "customers": recorder.customers,
        "products": catalog.products,
        "prices": list(catalog.prices.values()),
        "subscriptions": [state.data for state in recorder.subscriptions],
        "invoices": recorder.invoices,
        "charges": recorder.charges,
        "refunds": recorder.refunds,
        "events": recorder.events,
    }
    counts: dict[str, int] = {}
    for name in RAW_OBJECTS:
        model = MODEL_BY_OBJECT[name]
        rows = sorted(records[name], key=lambda row: (row["created"], row["id"]))
        for row in rows:
            model.model_validate(row)  # fail fast on anything Stripe would not produce
        object_dir = out_dir / name
        shutil.rmtree(object_dir, ignore_errors=True)
        counts[name] = write_jsonl(object_dir / GENERATED_FILE, rows)
    return counts
