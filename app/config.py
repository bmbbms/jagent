from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Acquiring AI"
    env: str = "dev"
    debug: bool = True
    api_prefix: str = "/api"
    agent_runtime: str = "agentscope"
    capability_registry_backend: str = "local"
    capability_module_packages: List[str] = Field(
        default_factory=lambda: ["app.agents.capabilities"]
    )
    enabled_domains: List[str] = Field(
        default_factory=lambda: ["merchant", "operations", "data_support"]
    )
    skill_root: str = "app/skills"
    tool_catalog_backend: str = "internal"
    internal_tool_provider_backend: str = "local_db"
    internal_tool_http_base_url: str = ""
    internal_tool_http_timeout_seconds: float = 10.0
    internal_tool_http_bearer_token: str = ""
    mcp_enabled: bool = False
    mcp_config_path: str = "config/mcp.json"
    redis_url: str = "redis://127.0.0.1:6379/0"
    vector_store_enabled: bool = False
    vector_store_provider: str = "external"
    agentscope_use_model_bridge: bool = False
    agentscope_model_name: str = ""
    agentscope_api_key: str = ""
    agentscope_base_url: str = ""
    agentscope_max_iters: int = 6

    database_enabled: bool = True
    database_url: str = "sqlite+pysqlite:///./acquiring_ai.db"
    mysql_database_url: str = (
        "mysql+pymysql://root:password@127.0.0.1:3306/jagent?charset=utf8mb4"
    )
    postgres_database_url: str = (
        "postgresql+psycopg://acquiring_ai:acquiring_ai@127.0.0.1:5432/acquiring_ai"
    )
    database_echo: bool = False
    database_auto_create: bool = True
    database_run_migrations: bool = False

    nacos_enabled: bool = False
    nacos_server_address: str = "127.0.0.1:8848"
    nacos_username: str = ""
    nacos_password: str = ""
    nacos_namespace: str = "public"
    nacos_group: str = "DEFAULT_GROUP"
    nacos_service_prefix: str = "agent"
    nacos_service_host: str = "127.0.0.1"
    nacos_service_port: int = 8000
    nacos_service_path: str = "/api/chat"
    nacos_service_cluster: str = "DEFAULT"
    nacos_service_weight: float = 1.0
    nacos_ai_enabled: bool = False
    nacos_ai_publish_local_agents: bool = False
    nacos_ai_namespace: str = "public"
    nacos_ai_server_address: str = ""
    nacos_ai_username: str = ""
    nacos_ai_password: str = ""
    nacos_ai_page_size: int = 100

    model_config = SettingsConfigDict(
        env_prefix="ACQUIRING_AI_",
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
