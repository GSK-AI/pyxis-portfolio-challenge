import upath
from pydantic import computed_field, field_validator
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

    # Azure Settings
    azure_key_vault_name: str = "codvmtrdfpus6kvdevtest01"
    azure_storage_account_name: str = "codvmtrdfpus6sacdevtst01"
    managed_identity_enabled: bool = (
        False  # can override with env var APP_MANAGED_IDENTITY_ENABLED=1
    )

    # Middleware Settings
    disable_auth_middleware: bool = (
        False  # can override with env var APP_DISABLE_AUTH_MIDDLEWARE=1
    )
    dev_url: str = "https://*.rd-iase-devtest-us6.appserviceenvironment.net"
    uat_url: str = "https://*.rd-iase-uat-us6.appserviceenvironment.net"
    prod_url: str = "https://*.rd-iase-prod-us6.appserviceenvironment.net"
    main_url: str = "https://pyxis.gsk.com"
    docs_cdn: str = "https://cdn.jsdelivr.net"
    docs_api: str = "https://fastapi.tiangolo.com"
    auth_excluded_routes: tuple[str, ...] = ("/", "/robots933456.txt")

    # Multi-agent game settings
    max_opponents: int = 1  # Max opponents allowed in multi-agent games

    # Game assets - can be local path or Azure blob storage path
    game_assets_dir: upath.UPath = upath.UPath("az://game-generated-assets/")

    @field_validator("game_assets_dir", mode="before")
    @classmethod
    def parse_game_assets_dir(cls, v):
        """Parse game_assets_dir from string to UPath."""
        if isinstance(v, str):
            return upath.UPath(v)
        return v

    @computed_field
    @property
    def azure_key_vault_url(self) -> str:
        """Construct the Azure Key Vault URL from the vault name."""
        return f"https://{self.azure_key_vault_name}.vault.azure.net/"

    @computed_field
    @property
    def azure_storage_account_url(self) -> str:
        """Construct the Azure Storage Account URL from the account name."""
        return f"https://{self.azure_storage_account_name}.blob.core.windows.net/"


settings = Settings()
