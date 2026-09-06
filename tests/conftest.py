from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from revenue_monitor.generator import generate
from revenue_monitor.raw_io import RAW_OBJECTS, read_jsonl

SMALL_START = date(2024, 1, 1)
SMALL_END = date(2025, 12, 31)

RawData = dict[str, list[dict[str, Any]]]


def read_raw(raw_dir: Path) -> RawData:
    return {name: list(read_jsonl(raw_dir / name / "generated.jsonl")) for name in RAW_OBJECTS}


@pytest.fixture(scope="session")
def small_raw_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Two years of generated data, shared by every test that only reads it."""
    raw_dir = tmp_path_factory.mktemp("raw")
    generate(seed=7, start=SMALL_START, end=SMALL_END, out_dir=raw_dir)
    return raw_dir


@pytest.fixture(scope="session")
def small_run(small_raw_dir: Path) -> RawData:
    return read_raw(small_raw_dir)


@pytest.fixture
def run_generator(tmp_path: Path) -> Callable[[int], RawData]:
    def _run(seed: int) -> RawData:
        out = tmp_path / f"seed_{seed}"
        generate(seed=seed, start=SMALL_START, end=date(2024, 6, 30), out_dir=out)
        return read_raw(out)

    return _run
