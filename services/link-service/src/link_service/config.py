from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LINK_")

    database_url: str = "postgresql+asyncpg://shortlink:shortlink@localhost:15432/links"
    kafka_bootstrap_servers: str = "localhost:29092"
    public_base_url: str = "http://localhost:8000/r"
    relay_batch_size: int = 100
    relay_poll_interval: float = 1.0
