"""add internal tool business tables

Revision ID: 0003_add_internal_tool_business_tables
Revises: 0002_add_merchant_tool_tables
Create Date: 2026-05-18 16:20:00
"""

from alembic import op
from alembic import context
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.exc import NoInspectionAvailable


revision = "0003_add_internal_tool_business_tables"
down_revision = "0002_add_merchant_tool_tables"
branch_labels = None
depends_on = None

AUTO_ID_TYPE = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _run_step(step_name: str, operation) -> None:
    print(f"[alembic 0003] {step_name}", flush=True)
    try:
        operation()
    except Exception as exc:
        print(f"[alembic 0003] FAILED {step_name}: {exc!r}", flush=True)
        raise


def _table_exists(table_name: str) -> bool:
    if context.is_offline_mode():
        return False
    bind = op.get_bind()
    try:
        inspector = inspect(bind)
    except NoInspectionAvailable:
        return False
    return table_name in inspector.get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    if context.is_offline_mode():
        return False
    bind = op.get_bind()
    try:
        inspector = inspect(bind)
    except NoInspectionAvailable:
        return False
    if table_name not in inspector.get_table_names():
        return False
    return any(item["name"] == index_name for item in inspector.get_indexes(table_name))


def upgrade() -> None:
    if not _table_exists("t_service_ticket"):
        _run_step(
            "create table t_service_ticket",
            lambda: op.create_table(
                "t_service_ticket",
                sa.Column("ticket_id", sa.String(length=64), primary_key=True),
                sa.Column("merchant_id", sa.String(length=64), nullable=True),
                sa.Column("biz_domain", sa.String(length=64), nullable=False),
                sa.Column("category", sa.String(length=64), nullable=False),
                sa.Column("priority", sa.String(length=16), nullable=False),
                sa.Column("title", sa.String(length=255), nullable=False),
                sa.Column("description", sa.Text(), nullable=True),
                sa.Column("status", sa.String(length=32), nullable=False),
                sa.Column("requested_by", sa.String(length=64), nullable=False),
                sa.Column("source", sa.String(length=32), nullable=False),
                sa.Column("payload", sa.JSON(), nullable=True),
                sa.Column("create_time", sa.DateTime(), nullable=False),
                sa.Column("update_time", sa.DateTime(), nullable=False),
            ),
        )
    if not _index_exists("t_service_ticket", "ix_t_service_ticket_merchant_id"):
        _run_step(
            "create index ix_t_service_ticket_merchant_id",
            lambda: op.create_index(
                "ix_t_service_ticket_merchant_id",
                "t_service_ticket",
                ["merchant_id"],
                unique=False,
            ),
        )
    if not _index_exists("t_service_ticket", "ix_t_service_ticket_biz_domain"):
        _run_step(
            "create index ix_t_service_ticket_biz_domain",
            lambda: op.create_index(
                "ix_t_service_ticket_biz_domain",
                "t_service_ticket",
                ["biz_domain"],
                unique=False,
            ),
        )
    if not _index_exists("t_service_ticket", "ix_t_service_ticket_category"):
        _run_step(
            "create index ix_t_service_ticket_category",
            lambda: op.create_index(
                "ix_t_service_ticket_category",
                "t_service_ticket",
                ["category"],
                unique=False,
            ),
        )
    if not _index_exists("t_service_ticket", "ix_t_service_ticket_status"):
        _run_step(
            "create index ix_t_service_ticket_status",
            lambda: op.create_index(
                "ix_t_service_ticket_status",
                "t_service_ticket",
                ["status"],
                unique=False,
            ),
        )
    if not _index_exists("t_service_ticket", "ix_t_service_ticket_requested_by"):
        _run_step(
            "create index ix_t_service_ticket_requested_by",
            lambda: op.create_index(
                "ix_t_service_ticket_requested_by",
                "t_service_ticket",
                ["requested_by"],
                unique=False,
            ),
        )

    if not _table_exists("t_direct_sales_metric_daily"):
        _run_step(
            "create table t_direct_sales_metric_daily",
            lambda: op.create_table(
                "t_direct_sales_metric_daily",
                sa.Column("id", AUTO_ID_TYPE, primary_key=True, autoincrement=True),
                sa.Column("stat_date", sa.String(length=10), nullable=False),
                sa.Column("region_code", sa.String(length=64), nullable=False),
                sa.Column("sales_amount", sa.BigInteger(), nullable=False),
                sa.Column("merchant_count", sa.Integer(), nullable=False),
                sa.Column("conversion_rate", sa.Float(), nullable=False),
                sa.Column("create_time", sa.DateTime(), nullable=False),
                sa.Column("update_time", sa.DateTime(), nullable=False),
            ),
        )
    if not _index_exists(
        "t_direct_sales_metric_daily", "ix_t_direct_sales_metric_daily_stat_date"
    ):
        _run_step(
            "create index ix_t_direct_sales_metric_daily_stat_date",
            lambda: op.create_index(
                "ix_t_direct_sales_metric_daily_stat_date",
                "t_direct_sales_metric_daily",
                ["stat_date"],
                unique=False,
            ),
        )
    if not _index_exists(
        "t_direct_sales_metric_daily", "ix_t_direct_sales_metric_daily_region_code"
    ):
        _run_step(
            "create index ix_t_direct_sales_metric_daily_region_code",
            lambda: op.create_index(
                "ix_t_direct_sales_metric_daily_region_code",
                "t_direct_sales_metric_daily",
                ["region_code"],
                unique=False,
            ),
        )

    if not _table_exists("t_report_export_job"):
        _run_step(
            "create table t_report_export_job",
            lambda: op.create_table(
                "t_report_export_job",
                sa.Column("report_id", sa.String(length=64), primary_key=True),
                sa.Column("report_type", sa.String(length=64), nullable=False),
                sa.Column("biz_domain", sa.String(length=64), nullable=False),
                sa.Column("format", sa.String(length=16), nullable=False),
                sa.Column("status", sa.String(length=32), nullable=False),
                sa.Column("requested_by", sa.String(length=64), nullable=False),
                sa.Column("output_uri", sa.String(length=512), nullable=True),
                sa.Column("request_params", sa.JSON(), nullable=True),
                sa.Column("completed_time", sa.DateTime(), nullable=True),
                sa.Column("create_time", sa.DateTime(), nullable=False),
                sa.Column("update_time", sa.DateTime(), nullable=False),
            ),
        )
    if not _index_exists("t_report_export_job", "ix_t_report_export_job_report_type"):
        _run_step(
            "create index ix_t_report_export_job_report_type",
            lambda: op.create_index(
                "ix_t_report_export_job_report_type",
                "t_report_export_job",
                ["report_type"],
                unique=False,
            ),
        )
    if not _index_exists("t_report_export_job", "ix_t_report_export_job_biz_domain"):
        _run_step(
            "create index ix_t_report_export_job_biz_domain",
            lambda: op.create_index(
                "ix_t_report_export_job_biz_domain",
                "t_report_export_job",
                ["biz_domain"],
                unique=False,
            ),
        )
    if not _index_exists("t_report_export_job", "ix_t_report_export_job_status"):
        _run_step(
            "create index ix_t_report_export_job_status",
            lambda: op.create_index(
                "ix_t_report_export_job_status",
                "t_report_export_job",
                ["status"],
                unique=False,
            ),
        )
    if not _index_exists("t_report_export_job", "ix_t_report_export_job_requested_by"):
        _run_step(
            "create index ix_t_report_export_job_requested_by",
            lambda: op.create_index(
                "ix_t_report_export_job_requested_by",
                "t_report_export_job",
                ["requested_by"],
                unique=False,
            ),
        )


