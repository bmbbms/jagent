"""add internal tool business tables

Revision ID: 0003_add_internal_tool_business_tables
Revises: 0002_add_merchant_tool_tables
Create Date: 2026-05-18 16:20:00
"""

from alembic import op
from alembic import context
import sqlalchemy as sa


revision = "0003_add_internal_tool_business_tables"
down_revision = "0002_add_merchant_tool_tables"
branch_labels = None
depends_on = None

AUTO_ID_TYPE = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _is_already_exists_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "already exists" in message
        or "duplicate key name" in message
        or "duplicate column name" in message
        or "(1050," in message
        or "(1061," in message
    )


def _run_step(step_name: str, operation) -> None:
    print(f"[alembic 0003] {step_name}", flush=True)
    try:
        operation()
    except Exception as exc:
        if _is_already_exists_error(exc):
            print(f"[alembic 0003] skipped existing object during {step_name}: {exc!r}", flush=True)
            return
        print(f"[alembic 0003] FAILED {step_name}: {exc!r}", flush=True)
        raise


def _dialect_name() -> str:
    return op.get_context().dialect.name


def _execute_create_table(table_name: str, mysql_sql: str, sqlite_sql: str) -> None:
    sql = mysql_sql if _dialect_name() == "mysql" else sqlite_sql
    _run_step(f"create table {table_name}", lambda: op.execute(sql))


def _create_index(index_name: str, table_name: str, columns: list[str]) -> None:
    _run_step(
        f"create index {index_name}",
        lambda: op.create_index(index_name, table_name, columns, unique=False),
    )


def upgrade() -> None:
    print("[alembic 0003] starting internal tool business table migration", flush=True)
    _execute_create_table(
        "t_service_ticket",
        """
        CREATE TABLE IF NOT EXISTS t_service_ticket (
            ticket_id VARCHAR(64) NOT NULL,
            merchant_id VARCHAR(64) NULL,
            biz_domain VARCHAR(64) NOT NULL,
            category VARCHAR(64) NOT NULL,
            priority VARCHAR(16) NOT NULL,
            title VARCHAR(255) NOT NULL,
            description TEXT NULL,
            status VARCHAR(32) NOT NULL,
            requested_by VARCHAR(64) NOT NULL,
            source VARCHAR(32) NOT NULL,
            payload JSON NULL,
            create_time DATETIME NOT NULL,
            update_time DATETIME NOT NULL,
            PRIMARY KEY (ticket_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS t_service_ticket (
            ticket_id VARCHAR(64) NOT NULL,
            merchant_id VARCHAR(64) NULL,
            biz_domain VARCHAR(64) NOT NULL,
            category VARCHAR(64) NOT NULL,
            priority VARCHAR(16) NOT NULL,
            title VARCHAR(255) NOT NULL,
            description TEXT NULL,
            status VARCHAR(32) NOT NULL,
            requested_by VARCHAR(64) NOT NULL,
            source VARCHAR(32) NOT NULL,
            payload JSON NULL,
            create_time DATETIME NOT NULL,
            update_time DATETIME NOT NULL,
            PRIMARY KEY (ticket_id)
        )
        """,
    )
    _create_index("ix_t_service_ticket_merchant_id", "t_service_ticket", ["merchant_id"])
    _create_index("ix_t_service_ticket_biz_domain", "t_service_ticket", ["biz_domain"])
    _create_index("ix_t_service_ticket_category", "t_service_ticket", ["category"])
    _create_index("ix_t_service_ticket_status", "t_service_ticket", ["status"])
    _create_index("ix_t_service_ticket_requested_by", "t_service_ticket", ["requested_by"])

    _execute_create_table(
        "t_direct_sales_metric_daily",
        """
        CREATE TABLE IF NOT EXISTS t_direct_sales_metric_daily (
            id BIGINT NOT NULL AUTO_INCREMENT,
            stat_date VARCHAR(10) NOT NULL,
            region_code VARCHAR(64) NOT NULL,
            sales_amount BIGINT NOT NULL,
            merchant_count INTEGER NOT NULL,
            conversion_rate FLOAT NOT NULL,
            create_time DATETIME NOT NULL,
            update_time DATETIME NOT NULL,
            PRIMARY KEY (id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS t_direct_sales_metric_daily (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            stat_date VARCHAR(10) NOT NULL,
            region_code VARCHAR(64) NOT NULL,
            sales_amount BIGINT NOT NULL,
            merchant_count INTEGER NOT NULL,
            conversion_rate FLOAT NOT NULL,
            create_time DATETIME NOT NULL,
            update_time DATETIME NOT NULL
        )
        """,
    )
    _create_index(
        "ix_t_direct_sales_metric_daily_stat_date",
        "t_direct_sales_metric_daily",
        ["stat_date"],
    )
    _create_index(
        "ix_t_direct_sales_metric_daily_region_code",
        "t_direct_sales_metric_daily",
        ["region_code"],
    )

    _execute_create_table(
        "t_report_export_job",
        """
        CREATE TABLE IF NOT EXISTS t_report_export_job (
            report_id VARCHAR(64) NOT NULL,
            report_type VARCHAR(64) NOT NULL,
            biz_domain VARCHAR(64) NOT NULL,
            format VARCHAR(16) NOT NULL,
            status VARCHAR(32) NOT NULL,
            requested_by VARCHAR(64) NOT NULL,
            output_uri VARCHAR(512) NULL,
            request_params JSON NULL,
            completed_time DATETIME NULL,
            create_time DATETIME NOT NULL,
            update_time DATETIME NOT NULL,
            PRIMARY KEY (report_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS t_report_export_job (
            report_id VARCHAR(64) NOT NULL,
            report_type VARCHAR(64) NOT NULL,
            biz_domain VARCHAR(64) NOT NULL,
            format VARCHAR(16) NOT NULL,
            status VARCHAR(32) NOT NULL,
            requested_by VARCHAR(64) NOT NULL,
            output_uri VARCHAR(512) NULL,
            request_params JSON NULL,
            completed_time DATETIME NULL,
            create_time DATETIME NOT NULL,
            update_time DATETIME NOT NULL,
            PRIMARY KEY (report_id)
        )
        """,
    )
    _create_index("ix_t_report_export_job_report_type", "t_report_export_job", ["report_type"])
    _create_index("ix_t_report_export_job_biz_domain", "t_report_export_job", ["biz_domain"])
    _create_index("ix_t_report_export_job_status", "t_report_export_job", ["status"])
    _create_index("ix_t_report_export_job_requested_by", "t_report_export_job", ["requested_by"])
    print("[alembic 0003] completed internal tool business table migration", flush=True)


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
