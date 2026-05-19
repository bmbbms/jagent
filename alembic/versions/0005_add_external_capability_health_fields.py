"""add external capability health fields

Revision ID: 0005_add_external_capability_health_fields
Revises: 0004_add_external_capability_registry_table
Create Date: 2026-05-19 20:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_add_external_capability_health_fields"
down_revision = "0004_add_external_capability_registry_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("t_external_capability_registry") as batch_op:
        batch_op.add_column(
            sa.Column("health_status", sa.String(length=32), nullable=False, server_default="unknown")
        )
        batch_op.add_column(sa.Column("last_check_time", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("last_success_time", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("last_failure_time", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("last_error", sa.String(length=1024), nullable=True))
        batch_op.add_column(
            sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(sa.Column("last_latency_ms", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("t_external_capability_registry") as batch_op:
        batch_op.drop_column("last_latency_ms")
        batch_op.drop_column("consecutive_failures")
        batch_op.drop_column("last_error")
        batch_op.drop_column("last_failure_time")
        batch_op.drop_column("last_success_time")
        batch_op.drop_column("last_check_time")
        batch_op.drop_column("health_status")
