import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


API_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("APP_DATA_DIR", API_DIR / "data"))


class Settings(BaseSettings):
    app_name: str = "Portal Website API"
    api_prefix: str = "/api/v1"
    secret_key: str = "change-this-in-production"
    access_token_expire_minutes: int = 60 * 8
    database_url: str = f"sqlite:///{(DATA_DIR / 'portal.db').as_posix()}"
    cors_origins: str = "http://localhost:3100,http://localhost:5174"
    storage_root: str = str(DATA_DIR / "files")
    upload_dir: str = "uploads"
    export_dir: str = "exports"
    report_dir: str = "reports"
    backup_dir: str = "backup"
    admin_username: str = "admin"
    admin_password: str = "ChangeMe123!"
    admin_real_name: str = "System Administrator"
    sms_test_code: str = "123456"
    init_sample_data: bool = True
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
