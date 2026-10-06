"""End-to-end: generate → load → dbt build → MetricForge, in a temp directory."""

import os
import subprocess
from datetime import date
from pathlib import Path

import duckdb
import pytest

from revenue_monitor.generator import generate
from revenue_monitor.loader import load_raw
from revenue_monitor.metrics import monthly_metrics

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def built_warehouse(tmp_path_factory: pytest.TempPathFactory) -> Path:
    workdir = tmp_path_factory.mktemp("pipeline")
    raw_dir = workdir / "raw"
    # Reason: dbt-duckdb names the catalog after the file, and views reference it, so keep
    # the production file name even in a temp directory.
    db_path = workdir / "revenue_monitor.duckdb"
    generate(seed=7, start=date(2024, 1, 1), end=date(2025, 6, 30), out_dir=raw_dir)
    load_raw(raw_dir, db_path)

    result = subprocess.run(
        [
            "dbt",
            "build",
            "--profiles-dir",
            ".",
            "--target-path",
            str(workdir / "target"),
            "--log-path",
            str(workdir / "logs"),
        ],  # fmt: skip
        cwd=PROJECT_ROOT,
        env={**os.environ, "REVMON_DB_PATH": str(db_path)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout[-4000:]
    return db_path


@pytest.mark.integration
def test_dbt_build_produces_every_mart(built_warehouse: Path) -> None:
    with duckdb.connect(str(built_warehouse), read_only=True) as connection:
        marts = {
            row[0]
            for row in connection.execute(
                "select table_name from information_schema.tables where table_schema = 'marts'"
            ).fetchall()
        }
    assert marts == {
        "mart_mrr_bridge",
        "mart_cohort_retention",
        "mart_plan_summary",
        "mart_churn_analysis",
        "mart_customer_health",
    }


@pytest.mark.integration
def test_metricforge_mrr_matches_bridge_mart(built_warehouse: Path) -> None:
    with duckdb.connect(str(built_warehouse), read_only=True) as connection:
        row = connection.execute(
            "select ending_mrr, customers_end from marts.mart_mrr_bridge "
            "order by month desc limit 1"
        ).fetchone()
    assert row is not None
    mart_mrr, mart_customers = row

    latest = monthly_metrics(
        PROJECT_ROOT / "metrics", built_warehouse, ["total_mrr", "paying_customers"], 1
    )[0]
    assert latest["total_mrr"] == pytest.approx(mart_mrr, abs=0.01)
    assert latest["paying_customers"] == mart_customers


@pytest.mark.integration
def test_metricforge_gross_churn_matches_bridge_mart(built_warehouse: Path) -> None:
    # Reason: the README and dashboard define gross revenue churn as (churned + contraction)
    # over starting MRR; the YAML metric must agree or the CLI prints a different number.
    with duckdb.connect(str(built_warehouse), read_only=True) as connection:
        row = connection.execute(
            "select gross_mrr_churn_pct from marts.mart_mrr_bridge order by month desc limit 1"
        ).fetchone()
    assert row is not None
    mart_rate = row[0] / 100

    latest = monthly_metrics(
        PROJECT_ROOT / "metrics", built_warehouse, ["gross_mrr_churn_rate"], 1
    )[0]
    assert latest["gross_mrr_churn_rate"] == pytest.approx(mart_rate, abs=0.0001)
