from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from the environment. No defaults for secrets."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str
    jwt_expiry_minutes: int = 60
    jwt_algorithm: str = "HS256"

    ai_api_key: str | None = None
    ai_model: str = "gpt-4o-mini"

    attachment_dir: str = "/data/attachments"
    max_attachment_bytes: int = 5_242_880
    allowed_attachment_types: str = "image/png,image/jpeg,application/pdf,text/plain"

    default_page_size: int = 20
    max_page_size: int = 100

    @property
    def allowed_attachment_type_set(self) -> set[str]:
        return {t.strip() for t in self.allowed_attachment_types.split(",") if t.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
