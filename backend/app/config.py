from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    ANTHROPIC_API_KEY: str = ""
    UPLOAD_DIR: str = "data/uploads"
    GENERATED_DIR: str = "data/generated"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
