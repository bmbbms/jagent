"""add merchant tool tables

Revision ID: 0002_add_merchant_tool_tables
Revises: 0001_create_initial_mysql_schema
Create Date: 2026-05-18 18:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_add_merchant_tool_tables"
down_revision = "0001_create_initial_mysql_schema"
branch_labels = None
depends_on = None

AUTO_ID_TYPE = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "t_merchant_profile",
        sa.Column("merchant_id", sa.String(length=64), primary_key=True),
        sa.Column("merchant_name", sa.String(length=256), nullable=False),
        sa.Column("biz_domain", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("industry_code", sa.String(length=64), nullable=True),
        sa.Column("contact_name", sa.String(length=128), nullable=True),
        sa.Column("contact_phone", sa.String(length=64), nullable=True),
        sa.Column("register_time", sa.DateTime(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=False),
        sa.Column("update_time", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_t_merchant_profile_merchant_name",
        "t_merchant_profile",
        ["merchant_name"],
        unique=False,
    )
    op.create_index(
        "ix_t_merchant_profile_biz_domain",
        "t_merchant_profile",
        ["biz_domain"],
        unique=False,
    )
    op.create_index(
        "ix_t_merchant_profile_status",
        "t_merchant_profile",
        ["status"],
        unique=False,
    )

    op.create_table(
        "t_merchant_transaction_daily",
        sa.Column("id", AUTO_ID_TYPE, primary_key=True, autoincrement=True),
        sa.Column("merchant_id", sa.String(length=64), nullable=False),
        sa.Column("stat_date", sa.String(length=10), nullable=False),
        sa.Column("txn_count", sa.Integer(), nullable=False),
        sa.Column("success_count", sa.Integer(), nullable=False),
        sa.Column("refund_count", sa.Integer(), nullable=False),
        sa.Column("gmv_amount", sa.BigInteger(), nullable=False),
        sa.Column("refund_amount", sa.BigInteger(), nullable=False),
        sa.Column("create_time", sa.DateTime(), nullable=False),
        sa.Column("update_time", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_t_merchant_transaction_daily_merchant_id",
        "t_merchant_transaction_daily",
        ["merchant_id"],
        unique=False,
    )
    op.create_index(
        "ix_t_merchant_transaction_daily_stat_date",
        "t_merchant_transaction_daily",
        ["stat_date"],
        unique=False,
    )

    op.create_table(
        "t_merchant_risk_tag",
        sa.Column("id", AUTO_ID_TYPE, primary_key=True, autoincrement=True),
        sa.Column("merchant_id", sa.String(length=64), nullable=False),
        sa.Column("risk_tag", sa.String(length=64), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("source_system", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=False),
        sa.Column("update_time", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_t_merchant_risk_tag_merchant_id",
        "t_merchant_risk_tag",
        ["merchant_id"],
        unique=False,
    )
    op.create_index(
        "ix_t_merchant_risk_tag_risk_tag",
        "t_merchant_risk_tag",
        ["risk_tag"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_t_merchant_risk_tag_risk_tag", table_name="t_merchant_risk_tag")
    op.drop_index(
        "ix_t_merchant_risk_tag_merchant_id", table_name="t_merchant_risk_tag"
    )
    op.drop_table("t_merchant_risk_tag")

    op.drop_index(
        "ix_t_merchant_transaction_daily_stat_date",
        table_name="t_merchant_transaction_daily",
    )
    op.drop_index(
        "ix_t_merchant_transaction_daily_merchant_id",
        table_name="t_merchant_transaction_daily",
    )
    op.drop_table("t_merchant_transaction_daily")

    op.drop_index(
        "ix_t_merchant_profile_status", table_name="t_merchant_profile"
    )
    op.drop_index(
        "ix_t_merchant_profile_biz_domain", table_name="t_merchant_profile"
    )
    op.drop_index(
        "ix_t_merchant_profile_merchant_name", table_name="t_merchant_profile"
    )
    op.drop_table("t_merchant_profile")
