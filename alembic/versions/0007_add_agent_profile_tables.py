"""add agent profile tables

Revision ID: 0007_add_agent_profile_tables
Revises: 0006_add_evaluation_and_ticket_governance_fields
Create Date: 2026-05-20 20:00:00
"""

from alembic import op


revision = "0007_add_agent_profile_tables"
down_revision = "0006_add_evaluation_and_ticket_governance_fields"
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
    print(f"[alembic 0007] {step_name}", flush=True)
    try:
        operation()
    except Exception as exc:
        if _is_already_exists_error(exc):
            print(
                f"[alembic 0007] skipped existing object during {step_name}: {exc!r}",
                flush=True,
            )
            return
        print(f"[alembic 0007] FAILED {step_name}: {exc!r}", flush=True)
        raise


def upgrade() -> None:
    print("[alembic 0007] starting agent profile migration", flush=True)
    _run_step(
        "create table t_agent_profile",
        lambda: op.execute(
            """
            CREATE TABLE IF NOT EXISTS t_agent_profile (
                agent_id VARCHAR(128) NOT NULL,
                source_agent_name VARCHAR(128) NOT NULL,
                agent_name VARCHAR(128) NOT NULL,
                description VARCHAR(1024) NULL,
                endpoint VARCHAR(512) NULL,
                protocol VARCHAR(32) NOT NULL,
                transport VARCHAR(32) NOT NULL,
                version VARCHAR(32) NOT NULL,
                namespace VARCHAR(64) NOT NULL,
                source VARCHAR(32) NOT NULL,
                biz_domain VARCHAR(64) NOT NULL,
                tags JSON NULL,
                raw_card JSON NULL,
                normalized_card JSON NULL,
                health_status VARCHAR(32) NOT NULL,
                governance_status VARCHAR(32) NOT NULL,
                risk_level VARCHAR(16) NOT NULL,
                enabled BOOL NOT NULL,
                last_sync_time DATETIME NULL,
                create_time DATETIME NOT NULL,
                update_time DATETIME NOT NULL,
                PRIMARY KEY (agent_id)
            )
            """
        ),
    )
    _run_step(
        "create table t_agent_declared_skill",
        lambda: op.execute(
            """
            CREATE TABLE IF NOT EXISTS t_agent_declared_skill (
                id BIGINT NOT NULL AUTO_INCREMENT,
                agent_id VARCHAR(128) NOT NULL,
                skill_id VARCHAR(128) NOT NULL,
                skill_name VARCHAR(128) NOT NULL,
                description VARCHAR(1024) NULL,
                tags JSON NULL,
                examples JSON NULL,
                input_modes JSON NULL,
                output_modes JSON NULL,
                raw_payload JSON NULL,
                create_time DATETIME NOT NULL,
                update_time DATETIME NOT NULL,
                PRIMARY KEY (id)
            )
            """
        ),
    )
    _run_step(
        "create table t_agent_declared_mcp",
        lambda: op.execute(
            """
            CREATE TABLE IF NOT EXISTS t_agent_declared_mcp (
                id BIGINT NOT NULL AUTO_INCREMENT,
                agent_id VARCHAR(128) NOT NULL,
                mcp_id VARCHAR(128) NOT NULL,
                mcp_name VARCHAR(128) NOT NULL,
                description VARCHAR(1024) NULL,
                transport VARCHAR(32) NULL,
                endpoint VARCHAR(512) NULL,
                tags JSON NULL,
                raw_payload JSON NULL,
                create_time DATETIME NOT NULL,
                update_time DATETIME NOT NULL,
                PRIMARY KEY (id)
            )
            """
        ),
    )
    _run_step(
        "create table t_agent_declared_workflow",
        lambda: op.execute(
            """
            CREATE TABLE IF NOT EXISTS t_agent_declared_workflow (
                id BIGINT NOT NULL AUTO_INCREMENT,
                agent_id VARCHAR(128) NOT NULL,
                workflow_id VARCHAR(128) NOT NULL,
                workflow_name VARCHAR(128) NOT NULL,
                description VARCHAR(1024) NULL,
                steps JSON NULL,
                tags JSON NULL,
                raw_payload JSON NULL,
                create_time DATETIME NOT NULL,
                update_time DATETIME NOT NULL,
                PRIMARY KEY (id)
            )
            """
        ),
    )
    _run_step(
        "create table t_agent_profile_sync_log",
        lambda: op.execute(
            """
            CREATE TABLE IF NOT EXISTS t_agent_profile_sync_log (
                sync_id VARCHAR(64) NOT NULL,
                namespace VARCHAR(64) NOT NULL,
                source VARCHAR(32) NOT NULL,
                status VARCHAR(32) NOT NULL,
                pulled_count INTEGER NOT NULL,
                upserted_count INTEGER NOT NULL,
                failed_count INTEGER NOT NULL,
                error_message VARCHAR(2048) NULL,
                start_time DATETIME NOT NULL,
                end_time DATETIME NULL,
                PRIMARY KEY (sync_id)
            )
            """
        ),
    )

    for table_name, index_name, columns in [
        ("t_agent_profile", "ix_t_agent_profile_source_agent_name", ["source_agent_name"]),
        ("t_agent_profile", "ix_t_agent_profile_namespace", ["namespace"]),
        ("t_agent_profile", "ix_t_agent_profile_biz_domain", ["biz_domain"]),
        ("t_agent_profile", "ix_t_agent_profile_create_time", ["create_time"]),
        ("t_agent_declared_skill", "ix_t_agent_declared_skill_agent_id", ["agent_id"]),
        ("t_agent_declared_skill", "ix_t_agent_declared_skill_skill_id", ["skill_id"]),
        ("t_agent_declared_mcp", "ix_t_agent_declared_mcp_agent_id", ["agent_id"]),
        ("t_agent_declared_mcp", "ix_t_agent_declared_mcp_mcp_id", ["mcp_id"]),
        (
            "t_agent_declared_workflow",
            "ix_t_agent_declared_workflow_agent_id",
            ["agent_id"],
        ),
        (
            "t_agent_declared_workflow",
            "ix_t_agent_declared_workflow_workflow_id",
            ["workflow_id"],
        ),
        ("t_agent_profile_sync_log", "ix_t_agent_profile_sync_log_namespace", ["namespace"]),
        ("t_agent_profile_sync_log", "ix_t_agent_profile_sync_log_status", ["status"]),
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
    print("[alembic 0007] completed agent profile migration", flush=True)


def downgrade() -> None:
    for table_name, index_name in [
        ("t_agent_profile_sync_log", "ix_t_agent_profile_sync_log_status"),
        ("t_agent_profile_sync_log", "ix_t_agent_profile_sync_log_namespace"),
        ("t_agent_declared_workflow", "ix_t_agent_declared_workflow_workflow_id"),
        ("t_agent_declared_workflow", "ix_t_agent_declared_workflow_agent_id"),
        ("t_agent_declared_mcp", "ix_t_agent_declared_mcp_mcp_id"),
        ("t_agent_declared_mcp", "ix_t_agent_declared_mcp_agent_id"),
        ("t_agent_declared_skill", "ix_t_agent_declared_skill_skill_id"),
        ("t_agent_declared_skill", "ix_t_agent_declared_skill_agent_id"),
        ("t_agent_profile", "ix_t_agent_profile_create_time"),
        ("t_agent_profile", "ix_t_agent_profile_biz_domain"),
        ("t_agent_profile", "ix_t_agent_profile_namespace"),
        ("t_agent_profile", "ix_t_agent_profile_source_agent_name"),
    ]:
        op.drop_index(index_name, table_name=table_name)
    op.drop_table("t_agent_profile_sync_log")
    op.drop_table("t_agent_declared_workflow")
    op.drop_table("t_agent_declared_mcp")
    op.drop_table("t_agent_declared_skill")
    op.drop_table("t_agent_profile")
