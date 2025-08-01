
from typing import List, Optional, Dict, Any
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


class UncertaintyInfo(BaseModel):
    """Information about AI uncertainty in food analysis"""
    has_uncertainty: bool = False
    uncertain_items: List[str] = Field(default_factory=list)
    uncertainty_reasons: List[str] = Field(default_factory=list)
    confidence_score: float = 1.0


class FoodAnalysisResponse(BaseModel):
    food_items: List[FoodItem] = Field(default_factory=list)
    total_nutrition: NutritionInfo = Field(default_factory=NutritionInfo)
    analysis_timestamp: Optional[datetime] = None
    uncertainty: Optional[UncertaintyInfo] = None


class PendingClarification(BaseModel):
    """Stores information about pending clarification request"""
    user_id: int
    original_data: Dict[str, Any]  # Store original image/audio data
    analysis_text: str  # Original AI analysis text
    uncertain_items: List[str]
    uncertainty_reasons: List[str]
    timestamp: datetime
    media_type: str  # 'photo' or 'audio'
