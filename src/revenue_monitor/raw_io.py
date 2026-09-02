"""JSON Lines helpers for the raw layer.

Raw layout is ``<raw_dir>/<object>/<file>.jsonl`` for every name in ``RAW_OBJECTS``. The
generator and the Stripe extractor both write this layout, so loading is source-agnostic.
"""

import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

RAW_OBJECTS: tuple[str, ...] = (
    "customers",
    "products",
    "prices",
    "subscriptions",
    "invoices",
    "charges",
    "refunds",
    "events",
)


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    """Write records as JSON Lines, replacing any existing file.

    Args:
        path: Destination file. Parent directories are created.
        records: JSON-serialisable dicts.

    Returns:
        Number of records written.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, separators=(",", ":"), sort_keys=True))
            handle.write("\n")
            count += 1
    return count


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """Yield records from a JSON Lines file.

    Args:
        path: File to read.

    Yields:
        One dict per non-empty line.
    """
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)
