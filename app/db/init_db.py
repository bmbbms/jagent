from __future__ import annotations

from sqlalchemy.engine import Engine

from app.db.base import Base
from app.db import models  # noqa: F401


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)
