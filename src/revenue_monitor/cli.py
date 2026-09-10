"""``revmon`` command line interface."""

from datetime import date, datetime
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from revenue_monitor.config import Settings
from revenue_monitor.generator import generate as run_generator
from revenue_monitor.loader import load_raw
from revenue_monitor.stripe_source import LiveKeyError, extract, require_test_key

app = typer.Typer(
    help="SaaS revenue analytics on Stripe-shaped billing data.", no_args_is_help=True
)
console = Console()


@app.callback()
def main() -> None:
    """SaaS revenue analytics on Stripe-shaped billing data."""


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def print_counts(title: str, counts: dict[str, int], location: str) -> None:
    table = Table(title=title, caption=location)
    table.add_column("Object")
    table.add_column("Rows", justify="right")
    for name, count in counts.items():
        table.add_row(name, f"{count:,}")
    console.print(table)


@app.command()
def generate(
    seed: Annotated[int, typer.Option(help="RNG seed; same seed, same data.")] = 42,
    start: Annotated[str, typer.Option(help="First signup day (YYYY-MM-DD).")] = "2023-09-01",
    end: Annotated[str, typer.Option(help="Last simulated day (YYYY-MM-DD).")] = "2026-08-31",
) -> None:
    """Generate synthetic Stripe data into the raw directory."""
    settings = Settings()
    counts = run_generator(seed, parse_date(start), parse_date(end), settings.raw_dir)
    print_counts("Generated", counts, str(settings.raw_dir))


@app.command()
def load() -> None:
    """Load raw JSONL into the DuckDB raw schema."""
    settings = Settings()
    counts = load_raw(settings.raw_dir, settings.db_path)
    print_counts("Loaded", counts, str(settings.db_path))


@app.command()
def stripe() -> None:
    """Pull objects from a Stripe test-mode account (needs STRIPE_API_KEY)."""
    settings = Settings()
    if settings.stripe_api_key is None:
        raise typer.BadParameter("Set STRIPE_API_KEY to a test-mode key (sk_test_...)")
    api_key = settings.stripe_api_key.get_secret_value()
    try:
        require_test_key(api_key)
    except LiveKeyError as error:
        raise typer.BadParameter(str(error)) from error
    try:
        import stripe as stripe_sdk
    except ImportError as error:
        raise typer.BadParameter("Install the extra: uv sync --extra stripe") from error
    counts = extract(stripe_sdk.StripeClient(api_key).v1, settings.raw_dir)
    print_counts("Pulled from Stripe", counts, str(settings.raw_dir))
