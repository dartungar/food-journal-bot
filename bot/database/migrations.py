import sqlite3
import logging

logger = logging.getLogger(__name__)

def add_language_column(db_path: str):
    """Add language column to users table"""
    try:
        with sqlite3.connect(db_path) as db:
            # Check if column already exists
            cursor = db.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'language' not in columns:
                db.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'en'")
                db.commit()
                logger.info("Added language column to users table")
            else:
                logger.info("Language column already exists in users table")
    except Exception as e:
        logger.error(f"Error adding language column: {e}")

def run_migrations(db_path: str):
    """Run all pending migrations"""
    logger.info("Running database migrations...")
    add_language_column(db_path)
    logger.info("Migrations completed")