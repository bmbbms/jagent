from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Acquiring AI"
    env: str = "dev"
    debug: bool = True
    api_prefix: str = "/api"
    capability_registry_backend: str = "local"
    capability_module_packages: List[str] = Field(
        default_factory=lambda: ["app.agents.capabilities"]
    )
    enabled_domains: List[str] = Field(
        default_factory=lambda: ["merchant", "operations", "data_support"]
    )
    skill_root: str = "app/skills"

    database_enabled: bool = True
    database_url: str = "sqlite+pysqlite:///./acquiring_ai.db"
    database_echo: bool = False
    database_auto_create: bool = True

    nacos_enabled: bool = False
    nacos_server_address: str = "127.0.0.1:8848"
    nacos_namespace: str = "public"
    nacos_group: str = "DEFAULT_GROUP"
    nacos_service_prefix: str = "agent"
    nacos_service_host: str = "127.0.0.1"
    nacos_service_port: int = 8000
    nacos_service_path: str = "/api/chat"
    nacos_service_cluster: str = "DEFAULT"
    nacos_service_weight: float = 1.0

    model_config = SettingsConfigDict(
        env_prefix="ACQUIRING_AI_",
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
