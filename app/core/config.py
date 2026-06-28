from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Early Literacy MVP Backend"
    environment: Literal["local", "development", "staging", "production", "test"] = "local"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite+pysqlite:///./app.db"
    access_token_secret: str = "unsafe-access-secret"
    refresh_token_secret: str = "unsafe-refresh-secret"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    local_storage_path: str = "./local_storage"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    azure_blob_connection_string: str | None = None
    azure_blob_container: str = Field(
        default="assessment-files", validation_alias="AZURE_STORAGE_CONTAINER_NAME"
    )
    azure_storage_assessment_container_name: str = Field(
        default="assessment-files", validation_alias="AZURE_STORAGE_ASSESSMENT_CONTAINER_NAME"
    )
    azure_vision_endpoint: str | None = None
    azure_vision_key: str | None = None
    azure_speech_key: str | None = None
    azure_speech_region: str | None = None
    azure_speech_endpoint: str | None = None

    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    email_from: str = "noreply@tamizai.com"
    reset_token_expire_minutes: int = 5

    azure_blob_sas_expiration_minutes: int = 5
    azure_blob_template_folder: str = "general_consent"

    assessment_stt_provider: str = "faster_whisper"
    whisper_model_size: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_language: str = "es"
    whisper_beam_size: int = 5
    whisper_word_timestamps: bool = True
    whisper_vad_filter: bool = False
    whisper_model_download_root: str | None = None
    whisper_low_confidence_threshold: float = -1.0


@lru_cache
def get_settings() -> Settings:
    return Settings()

