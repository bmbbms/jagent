"""add evaluation and ticket governance fields

Revision ID: 0006_add_evaluation_and_ticket_governance_fields
Revises: 0005_add_external_capability_health_fields
Create Date: 2026-05-19 23:20:00
"""

from alembic import op
from alembic import context
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.exc import NoInspectionAvailable, SQLAlchemyError


revision = "0006_add_evaluation_and_ticket_governance_fields"
down_revision = "0005_add_external_capability_health_fields"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    if context.is_offline_mode():
        return False
    bind = op.get_bind()
    try:
        inspector = inspect(bind)
    except (NoInspectionAvailable, SQLAlchemyError) as exc:
        print(
            f"[alembic 0006] column existence check failed for {table_name}.{column_name}: {exc!r}; continuing",
            flush=True,
        )
        return False
    if table_name not in inspector.get_table_names():
        return False
    return any(item["name"] == column_name for item in inspector.get_columns(table_name))


def _index_exists(table_name: str, index_name: str) -> bool:
    if context.is_offline_mode():
        return False
    bind = op.get_bind()
    try:
        inspector = inspect(bind)
    except (NoInspectionAvailable, SQLAlchemyError) as exc:
        print(
            f"[alembic 0006] index existence check failed for {index_name}: {exc!r}; continuing",
            flush=True,
        )
        return False
    if table_name not in inspector.get_table_names():
        return False
    return any(item["name"] == index_name for item in inspector.get_indexes(table_name))


def _is_already_exists_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "duplicate column name" in message
        or "duplicate key name" in message
        or "(1060," in message
        or "(1061," in message
    )


def _run_step(step_name: str, operation) -> None:
    print(f"[alembic 0006] {step_name}", flush=True)
    try:
        operation()
    except Exception as exc:
        if _is_already_exists_error(exc):
            print(
                f"[alembic 0006] skipped existing object during {step_name}: {exc!r}",
                flush=True,
            )
            return
        print(f"[alembic 0006] FAILED {step_name}: {exc!r}", flush=True)
        raise


def upgrade() -> None:
    print("[alembic 0006] starting evaluation and ticket governance migration", flush=True)
    with op.batch_alter_table("t_agent_optimization_suggestion") as batch_op:
        if not _column_exists("t_agent_optimization_suggestion", "source_type"):
            _run_step(
                "add column t_agent_optimization_suggestion.source_type",
                lambda: batch_op.add_column(
                    sa.Column("source_type", sa.String(length=32), nullable=True)
                ),
            )
        if not _column_exists("t_agent_optimization_suggestion", "source_ref"):
            _run_step(
                "add column t_agent_optimization_suggestion.source_ref",
                lambda: batch_op.add_column(
                    sa.Column("source_ref", sa.String(length=128), nullable=True)
                ),
            )
        if not _column_exists("t_agent_optimization_suggestion", "ticket_id"):
            _run_step(
                "add column t_agent_optimization_suggestion.ticket_id",
                lambda: batch_op.add_column(
                    sa.Column("ticket_id", sa.String(length=64), nullable=True)
                ),
            )
        if not _column_exists("t_agent_optimization_suggestion", "ticket_status"):
            _run_step(
                "add column t_agent_optimization_suggestion.ticket_status",
                lambda: batch_op.add_column(
                    sa.Column("ticket_status", sa.String(length=32), nullable=True)
                ),
            )
        if not _column_exists("t_agent_optimization_suggestion", "closed_at"):
            _run_step(
                "add column t_agent_optimization_suggestion.closed_at",
                lambda: batch_op.add_column(
                    sa.Column("closed_at", sa.DateTime(), nullable=True)
                ),
            )

    if not _index_exists(
        "t_agent_optimization_suggestion",
        "ix_t_agent_optimization_suggestion_ticket_id",
    ):
        _run_step(
            "create index ix_t_agent_optimization_suggestion_ticket_id",
            lambda: op.create_index(
                "ix_t_agent_optimization_suggestion_ticket_id",
                "t_agent_optimization_suggestion",
                ["ticket_id"],
                unique=False,
            ),
        )

    with op.batch_alter_table("t_service_ticket") as batch_op:
        if not _column_exists("t_service_ticket", "owner"):
            _run_step(
                "add column t_service_ticket.owner",
                lambda: batch_op.add_column(
                    sa.Column("owner", sa.String(length=64), nullable=True)
                ),
            )
        if not _column_exists("t_service_ticket", "closed_at"):
            _run_step(
                "add column t_service_ticket.closed_at",
                lambda: batch_op.add_column(
                    sa.Column("closed_at", sa.DateTime(), nullable=True)
                ),
            )

    if not _index_exists("t_service_ticket", "ix_t_service_ticket_owner"):
        _run_step(
            "create index ix_t_service_ticket_owner",
            lambda: op.create_index(
                "ix_t_service_ticket_owner",
                "t_service_ticket",
                ["owner"],
                unique=False,
            ),
        )
    print("[alembic 0006] completed evaluation and ticket governance migration", flush=True)


def downgrade() -> None:
    if _index_exists("t_service_ticket", "ix_t_service_ticket_owner"):
        op.drop_index("ix_t_service_ticket_owner", table_name="t_service_ticket")

    with op.batch_alter_table("t_service_ticket") as batch_op:
        if _column_exists("t_service_ticket", "closed_at"):
            batch_op.drop_column("closed_at")
        if _column_exists("t_service_ticket", "owner"):
            batch_op.drop_column("owner")

    if _index_exists(
        "t_agent_optimization_suggestion",
        "ix_t_agent_optimization_suggestion_ticket_id",
    ):
        op.drop_index(
            "ix_t_agent_optimization_suggestion_ticket_id",
            table_name="t_agent_optimization_suggestion",
        )

    with op.batch_alter_table("t_agent_optimization_suggestion") as batch_op:
        if _column_exists("t_agent_optimization_suggestion", "closed_at"):
            batch_op.drop_column("closed_at")
        if _column_exists("t_agent_optimization_suggestion", "ticket_status"):
            batch_op.drop_column("ticket_status")
        if _column_exists("t_agent_optimization_suggestion", "ticket_id"):
            batch_op.drop_column("ticket_id")
        if _column_exists("t_agent_optimization_suggestion", "source_ref"):
            batch_op.drop_column("source_ref")
        if _column_exists("t_agent_optimization_suggestion", "source_type"):
            batch_op.drop_column("source_type")
