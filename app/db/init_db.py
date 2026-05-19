from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType

from sqlalchemy import inspect
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.config import Settings
from app.db.base import Base
from app.db import models  # noqa: F401


def init_db(engine: Engine) -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    missing_tables = [
        table for table in Base.metadata.sorted_tables if table.name not in existing_tables
    ]
    if missing_tables:
        Base.metadata.create_all(bind=engine, tables=missing_tables)
    _upgrade_external_capability_registry_columns(engine)


def _upgrade_external_capability_registry_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    if "t_external_capability_registry" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("t_external_capability_registry")
    }
    required_sql = {
        "health_status": (
            "ALTER TABLE t_external_capability_registry "
            "ADD COLUMN health_status VARCHAR(32) NOT NULL DEFAULT 'unknown'"
        ),
        "last_check_time": (
            "ALTER TABLE t_external_capability_registry "
            "ADD COLUMN last_check_time DATETIME NULL"
        ),
        "last_success_time": (
            "ALTER TABLE t_external_capability_registry "
            "ADD COLUMN last_success_time DATETIME NULL"
        ),
        "last_failure_time": (
            "ALTER TABLE t_external_capability_registry "
            "ADD COLUMN last_failure_time DATETIME NULL"
        ),
        "last_error": (
            "ALTER TABLE t_external_capability_registry "
            "ADD COLUMN last_error VARCHAR(1024) NULL"
        ),
        "consecutive_failures": (
            "ALTER TABLE t_external_capability_registry "
            "ADD COLUMN consecutive_failures INTEGER NOT NULL DEFAULT 0"
        ),
        "last_latency_ms": (
            "ALTER TABLE t_external_capability_registry "
            "ADD COLUMN last_latency_ms BIGINT NULL"
        ),
    }

    with engine.begin() as connection:
        for column_name, ddl in required_sql.items():
            if column_name in existing_columns:
                continue
            connection.execute(text(ddl))


def _load_installed_alembic(project_root: Path) -> tuple[ModuleType, ModuleType]:
    original_sys_path = list(sys.path)

    try:
        filtered_sys_path: list[str] = []
        for entry in sys.path:
            resolved_entry = Path(entry or ".").resolve()
            if resolved_entry == project_root:
                continue
            filtered_sys_path.append(entry)

        sys.path[:] = filtered_sys_path
        sys.modules.pop("alembic", None)
        sys.modules.pop("alembic.command", None)
        sys.modules.pop("alembic.config", None)

        try:
            alembic_command = importlib.import_module("alembic.command")
            alembic_config = importlib.import_module("alembic.config")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Alembic 不可用。请确认当前 Python 环境已安装 `alembic`，"
                "或在本地调试时关闭 `ACQUIRING_AI_DATABASE_RUN_MIGRATIONS`。"
            ) from exc
        return alembic_command, alembic_config
    finally:
        sys.path[:] = original_sys_path


def run_db_migrations(settings: Settings) -> None:
    project_root = Path(__file__).resolve().parents[2]
    alembic_ini_path = project_root / "alembic.ini"
    alembic_script_path = project_root / "alembic"

    alembic_command, alembic_config = _load_installed_alembic(project_root)
    config = alembic_config.Config(str(alembic_ini_path))
    config.set_main_option("script_location", str(alembic_script_path))
    config.set_main_option("sqlalchemy.url", settings.database_url)

    alembic_command.upgrade(config, "head")
