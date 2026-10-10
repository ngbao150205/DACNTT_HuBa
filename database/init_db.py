from database.base import Base
from database.connection import engine

from database import models


def init_db():
    Base.metadata.create_all(
        bind=engine
    )


if __name__ == "__main__":

    init_db()

    print(
        "Database tables created successfully."
    )
