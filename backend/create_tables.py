from app.database.base import Base
from app.database.connection import engine
from app.database import models


print("Creating database tables...")

Base.metadata.create_all(
    bind=engine
)

print("Database tables created successfully.")