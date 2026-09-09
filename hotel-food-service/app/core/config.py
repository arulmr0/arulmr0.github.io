"""Application settings.

Every value can be overridden with an environment variable prefixed ``HFS_``
(for example ``HFS_DATABASE_URL``). Defaults are safe for local development.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET_KEY = "dev-only-secret-change-me-before-going-live-0123456789"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HFS_", env_file=".env", extra="ignore")

    app_name: str = "Hotel Food Service"
    database_url: str = "sqlite:///./hfs.db"
    secret_key: str = DEV_SECRET_KEY
    bcrypt_rounds: int = 12
    access_token_minutes: int = 480
    currency: str = "INR"

    # Bill header / footer
    business_name: str = "Hotel Food Service"
    business_address: str | None = None
    tax_id: str | None = None  # e.g. GSTIN
    bill_footer: str | None = "Thank you for dining with us"

    # First-run bootstrap: when set, this admin account is created at start-up if it
    # does not exist. This is how a fresh production database gets its first login.
    admin_email: str | None = None
    admin_password: str | None = None

    # Operations
    # Load the demo dataset on first boot when the database is empty (one-click deploys).
    seed_on_start: bool = False

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
