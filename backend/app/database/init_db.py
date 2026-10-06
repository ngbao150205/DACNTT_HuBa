from app.database.base import Base
from app.database.connection import engine

# Import models để SQLAlchemy đăng ký tất cả các bảng
from app.database import models


def init_db():
    Base.metadata.create_all(
        bind=engine
    )


if __name__ == "__main__":

    init_db()

    print(
        "Database tables created successfully."
    )
