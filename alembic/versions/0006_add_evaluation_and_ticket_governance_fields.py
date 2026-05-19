"""add evaluation and ticket governance fields

Revision ID: 0006_add_evaluation_and_ticket_governance_fields
Revises: 0005_add_external_capability_health_fields
Create Date: 2026-05-19 23:20:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0006_add_evaluation_and_ticket_governance_fields"
down_revision = "0005_add_external_capability_health_fields"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return any(item["name"] == column_name for item in inspector.get_columns(table_name))


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return any(item["name"] == index_name for item in inspector.get_indexes(table_name))


def upgrade() -> None:
    with op.batch_alter_table("t_agent_optimization_suggestion") as batch_op:
        if not _column_exists("t_agent_optimization_suggestion", "source_type"):
            batch_op.add_column(sa.Column("source_type", sa.String(length=32), nullable=True))
        if not _column_exists("t_agent_optimization_suggestion", "source_ref"):
            batch_op.add_column(sa.Column("source_ref", sa.String(length=128), nullable=True))
        if not _column_exists("t_agent_optimization_suggestion", "ticket_id"):
            batch_op.add_column(sa.Column("ticket_id", sa.String(length=64), nullable=True))
        if not _column_exists("t_agent_optimization_suggestion", "ticket_status"):
            batch_op.add_column(sa.Column("ticket_status", sa.String(length=32), nullable=True))
        if not _column_exists("t_agent_optimization_suggestion", "closed_at"):
            batch_op.add_column(sa.Column("closed_at", sa.DateTime(), nullable=True))

    if not _index_exists(
        "t_agent_optimization_suggestion",
        "ix_t_agent_optimization_suggestion_ticket_id",
    ):
        op.create_index(
            "ix_t_agent_optimization_suggestion_ticket_id",
            "t_agent_optimization_suggestion",
            ["ticket_id"],
            unique=False,
        )

    with op.batch_alter_table("t_service_ticket") as batch_op:
        if not _column_exists("t_service_ticket", "owner"):
            batch_op.add_column(sa.Column("owner", sa.String(length=64), nullable=True))
        if not _column_exists("t_service_ticket", "closed_at"):
            batch_op.add_column(sa.Column("closed_at", sa.DateTime(), nullable=True))

    if not _index_exists("t_service_ticket", "ix_t_service_ticket_owner"):
        op.create_index(
            "ix_t_service_ticket_owner",
            "t_service_ticket",
            ["owner"],
            unique=False,
        )


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
