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


def _is_already_exists_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "duplicate column name" in message or "(1060," in message


def _run_step(step_name: str, operation) -> None:
    print(f"[alembic 0005] {step_name}", flush=True)
    try:
        operation()
    except Exception as exc:
        if _is_already_exists_error(exc):
            print(
                f"[alembic 0005] skipped existing column during {step_name}: {exc!r}",
                flush=True,
            )
            return
        print(f"[alembic 0005] FAILED {step_name}: {exc!r}", flush=True)
        raise


def upgrade() -> None:
    print("[alembic 0005] starting external capability health migration", flush=True)
    with op.batch_alter_table("t_external_capability_registry") as batch_op:
        _run_step(
            "add column health_status",
            lambda: batch_op.add_column(
                sa.Column(
                    "health_status",
                    sa.String(length=32),
                    nullable=False,
                    server_default="unknown",
                )
            ),
        )
        _run_step(
            "add column last_check_time",
            lambda: batch_op.add_column(
                sa.Column("last_check_time", sa.DateTime(), nullable=True)
            ),
        )
        _run_step(
            "add column last_success_time",
            lambda: batch_op.add_column(
                sa.Column("last_success_time", sa.DateTime(), nullable=True)
            ),
        )
        _run_step(
            "add column last_failure_time",
            lambda: batch_op.add_column(
                sa.Column("last_failure_time", sa.DateTime(), nullable=True)
            ),
        )
        _run_step(
            "add column last_error",
            lambda: batch_op.add_column(
                sa.Column("last_error", sa.String(length=1024), nullable=True)
            ),
        )
        _run_step(
            "add column consecutive_failures",
            lambda: batch_op.add_column(
                sa.Column(
                    "consecutive_failures",
                    sa.Integer(),
                    nullable=False,
                    server_default="0",
                )
            ),
        )
        _run_step(
            "add column last_latency_ms",
            lambda: batch_op.add_column(
                sa.Column("last_latency_ms", sa.BigInteger(), nullable=True)
            ),
        )
    print("[alembic 0005] completed external capability health migration", flush=True)


def downgrade() -> None:
    with op.batch_alter_table("t_external_capability_registry") as batch_op:
        batch_op.drop_column("last_latency_ms")
        batch_op.drop_column("consecutive_failures")
        batch_op.drop_column("last_error")
        batch_op.drop_column("last_failure_time")
        batch_op.drop_column("last_success_time")
        batch_op.drop_column("last_check_time")
        batch_op.drop_column("health_status")
