from app.config import get_settings
from app.db.init_db import init_db
from app.db.session import create_db_engine


def main() -> None:
    settings = get_settings()
    engine = create_db_engine(settings)
    init_db(engine)
    print("database initialized", settings.database_url)


if __name__ == "__main__":
    main()
