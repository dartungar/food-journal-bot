import sqlite3
import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any
from database.models import User, FoodEntry, FoodItem
import logging


logger = logging.getLogger(__name__)


class Database:
    def initialize(self):
        """Initialize database and create tables if they don't exist"""
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as db:
            self._create_tables(db)
            db.commit()
        logger.info(f"Database initialized at {self.db_path}")

    def _create_tables(self, db: sqlite3.Connection):
        """Create all necessary tables"""
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS food_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                total_calories REAL NOT NULL DEFAULT 0,
                total_protein REAL NOT NULL DEFAULT 0,
                total_carbs REAL NOT NULL DEFAULT 0,
                total_fat REAL NOT NULL DEFAULT 0,
                total_fiber REAL DEFAULT 0,
                total_sugar REAL DEFAULT 0,
                meal_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS food_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                food_entry_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                quantity TEXT,
                calories REAL NOT NULL DEFAULT 0,
                protein REAL NOT NULL DEFAULT 0,
                carbs REAL NOT NULL DEFAULT 0,
                fat REAL NOT NULL DEFAULT 0,
                fiber REAL DEFAULT 0,
                sugar REAL DEFAULT 0,
                confidence REAL DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (food_entry_id) REFERENCES food_entries (id)
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users (telegram_user_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_food_entries_user_id ON food_entries (user_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_food_entries_timestamp ON food_entries (timestamp)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_food_items_entry_id ON food_items (food_entry_id)")
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._connection = None

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def create_or_update_user(self, telegram_user_id: int, username: str = None, first_name: str = None) -> int:
        with self.get_connection() as db:
            cursor = db.execute(
                "SELECT id FROM users WHERE telegram_user_id = ?",
                (telegram_user_id,)
            )
            row = cursor.fetchone()
            if row:
                user_id = row[0]
                db.execute(
                    "UPDATE users SET username = ?, first_name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (username, first_name, user_id)
                )
                db.commit()
                return user_id
            else:
                cursor = db.execute(
                    "INSERT INTO users (telegram_user_id, username, first_name) VALUES (?, ?, ?)",
                    (telegram_user_id, username, first_name)
                )
                db.commit()
                return cursor.lastrowid

    def create_food_entry(self, food_entry: FoodEntry, food_items: List[FoodItem]) -> bool:
        try:
            with self.get_connection() as db:
                cursor = db.execute(
                    """
                    INSERT INTO food_entries 
                    (user_id, timestamp, total_calories, total_protein, total_carbs, total_fat, total_fiber, total_sugar, meal_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        food_entry.user_id,
                        food_entry.timestamp,
                        food_entry.total_calories,
                        food_entry.total_protein,
                        food_entry.total_carbs,
                        food_entry.total_fat,
                        food_entry.total_fiber,
                        food_entry.total_sugar,
                        food_entry.meal_count
                    )
                )
                entry_id = cursor.lastrowid
                for item in food_items:
                    db.execute(
                        """
                        INSERT INTO food_items 
                        (food_entry_id, name, quantity, calories, protein, carbs, fat, fiber, sugar, confidence)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            entry_id,
                            item.name,
                            item.quantity,
                            item.calories,
                            item.protein,
                            item.carbs,
                            item.fat,
                            item.fiber,
                            item.sugar,
                            item.confidence
                        )
                    )
                db.commit()
            return True
        except Exception as e:
            logger.error(f"Error creating food entry: {e}")
            return False

    def get_daily_summary(self, user_id: int, date_str: str) -> Optional[Dict]:
        try:
            with self.get_connection() as db:
                cursor = db.execute(
                    """
                    SELECT 
                        COUNT(*) as meal_count,
                        SUM(total_calories) as total_calories,
                        SUM(total_protein) as total_protein,
                        SUM(total_carbs) as total_carbs,
                        SUM(total_fat) as total_fat,
                        SUM(total_fiber) as total_fiber,
                        SUM(total_sugar) as total_sugar
                    FROM food_entries 
                    WHERE user_id = ? AND DATE(timestamp) = ?
                    """,
                    (user_id, date_str)
                )
                row = cursor.fetchone()
                if row and row[1] is not None:
                    return {
                        'date': date_str,
                        'meal_count': row[0] or 0,
                        'total_calories': row[1] or 0,
                        'total_protein': row[2] or 0,
                        'total_carbs': row[3] or 0,
                        'total_fat': row[4] or 0,
                        'total_fiber': row[5] or 0,
                        'total_sugar': row[6] or 0
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting daily summary: {e}")
            return None

    def get_food_entries_with_items(self, user_id: int, start_date: str, end_date: str) -> List[Dict]:
        try:
            with self.get_connection() as db:
                cursor = db.execute(
                    """
                    SELECT id, timestamp, total_calories, total_protein, total_carbs, total_fat,
                           total_fiber, total_sugar, meal_count
                    FROM food_entries 
                    WHERE user_id = ? AND DATE(timestamp) BETWEEN ? AND ?
                    ORDER BY timestamp
                    """,
                    (user_id, start_date, end_date)
                )
                entries = []
                rows = cursor.fetchall()
                for row in rows:
                    entry = {
                        'id': row[0],
                        'timestamp': row[1],
                        'total_calories': row[2],
                        'total_protein': row[3],
                        'total_carbs': row[4],
                        'total_fat': row[5],
                        'total_fiber': row[6],
                        'total_sugar': row[7],
                        'meal_count': row[8],
                        'food_items': []
                    }
                    items_cursor = db.execute(
                        """
                        SELECT name, quantity, calories, protein, carbs, fat, fiber, sugar, confidence
                        FROM food_items WHERE food_entry_id = ? ORDER BY id
                        """,
                        (row[0],)
                    )
                    for item_row in items_cursor.fetchall():
                        entry['food_items'].append({
                            'name': item_row[0],
                            'quantity': item_row[1],
                            'calories': item_row[2],
                            'protein': item_row[3],
                            'carbs': item_row[4],
                            'fat': item_row[5],
                            'fiber': item_row[6],
                            'sugar': item_row[7],
                            'confidence': item_row[8]
                        })
                    entries.append(entry)
                return entries
        except Exception as e:
            logger.error(f"Error getting food entries with items: {e}")
            return []

    def get_all_user_ids(self) -> List[int]:
        try:
            with self.get_connection() as db:
                cursor = db.execute("SELECT id FROM users")
                rows = cursor.fetchall()
                return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"Error getting all user IDs: {e}")
            return []

    def get_user_by_telegram_id(self, telegram_user_id: int) -> Optional[Dict]:
        try:
            with self.get_connection() as db:
                cursor = db.execute(
                    "SELECT id, telegram_user_id, username, first_name FROM users WHERE telegram_user_id = ?",
                    (telegram_user_id,)
                )
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'telegram_user_id': row[1],
                        'username': row[2],
                        'first_name': row[3]
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting user by Telegram ID: {e}")
            return None
