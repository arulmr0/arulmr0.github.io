"""Application settings.

Every value can be overridden with an environment variable prefixed ``HFS_``
(for example ``HFS_DATABASE_URL``). Defaults are safe for local development.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HFS_", env_file=".env", extra="ignore")

    app_name: str = "Hotel Food Service"
    database_url: str = "sqlite:///./hfs.db"
    secret_key: str = "dev-only-secret-change-me-before-going-live-0123456789"
    bcrypt_rounds: int = 12
    access_token_minutes: int = 480
    currency: str = "INR"

    # Sales
    tax_rate_percent: float = 5.0
    # When False, paying an order that would drive an ingredient below zero is refused.
    allow_negative_stock: bool = False

    # Payroll policy
    standard_hours_per_day: float = 8.0
    overtime_multiplier: float = 1.5
    statutory_deduction_percent: float = 12.0  # e.g. provident fund on basic pay
    allowance_percent: float = 10.0  # flat allowance on basic pay


@lru_cache
def get_settings() -> Settings:
    return Settings()
