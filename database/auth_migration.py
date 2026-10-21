"""Idempotent PostgreSQL migration: retain legacy rows, add tenant isolation."""
from sqlalchemy import inspect, text


def migrate_auth_ownership(connection):
    inspector = inspect(connection)
    if "owner_id" not in {col["name"] for col in inspector.get_columns("products")}:
        connection.execute(text('ALTER TABLE products ADD COLUMN owner_id INTEGER REFERENCES users(id)'))
    connection.execute(text('CREATE INDEX IF NOT EXISTS ix_products_owner_id ON products(owner_id)'))
    quote = connection.dialect.identifier_preparer.quote
    changes = [
        ("products", {"platform", "platform_product_id"}, "uq_product_owner_platform_product", "owner_id, platform, platform_product_id"),
        ("reviews", {"platform", "platform_review_id"}, "uq_review_product_platform_review", "product_id, platform, platform_review_id"),
    ]
    for table, old_columns, new_name, new_columns in changes:
        constraints = inspect(connection).get_unique_constraints(table)
        for constraint in constraints:
            if set(constraint["column_names"]) == old_columns and constraint.get("name"):
                connection.execute(text(f'ALTER TABLE {quote(table)} DROP CONSTRAINT {quote(constraint["name"])}'))
        if new_name not in {constraint["name"] for constraint in constraints}:
            connection.execute(text(f'ALTER TABLE {quote(table)} ADD CONSTRAINT {quote(new_name)} UNIQUE ({new_columns})'))
