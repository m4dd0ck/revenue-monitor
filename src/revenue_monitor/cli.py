"""``revmon`` command line interface."""

from datetime import date, datetime
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from revenue_monitor.config import Settings
from revenue_monitor.generator import generate as run_generator

app = typer.Typer(
    help="SaaS revenue analytics on Stripe-shaped billing data.", no_args_is_help=True
)
console = Console()


@app.callback()
def main() -> None:
    """SaaS revenue analytics on Stripe-shaped billing data."""


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def print_counts(title: str, counts: dict[str, int]) -> None:
    table = Table(title=title)
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
    print_counts(f"Generated into {settings.raw_dir}", counts)
