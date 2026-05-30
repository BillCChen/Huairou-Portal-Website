import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


API_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("APP_DATA_DIR", API_DIR / "data"))


class Settings(BaseSettings):
    app_name: str = "Portal Website API"
    api_prefix: str = "/api/v1"
    secret_key: str = "change-this-in-production"
    access_token_expire_minutes: int = Field(default=180, ge=1)
    login_lockout_enabled: bool = True
    login_lockout_account_ip_failures: int = Field(default=10, ge=1, le=1000)
    login_lockout_ip_failures: int = Field(default=30, ge=1, le=5000)
    login_lockout_window_hours: int = Field(default=24, ge=1, le=168)
    login_lockout_duration_hours: int = Field(default=24, ge=1, le=168)
    login_lockout_email_cooldown_hours: int = Field(default=24, ge=1, le=168)
    database_url: str = f"sqlite:///{(DATA_DIR / 'portal_test.db').as_posix()}"
    cors_origins: str = "http://localhost:3100,http://127.0.0.1:3100,http://localhost:5174,http://127.0.0.1:5174"
    storage_root: str = str(DATA_DIR / "files")
    upload_dir: str = "uploads"
    file_scan_provider: str = "mock"
    clamav_host: str = "127.0.0.1"
    clamav_port: int = Field(default=3310, ge=1, le=65535)
    clamav_timeout_seconds: float = Field(default=30.0, ge=1.0, le=300.0)
    file_scan_worker_limit: int = Field(default=20, ge=1, le=1000)
    file_scan_worker_retries: int = Field(default=2, ge=0, le=10)
    file_scan_worker_retry_delay_seconds: float = Field(default=5.0, ge=0.0, le=300.0)
    export_dir: str = "exports"
    report_dir: str = "reports"
    backup_dir: str = "backup"
    admin_username: str = "admin"
    admin_password: str = "ChangeMe123!"
    admin_real_name: str = "系统管理员"
    sms_test_code: str = "123456"
    password_reset_enabled: bool = True
    password_reset_token_ttl_minutes: int = 60
    password_reset_dev_outbox_dir: str = str(DATA_DIR / "tmp" / "mail_outbox")
    public_frontend_base_url: str = "http://127.0.0.1:3100"
    email_provider: str = "dev_outbox"
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_from_name: str = "Portal Website"
    smtp_use_tls: bool = False
    smtp_use_starttls: bool = True
    smtp_timeout_seconds: float = Field(default=10.0, ge=1.0, le=60.0)
    smtp_require_auth: bool = True
    init_sample_data: bool = True
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
