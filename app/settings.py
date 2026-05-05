import upath
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings, loaded from environment variables.

    Prefix 'APP_' to environment variables, e.g., APP_REDIS_HOST=...
    to override defaults.
    """

    model_config = SettingsConfigDict(env_prefix="APP_")

    # Redis Settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    use_local_redis: bool = True  # A flag to switch between local and Azure

    # Middleware Settings
    dev_url: str = "https://*.rd-iase-devtest-us6.appserviceenvironment.net"
    uat_url: str = "https://*.rd-iase-uat-us6.appserviceenvironment.net"
    prod_url: str = "https://*.rd-iase-prod-us6.appserviceenvironment.net"
    main_url: str = "https://pyxis.gsk.com"
    docs_cdn: str = "https://cdn.jsdelivr.net"
    docs_api: str = "https://fastapi.tiangolo.com"

    # Multi-agent game settings
    max_opponents: int = 1  # Max opponents allowed in multi-agent games

    # Game assets - local path
    game_assets_dir: upath.UPath = upath.UPath("rl-environment-assets/")

    @field_validator("game_assets_dir", mode="before")
    @classmethod
    def parse_game_assets_dir(cls, v):
        """Parse game_assets_dir from string to UPath."""
        if isinstance(v, str):
            return upath.UPath(v)
        return v


settings = Settings()
