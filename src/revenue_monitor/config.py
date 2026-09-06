"""Runtime settings, overridable with ``REVMON_*`` environment variables or ``.env``."""

from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paths and credentials used by the CLI."""

    model_config = SettingsConfigDict(env_prefix="REVMON_", env_file=".env", extra="ignore")

    raw_dir: Path = Path("data/raw")
    db_path: Path = Path("data/revenue_monitor.duckdb")
    metrics_dir: Path = Path("metrics")
    stripe_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("STRIPE_API_KEY", "REVMON_STRIPE_API_KEY")
    )
