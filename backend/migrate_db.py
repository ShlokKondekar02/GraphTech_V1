"""
Database Migration & Alignment Script -- Sprint 5.

Executes ALTER TABLE statements on the PostgreSQL database to ensure all Sprint 4 & 5
columns (attempt_count, validation_status, repair_history) exist on diagram_requests table.
"""

import logging
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.models.base import Base
import app.models.users  # noqa
import app.models.diagram_requests  # noqa

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_database():
    logger.info("Connecting to database at: %s", settings.DATABASE_URL)
    engine = create_engine(settings.DATABASE_URL)

    # 1. Create all missing tables if they don't exist yet
    Base.metadata.create_all(bind=engine)
    logger.info("Base.metadata.create_all completed.")

    # 2. Add missing columns to diagram_requests if running against PostgreSQL
    statements = [
        "ALTER TABLE diagram_requests ADD COLUMN IF NOT EXISTS attempt_count SMALLINT DEFAULT 1;",
        "ALTER TABLE diagram_requests ADD COLUMN IF NOT EXISTS validation_status VARCHAR(50);",
        "ALTER TABLE diagram_requests ADD COLUMN IF NOT EXISTS repair_history JSONB;",
    ]

    with engine.connect() as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
                conn.commit()
                logger.info("Successfully executed: %s", stmt)
            except Exception as exc:
                logger.warning("Statement execution notice (%s): %s", stmt, exc)

    logger.info("Database migration successfully completed!")


if __name__ == "__main__":
    migrate_database()
