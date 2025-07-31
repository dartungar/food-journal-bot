from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass
class User:
    id: int
    telegram_user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class FoodEntry:
    id: Optional[int] = None
    user_id: int = 0
    timestamp: datetime = None
    total_calories: float = 0.0
    total_protein: float = 0.0
    total_carbs: float = 0.0
    total_fat: float = 0.0
    total_fiber: Optional[float] = None
    total_sugar: Optional[float] = None
    meal_count: int = 0
    created_at: Optional[datetime] = None

@dataclass
class FoodItem:
    id: Optional[int] = None
    food_entry_id: int = 0
    name: str = ""
    quantity: str = ""
    calories: float = 0.0
    protein: float = 0.0
    carbs: float = 0.0
    fat: float = 0.0
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    confidence: float = 0.0
    created_at: Optional[datetime] = None