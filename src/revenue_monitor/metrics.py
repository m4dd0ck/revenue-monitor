"""Query revenue metrics through MetricForge."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from metricforge import MetricStore

DEFAULT_METRICS: tuple[str, ...] = (
    "total_mrr",
    "net_new_mrr_total",
    "paying_customers",
    "arpa",
    "logo_churn_rate",
    "net_revenue_retention",
)
# Ratio metrics come back as fractions; shown as percentages.
RATE_METRICS = frozenset({"logo_churn_rate", "gross_mrr_churn_rate", "net_revenue_retention"})


COLUMN_LABELS = {
    "total_mrr": "MRR",
    "arr": "ARR",
    "net_new_mrr_total": "Net new MRR",
    "paying_customers": "Customers",
    "arpa": "ARPA",
    "logo_churn_rate": "Logo churn",
    "net_revenue_retention": "NRR",
}


class WarehouseMissingError(FileNotFoundError):
    """Raised when the DuckDB file has not been built yet."""


def monthly_metrics(
    metrics_dir: Path, db_path: Path, metrics: Sequence[str], last_months: int
) -> list[dict[str, Any]]:
    """Return one row per month for the requested metrics, most recent months only.

    Args:
        metrics_dir: Directory of MetricForge YAML definitions.
        db_path: Built DuckDB warehouse.
        metrics: Metric names defined in ``metrics_dir``.
        last_months: How many trailing months to return.

    Returns:
        Rows with ``month`` plus one key per metric, oldest first.

    Raises:
        WarehouseMissingError: If ``db_path`` does not exist (run the pipeline first).
    """
    if not db_path.exists():
        raise WarehouseMissingError(f"{db_path} not found; run revmon load and dbt build first")
    store = MetricStore(metrics_dir, str(db_path))
    try:
        result = store.query(metrics=list(metrics), dimensions=["month"], time_grain="month")
    finally:
        store.executor.conn.close()
    rows: list[dict[str, Any]] = result.data
    return rows[-last_months:]


def format_value(metric: str, value: float | int | None) -> str:
    """Human-readable cell: percentages for rates, whole dollars for money, counts as-is."""
    if value is None:
        return "-"
    if metric in RATE_METRICS:
        return f"{value * 100:.1f}%"
    if isinstance(value, int):
        return f"{value:,}"
    return f"${value:,.0f}"
