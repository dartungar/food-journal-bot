
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class DailySummary(BaseModel):
    date: str
    total_calories: float = 0.0
    total_protein: float = 0.0
    total_carbs: float = 0.0
    total_fat: float = 0.0
    meal_count: int = 0


class WeeklySummary(BaseModel):
    start_date: str
    end_date: str
    avg_calories: float = 0.0
    avg_protein: float = 0.0
    avg_carbs: float = 0.0
    avg_fat: float = 0.0
    total_meals: int = 0


class NutritionInfo(BaseModel):
    calories: float = 0.0
    protein: float = 0.0
    carbs: float = 0.0
    fat: float = 0.0
    fiber: float = 0.0
    sugar: float = 0.0


class FoodItem(BaseModel):
    name: str
    quantity: Optional[str] = None
    nutrition: NutritionInfo = Field(default_factory=NutritionInfo)
    confidence: Optional[float] = None


class FoodAnalysisResponse(BaseModel):
    food_items: List[FoodItem] = Field(default_factory=list)
    total_nutrition: NutritionInfo = Field(default_factory=NutritionInfo)
    analysis_timestamp: Optional[datetime] = None
