from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from alembic.ddl.impl import DefaultImpl
from sqlalchemy import Column, MetaData, PrimaryKeyConstraint, String, Table, engine_from_config, inspect, pool

from app.config import get_settings
from app.db.base import Base
from app.db import models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def _patch_version_table_impl() -> None:
    def version_table_impl(self, *, version_table, version_table_schema, version_table_pk, **kw):
        table = Table(
            version_table,
            MetaData(),
            Column("version_num", String(64), nullable=False),
            schema=version_table_schema,
        )
        if version_table_pk:
            table.append_constraint(
                PrimaryKeyConstraint("version_num", name=f"{version_table}_pkc")
            )
        return table

    DefaultImpl.version_table_impl = version_table_impl


def _ensure_version_table_column_size(connection) -> None:
    if connection.dialect.name != "mysql":
        return

    inspector = inspect(connection)
    if "alembic_version" not in inspector.get_table_names():
        return

    version_columns = [
        column for column in inspector.get_columns("alembic_version")
        if column["name"] == "version_num"
    ]
    if not version_columns:
        return

    version_type = str(version_columns[0]["type"]).lower()
    if "varchar(64)" in version_type:
        return

    connection.exec_driver_sql(
        "ALTER TABLE alembic_version MODIFY version_num VARCHAR(64) NOT NULL"
    )


def run_migrations_offline() -> None:
    _patch_version_table_impl()
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    _patch_version_table_impl()
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _ensure_version_table_column_size(connection)
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
