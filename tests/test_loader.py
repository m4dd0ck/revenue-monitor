from pathlib import Path

import duckdb
import pytest

from revenue_monitor.loader import RawDataMissingError, load_raw
from revenue_monitor.raw_io import RAW_OBJECTS


class TestLoadRaw:
    def test_load_creates_raw_tables_with_row_counts(
        self, small_raw_dir: Path, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "warehouse.duckdb"
        counts = load_raw(small_raw_dir, db_path)

        assert set(counts) == set(RAW_OBJECTS)
        assert all(count > 0 for count in counts.values())
        with duckdb.connect(str(db_path), read_only=True) as connection:
            row = connection.execute(
                "select payload ->> '$.object', source_file from raw.subscriptions limit 1"
            ).fetchone()
        assert row is not None
        assert row[0] == "subscription"
        assert row[1].endswith("generated.jsonl")

    def test_reload_replaces_rather_than_appends(self, small_raw_dir: Path, tmp_path: Path) -> None:
        db_path = tmp_path / "warehouse.duckdb"
        first = load_raw(small_raw_dir, db_path)
        assert load_raw(small_raw_dir, db_path) == first

    def test_load_without_generated_data_raises(self, tmp_path: Path) -> None:
        with pytest.raises(RawDataMissingError, match="customers"):
            load_raw(tmp_path / "empty", tmp_path / "warehouse.duckdb")
