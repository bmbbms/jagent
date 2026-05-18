from app.config import get_settings
from app.db.init_db import init_db, run_db_migrations
from app.db.session import create_db_engine


def main() -> None:
    settings = get_settings()
    if settings.database_run_migrations:
        run_db_migrations(settings)
        print("database migrated", settings.database_url)
        return

    engine = create_db_engine(settings)
    init_db(engine)
    print("database initialized via metadata.create_all", settings.database_url)


if __name__ == "__main__":
    main()
