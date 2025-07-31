from database.database import Database
from database.models import FoodEntry, FoodItem
from models.nutrition_models import FoodAnalysisResponse, DailySummary, WeeklySummary
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def store_food_analysis(self, telegram_user_id: int, username: str, first_name: str, 
                            analysis: FoodAnalysisResponse) -> bool:
        """Store food analysis in database"""
        from database.database import Database
        try:
            db = Database(self.db_path)
            # Defensive: skip DB insert if no food items
            if not analysis.food_items:
                logger.warning(f"No food items extracted for user {telegram_user_id}, skipping DB insert.")
                return False
            # Create or update user
            user_id = db.create_or_update_user(telegram_user_id, username, first_name)
            # Create food entry
            food_entry = FoodEntry(
                user_id=user_id,
                timestamp=analysis.analysis_timestamp,
                total_calories=analysis.total_nutrition.calories,
                total_protein=analysis.total_nutrition.protein,
                total_carbs=analysis.total_nutrition.carbs,
                total_fat=analysis.total_nutrition.fat,
                total_fiber=analysis.total_nutrition.fiber,
                total_sugar=analysis.total_nutrition.sugar,
                meal_count=len(analysis.food_items)
            )
            # Create food items
            food_items = []
            for item in analysis.food_items:
                food_items.append(FoodItem(
                    name=item.name,
                    quantity=item.quantity,
                    calories=getattr(item.nutrition, 'calories', 0.0),
                    protein=getattr(item.nutrition, 'protein', 0.0),
                    carbs=getattr(item.nutrition, 'carbs', 0.0),
                    fat=getattr(item.nutrition, 'fat', 0.0),
                    fiber=getattr(item.nutrition, 'fiber', 0.0),
                    sugar=getattr(item.nutrition, 'sugar', 0.0),
                    confidence=item.confidence
                ))
            return db.create_food_entry(food_entry, food_items)
        except Exception as e:
            logger.error(f"Error storing food analysis: {e}")
            return False
    
    def get_daily_summary(self, telegram_user_id: int, date_str: str) -> Optional[DailySummary]:
        """Get daily summary for user"""
        try:
            db = Database(self.db_path)
            user = db.get_user_by_telegram_id(telegram_user_id)
            if not user:
                return None
            summary_data = db.get_daily_summary(user['id'], date_str)
            if summary_data:
                return DailySummary(
                    date=summary_data['date'],
                    total_calories=summary_data['total_calories'],
                    total_protein=summary_data['total_protein'],
                    total_carbs=summary_data['total_carbs'],
                    total_fat=summary_data['total_fat'],
                    meal_count=summary_data['meal_count']
                )
            return None
        except Exception as e:
            logger.error(f"Error getting daily summary: {e}")
            return None
    
    def get_weekly_data(self, telegram_user_id: int, start_date: str, end_date: str) -> List[Dict]:
        """Get weekly data for user"""
        try:
            db = Database(self.db_path)
            user = db.get_user_by_telegram_id(telegram_user_id)
            if not user:
                return []
            return db.get_food_entries_with_items(user['id'], start_date, end_date)
        except Exception as e:
            logger.error(f"Error getting weekly data: {e}")
            return []
    
    def get_all_telegram_user_ids(self) -> List[int]:
        """Get all Telegram user IDs for automated summaries"""
        try:
            db = Database(self.db_path)
            user_ids = db.get_all_user_ids()
            telegram_ids = []
            for user_id in user_ids:
                with db.get_connection() as conn:
                    cursor = conn.execute(
                        "SELECT telegram_user_id FROM users WHERE id = ?",
                        (user_id,)
                    )
                    row = cursor.fetchone()
                    if row:
                        telegram_ids.append(row[0])
            return telegram_ids
        except Exception as e:
            logger.error(f"Error getting all Telegram user IDs: {e}")
            return []