def downgrade() -> None:
    op.drop_index(
        "ix_t_report_export_job_requested_by", table_name="t_report_export_job"
    )
    op.drop_index("ix_t_report_export_job_status", table_name="t_report_export_job")
    op.drop_index(
        "ix_t_report_export_job_biz_domain", table_name="t_report_export_job"
    )
    op.drop_index(
        "ix_t_report_export_job_report_type", table_name="t_report_export_job"
    )
    op.drop_table("t_report_export_job")

    op.drop_index(
        "ix_t_direct_sales_metric_daily_region_code",
        table_name="t_direct_sales_metric_daily",
    )
    op.drop_index(
        "ix_t_direct_sales_metric_daily_stat_date",
        table_name="t_direct_sales_metric_daily",
    )
    op.drop_table("t_direct_sales_metric_daily")

    op.drop_index(
        "ix_t_service_ticket_requested_by", table_name="t_service_ticket"
    )
    op.drop_index("ix_t_service_ticket_status", table_name="t_service_ticket")
    op.drop_index("ix_t_service_ticket_category", table_name="t_service_ticket")
    op.drop_index("ix_t_service_ticket_biz_domain", table_name="t_service_ticket")
    op.drop_index("ix_t_service_ticket_merchant_id", table_name="t_service_ticket")
    op.drop_table("t_service_ticket")
