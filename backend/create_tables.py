from database.base import Base
from database.connection import engine
from database import models


print("Creating database tables...")

Base.metadata.create_all(
    bind=engine
)

print("Database tables created successfully.")