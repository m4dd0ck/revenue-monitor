"""Load raw JSONL into the DuckDB ``raw`` schema.

Each raw table keeps the full JSON payload plus the file it came from. Parsing happens in dbt
staging, so a field Stripe adds or renames never breaks the load.
"""

from pathlib import Path

import duckdb

from revenue_monitor.raw_io import RAW_OBJECTS


class RawDataMissingError(FileNotFoundError):
    """Raised when an object has no JSONL files to load."""


def load_raw(raw_dir: Path, db_path: Path) -> dict[str, int]:
    """Replace every ``raw.<object>`` table with the JSONL files on disk.

    Args:
        raw_dir: Directory holding ``<object>/*.jsonl``.
        db_path: DuckDB file; created if missing.

    Returns:
        Row count per raw table.

    Raises:
        RawDataMissingError: If any object has no files (run ``revmon generate`` first).
    """
    missing = [name for name in RAW_OBJECTS if not any((raw_dir / name).glob("*.jsonl"))]
    if missing:
        raise RawDataMissingError(f"No JSONL files in {raw_dir} for: {', '.join(missing)}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    with duckdb.connect(str(db_path)) as connection:
        connection.execute("create schema if not exists raw")
        for name in RAW_OBJECTS:
            # Table names come from the fixed RAW_OBJECTS allowlist, so interpolation is safe.
            connection.execute(
                f"""
                create or replace table raw.{name} as
                select json as payload, filename as source_file, current_timestamp as loaded_at
                from read_json_objects(?, format = 'newline_delimited', filename = true)
                """,
                [str(raw_dir / name / "*.jsonl")],
            )
            row = connection.execute(f"select count(*) from raw.{name}").fetchone()
            counts[name] = row[0] if row else 0
    return counts
