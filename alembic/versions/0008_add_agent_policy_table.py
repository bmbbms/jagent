"""add agent policy table

Revision ID: 0008_add_agent_policy_table
Revises: 0007_add_agent_profile_tables
Create Date: 2026-05-20 21:10:00
"""

from alembic import op


revision = "0008_add_agent_policy_table"
down_revision = "0007_add_agent_profile_tables"
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
    print(f"[alembic 0008] {step_name}", flush=True)
    try:
        operation()
    except Exception as exc:
        if _is_already_exists_error(exc):
            print(
                f"[alembic 0008] skipped existing object during {step_name}: {exc!r}",
                flush=True,
            )
            return
        print(f"[alembic 0008] FAILED {step_name}: {exc!r}", flush=True)
        raise


def upgrade() -> None:
    print("[alembic 0008] starting agent policy migration", flush=True)
    _run_step(
        "create table t_agent_policy",
        lambda: op.execute(
            """
            CREATE TABLE IF NOT EXISTS t_agent_policy (
                policy_id VARCHAR(64) NOT NULL,
                agent_id VARCHAR(128) NOT NULL,
                tenant_id VARCHAR(64) NULL,
                allowed_users JSON NULL,
                allowed_roles JSON NULL,
                allowed_sources JSON NULL,
                default_decision VARCHAR(16) NOT NULL,
                rate_limit INTEGER NULL,
                audit_required BOOL NOT NULL,
                enabled BOOL NOT NULL,
                create_time DATETIME NOT NULL,
                update_time DATETIME NOT NULL,
                PRIMARY KEY (policy_id)
            )
            """
        ),
    )
    for table_name, index_name, columns in [
        ("t_agent_policy", "ix_t_agent_policy_agent_id", ["agent_id"]),
        ("t_agent_policy", "ix_t_agent_policy_tenant_id", ["tenant_id"]),
    ]:
        _run_step(
            f"create index {index_name}",
            lambda table_name=table_name, index_name=index_name, columns=columns: op.create_index(
                index_name,
                table_name,
                columns,
                unique=False,
            ),
        )
    print("[alembic 0008] completed agent policy migration", flush=True)


def downgrade() -> None:
    op.drop_index("ix_t_agent_policy_tenant_id", table_name="t_agent_policy")
    op.drop_index("ix_t_agent_policy_agent_id", table_name="t_agent_policy")
    op.drop_table("t_agent_policy")
