"""add external capability registry table

Revision ID: 0004_add_external_capability_registry_table
Revises: 0003_add_internal_tool_business_tables
Create Date: 2026-05-19 12:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_add_external_capability_registry_table"
down_revision = "0003_add_internal_tool_business_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "t_external_capability_registry",
        sa.Column("capability_id", sa.String(length=64), primary_key=True),
        sa.Column("capability_name", sa.String(length=128), nullable=False),
        sa.Column("biz_domain", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=1024), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("triggers", sa.JSON(), nullable=True),
        sa.Column("skills", sa.JSON(), nullable=True),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("requires_approval", sa.Boolean(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("transport", sa.String(length=32), nullable=False),
        sa.Column("endpoint", sa.String(length=512), nullable=True),
        sa.Column("service_name", sa.String(length=128), nullable=True),
        sa.Column("service_host", sa.String(length=128), nullable=True),
        sa.Column("service_port", sa.Integer(), nullable=True),
        sa.Column("service_path", sa.String(length=255), nullable=False),
        sa.Column("extras", sa.JSON(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("create_time", sa.DateTime(), nullable=False),
        sa.Column("update_time", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_t_external_capability_registry_biz_domain",
        "t_external_capability_registry",
        ["biz_domain"],
        unique=False,
    )
    op.create_index(
        "ix_t_external_capability_registry_create_time",
        "t_external_capability_registry",
        ["create_time"],
        unique=False,
    )


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
