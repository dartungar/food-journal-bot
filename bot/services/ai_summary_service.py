from openai import OpenAI
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from services.database_service import DatabaseService

class DailyInsight(BaseModel):
    summary: str
    key_observations: List[str]
    nutrition_highlights: List[str]
    recommendations: List[str]
    motivational_message: str

class WeeklyInsight(BaseModel):
    summary: str
    trends_analysis: List[str]
    nutrition_patterns: List[str]
    achievements: List[str]
    areas_for_improvement: List[str]
    personalized_recommendations: List[str]
    next_week_goals: List[str]

class AISummaryService:
    def __init__(self, openai_api_key: str, database_service: DatabaseService):
        self.client = OpenAI(api_key=openai_api_key)
        self.database_service = database_service
    
    async def generate_daily_summary(self, telegram_user_id: int, date_str: str) -> Optional[DailyInsight]:
        """Generate AI-powered daily nutrition summary"""
        try:
            # Get user's food data for the day
            daily_entries = await self._get_daily_nutrition_data(telegram_user_id, date_str)
            
            if not daily_entries:
                return None
            
            # Get recent context (last 7 days for comparison)
            context_data = await self._get_recent_context(telegram_user_id, date_str, days=7)
            
            # Prepare data for AI analysis
            nutrition_data = self._format_daily_data_for_ai(daily_entries, context_data, date_str)
            
            system_prompt = """You are a professional nutritionist and health coach. Analyze the user's daily nutrition data and provide personalized insights.

Focus on:
1. Overall nutritional balance and quality
2. Calorie adequacy 
3. Macronutrient distribution
4. Meal timing and frequency
5. Progress compared to recent days
6. Specific food choices and their nutritional value

Be encouraging, specific, and actionable. Avoid medical advice. Keep tone friendly and motivational."""

            user_prompt = f"""Analyze today's nutrition data and provide insights:

{nutrition_data}

Please provide a comprehensive daily summary with specific observations about food choices, nutritional balance, and actionable recommendations for tomorrow."""

            response = await self.client.beta.chat.completions.parse(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="gpt-4o-mini",
                response_format=DailyInsight,
                temperature=0.7
            )
            
            if response.choices[0].message.parsed:
                return response.choices[0].message.parsed
            return None
            
        except Exception as e:
            print(f"Error generating daily AI summary: {e}")
            return None
    
    async def generate_weekly_summary(self, telegram_user_id: int) -> Optional[WeeklyInsight]:
        """Generate AI-powered weekly nutrition analysis"""
        try:
            # Get user's food data for the past week
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            weekly_data = await self.database_service.get_weekly_data(
                telegram_user_id, 
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            
            if not weekly_data:
                return None
            
            # Get previous week for comparison
            prev_week_data = await self.database_service.get_weekly_data(
                telegram_user_id,
                (start_date - timedelta(days=7)).strftime('%Y-%m-%d'),
                start_date.strftime('%Y-%m-%d')
            )
            
            # Format data for AI analysis
            nutrition_analysis = self._format_weekly_data_for_ai(weekly_data, prev_week_data)
            
            system_prompt = """You are an expert nutritionist analyzing a week of eating patterns. Provide comprehensive insights about:

1. Weekly nutrition trends and patterns
2. Consistency in eating habits
3. Macronutrient balance over time
4. Food variety and quality
5. Progress compared to previous week
6. Specific achievements and improvements needed
7. Personalized goals for next week

Be insightful, encouraging, and provide actionable recommendations. Focus on sustainable habits and positive reinforcement."""

            user_prompt = f"""Analyze this week's nutrition data and provide comprehensive insights:

{nutrition_analysis}

Provide detailed weekly analysis with trends, achievements, areas for improvement, and specific goals for next week."""

            response = await self.client.beta.chat.completions.parse(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="gpt-4o-mini",
                response_format=WeeklyInsight,
                temperature=0.7
            )
            
            if response.choices[0].message.parsed:
                return response.choices[0].message.parsed
            return None
            
        except Exception as e:
            print(f"Error generating weekly AI summary: {e}")
            return None
    
    def _get_daily_nutrition_data(self, telegram_user_id: int, date_str: str) -> List[Dict]:
        """Get detailed nutrition data for a specific day"""
        return self.database_service.get_weekly_data(telegram_user_id, date_str, date_str)
    
    def _get_recent_context(self, telegram_user_id: int, current_date: str, days: int = 7) -> List[Dict]:
        """Get recent nutrition data for context"""
        try:
            end_date = datetime.strptime(current_date, '%Y-%m-%d')
            start_date = end_date - timedelta(days=days)
            return self.database_service.get_weekly_data(
                telegram_user_id,
                start_date.strftime('%Y-%m-%d'),
                current_date
            )
        except Exception as e:
            print(f"Error getting recent context: {e}")
            return []
    
    def _format_daily_data_for_ai(self, daily_entries: List[Dict], context_data: List[Dict], date_str: str) -> str:
        """Format daily nutrition data for AI analysis"""
        formatted_data = f"=== DAILY NUTRITION ANALYSIS - {date_str} ===\n\n"
        
        if not daily_entries:
            return formatted_data + "No food entries logged today."
        
        total_calories = sum(entry.get('total_calories', 0) for entry in daily_entries)
        total_protein = sum(entry.get('total_protein', 0) for entry in daily_entries)
        total_carbs = sum(entry.get('total_carbs', 0) for entry in daily_entries)
        total_fat = sum(entry.get('total_fat', 0) for entry in daily_entries)
        
        formatted_data += f"DAILY TOTALS:\n"
        formatted_data += f"- Calories: {total_calories:.0f} kcal\n"
        formatted_data += f"- Protein: {total_protein:.1f}g ({(total_protein * 4 / total_calories * 100):.1f}% of calories)\n"
        formatted_data += f"- Carbs: {total_carbs:.1f}g ({(total_carbs * 4 / total_calories * 100):.1f}% of calories)\n"
        formatted_data += f"- Fat: {total_fat:.1f}g ({(total_fat * 9 / total_calories * 100):.1f}% of calories)\n"
        formatted_data += f"- Meals logged: {len(daily_entries)}\n\n"
        
        formatted_data += "MEAL BREAKDOWN:\n"
        for i, entry in enumerate(daily_entries, 1):
            meal_time = entry.get('timestamp', '').split('T')[1][:5] if 'T' in entry.get('timestamp', '') else 'Unknown time'
            formatted_data += f"\nMeal {i} ({meal_time}):\n"
            formatted_data += f"  Total: {entry.get('total_calories', 0):.0f} kcal, "
            formatted_data += f"{entry.get('total_protein', 0):.1f}g protein, "
            formatted_data += f"{entry.get('total_carbs', 0):.1f}g carbs, "
            formatted_data += f"{entry.get('total_fat', 0):.1f}g fat\n"
            
            if 'food_items' in entry:
                formatted_data += "  Foods consumed:\n"
                for item in entry['food_items']:
                    formatted_data += f"    - {item.get('name', 'Unknown')} ({item.get('quantity', 'Unknown amount')}): "
                    formatted_data += f"{item.get('calories', 0):.0f} kcal\n"
        
        # Add context from recent days
        if context_data:
            recent_avg_calories = sum(e.get('total_calories', 0) for e in context_data) / len(context_data)
            formatted_data += f"\n7-DAY CONTEXT:\n"
            formatted_data += f"- Average daily calories (last 7 days): {recent_avg_calories:.0f} kcal\n"
            formatted_data += f"- Today vs recent average: {((total_calories - recent_avg_calories) / recent_avg_calories * 100):+.1f}%\n"
        
        return formatted_data
    
    def _format_weekly_data_for_ai(self, weekly_data: List[Dict], prev_week_data: List[Dict]) -> str:
        """Format weekly nutrition data for AI analysis"""
        if not weekly_data:
            return "No nutrition data available for this week."
        
        # Group by day
        daily_totals = {}
        daily_foods = {}
        
        for entry in weekly_data:
            date = entry.get('timestamp', '')[:10]
            if date not in daily_totals:
                daily_totals[date] = {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'meals': 0}
                daily_foods[date] = []
            
            daily_totals[date]['calories'] += entry.get('total_calories', 0)
            daily_totals[date]['protein'] += entry.get('total_protein', 0)
            daily_totals[date]['carbs'] += entry.get('total_carbs', 0)
            daily_totals[date]['fat'] += entry.get('total_fat', 0)
            daily_totals[date]['meals'] += 1
            
            if 'food_items' in entry:
                daily_foods[date].extend([item.get('name', 'Unknown') for item in entry['food_items']])
        
        formatted_data = "=== WEEKLY NUTRITION ANALYSIS ===\n\n"
        
        # Weekly averages
        days_tracked = len(daily_totals)
        if days_tracked > 0:
            avg_calories = sum(day['calories'] for day in daily_totals.values()) / days_tracked