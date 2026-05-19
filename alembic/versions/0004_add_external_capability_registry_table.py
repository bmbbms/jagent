"""add external capability registry table

Revision ID: 0004_add_external_capability_registry_table
Revises: 0003_add_internal_tool_business_tables
Create Date: 2026-05-19 12:30:00
"""

from alembic import op


revision = "0004_add_external_capability_registry_table"
down_revision = "0003_add_internal_tool_business_tables"
branch_labels = None
depends_on = None


def _is_already_exists_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "already exists" in message
        or "duplicate key name" in message
        or "(1050," in message
        or "(1061," in message
    )


def _run_step(step_name: str, operation) -> None:
    print(f"[alembic 0004] {step_name}", flush=True)
    try:
        operation()
    except Exception as exc:
        if _is_already_exists_error(exc):
            print(
                f"[alembic 0004] skipped existing object during {step_name}: {exc!r}",
                flush=True,
            )
            return
        print(f"[alembic 0004] FAILED {step_name}: {exc!r}", flush=True)
        raise


def upgrade() -> None:
    print("[alembic 0004] starting external capability registry migration", flush=True)
    _run_step(
        "create table t_external_capability_registry",
        lambda: op.execute(
            """
            CREATE TABLE IF NOT EXISTS t_external_capability_registry (
                capability_id VARCHAR(64) NOT NULL,
                capability_name VARCHAR(128) NOT NULL,
                biz_domain VARCHAR(64) NOT NULL,
                description VARCHAR(1024) NOT NULL,
                priority INTEGER NOT NULL,
                triggers JSON NULL,
                skills JSON NULL,
                version VARCHAR(32) NOT NULL,
                risk_level VARCHAR(16) NOT NULL,
                requires_approval BOOL NOT NULL,
                tags JSON NULL,
                transport VARCHAR(32) NOT NULL,
                endpoint VARCHAR(512) NULL,
                service_name VARCHAR(128) NULL,
                service_host VARCHAR(128) NULL,
                service_port INTEGER NULL,
                service_path VARCHAR(255) NOT NULL,
                extras JSON NULL,
                enabled BOOL NOT NULL,
                create_time DATETIME NOT NULL,
                update_time DATETIME NOT NULL,
                PRIMARY KEY (capability_id)
            )
            """
        ),
    )
    _run_step(
        "create index ix_t_external_capability_registry_biz_domain",
        lambda: op.create_index(
            "ix_t_external_capability_registry_biz_domain",
            "t_external_capability_registry",
            ["biz_domain"],
            unique=False,
        ),
    )
    _run_step(
        "create index ix_t_external_capability_registry_create_time",
        lambda: op.create_index(
            "ix_t_external_capability_registry_create_time",
            "t_external_capability_registry",
            ["create_time"],
            unique=False,
        ),
    )
    print("[alembic 0004] completed external capability registry migration", flush=True)


def downgrade() -> None:
    op.drop_index(
        "ix_t_external_capability_registry_create_time",
        table_name="t_external_capability_registry",
    )
    op.drop_index(
        "ix_t_external_capability_registry_biz_domain",
        table_name="t_external_capability_registry",
    )
    op.drop_table("t_external_capability_registry")
