from __future__ import annotations

from redis import Redis
from sqlalchemy import inspect, text

from app.config import get_settings
from app.db.session import create_db_engine


REQUIRED_TABLES = [
    "t_agent_registry",
    "t_contact_list",
    "t_contact_msg_list",
    "t_agent_task",
    "t_agent_task_event",
    "t_agent_task_artifact",
    "t_approval_task",
    "t_audit_log",
    "t_agent_evaluation",
]


def verify_database() -> None:
    settings = get_settings()
    engine = create_db_engine(settings)

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        inspector = inspect(connection)
        existing_tables = set(inspector.get_table_names())

    missing_tables = [table for table in REQUIRED_TABLES if table not in existing_tables]
    if missing_tables:
        raise RuntimeError(f"missing tables: {', '.join(missing_tables)}")

    print("database ok:", settings.database_url)
    print("tables ok:", ", ".join(REQUIRED_TABLES))


def verify_redis() -> None:
    settings = get_settings()
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        client.ping()
    finally:
        client.close()
    print("redis ok:", settings.redis_url)


def main() -> None:
    verify_database()
    verify_redis()
    print("stack verification passed")


if __name__ == "__main__":
    main()
