from database.base import Base
from database.connection import engine

from database import models
from sqlalchemy import text
from database.auth_migration import migrate_auth_ownership


def init_db():
    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(text("SELECT pg_advisory_xact_lock(639472081)"))
        Base.metadata.create_all(bind=connection)
        if engine.dialect.name == "postgresql":
            migrate_auth_ownership(connection)


if __name__ == "__main__":

    init_db()

    print(
        "Database tables created successfully."
    )
