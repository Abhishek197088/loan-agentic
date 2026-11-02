import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # LLM Settings
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model_name: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL_NAME")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")

    # Application Settings
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    database_url: str = Field(default=f"sqlite:///{BASE_DIR}/loan_underwriting.db", alias="DATABASE_URL")

    # Underwriting Policy Defaults
    max_foir_percent: float = Field(default=40.0, alias="MAX_FOIR_PERCENT")
    default_annual_interest_rate: float = Field(default=12.0, alias="DEFAULT_ANNUAL_INTEREST_RATE")
    min_allowed_tenure_months: int = Field(default=6, alias="MIN_ALLOWED_TENURE_MONTHS")
    max_allowed_tenure_months: int = Field(default=84, alias="MAX_ALLOWED_TENURE_MONTHS")
    min_loan_amount: float = Field(default=10000.0, alias="MIN_LOAN_AMOUNT")
    max_loan_amount: float = Field(default=10000000.0, alias="MAX_LOAN_AMOUNT")
    allow_counter_offer_tenure_extension: bool = Field(default=True, alias="ALLOW_COUNTER_OFFER_TENURE_EXTENSION")

    # Security & File Uploads
    max_upload_size_mb: int = Field(default=5, alias="MAX_UPLOAD_SIZE_MB")
    allowed_extensions: str = Field(default="pdf", alias="ALLOWED_EXTENSIONS")
    enable_strict_prompt_injection_defense: bool = Field(default=True, alias="ENABLE_STRICT_PROMPT_INJECTION_DEFENSE")

    # Data paths
    data_dir: Path = BASE_DIR / "data"
    credit_history_path: Path = BASE_DIR / "data" / "credit_history.json"
    uploads_dir: Path = BASE_DIR / "uploads"


settings = Settings()
