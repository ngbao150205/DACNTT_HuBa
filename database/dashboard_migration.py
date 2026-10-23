"""Keep old snapshots intact while allowing new runs to store rating counts."""
from sqlalchemy import inspect, text


def migrate_dashboard_snapshots(connection):
    columns = {column["name"] for column in inspect(connection).get_columns("analysis_history")}
    if "rating_summary" not in columns:
        connection.execute(text("ALTER TABLE analysis_history ADD COLUMN rating_summary TEXT"))
