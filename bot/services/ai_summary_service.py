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
    
    def _get_daily_system_prompt(self, language: str) -> str:
        """Get system prompt for daily summary in specified language"""
        if language == 'ru':
            return """Ты профессиональный диетолог и консультант по здоровому питанию. Проанализируй дневные данные о питании пользователя и предоставь персонализированные рекомендации.

Сосредоточься на:
1. Общем балансе питания и качестве
2. Адекватности калорий
3. Распределении макронутриентов
4. Времени приема пищи и частоте
5. Прогрессе по сравнению с предыдущими днями
6. Конкретных выборах продуктов и их питательной ценности

Будь ободряющим, конкретным и практичным. Избегай медицинских советов. Поддерживай дружелюбный и мотивирующий тон.

ВАЖНО: Делай ответы очень краткими. Каждое поле должно быть кратким:
- summary: максимум 1-2 предложения
- key_observations: максимум 2-3 коротких пункта
- nutrition_highlights: максимум 2-3 коротких пункта
- recommendations: максимум 2-3 коротких пункта
- motivational_message: максимум 1 предложение

Ответь в формате JSON:
{
  "summary": "Краткое общее резюме дневного питания (1-2 предложения)",
  "key_observations": ["короткое наблюдение 1", "короткое наблюдение 2"],
  "nutrition_highlights": ["короткий акцент 1", "короткий акцент 2"],
  "recommendations": ["короткая рекомендация 1", "короткая рекомендация 2"],
  "motivational_message": "Короткое ободряющее сообщение"
}"""
        else:  # Default to English
            return """You are a professional nutritionist and health coach. Analyze the user's daily nutrition data and provide personalized insights.

Focus on:
1. Overall nutritional balance and quality
2. Calorie adequacy 
3. Macronutrient distribution
4. Meal timing and frequency
5. Progress compared to recent days
6. Specific food choices and their nutritional value

Be encouraging, specific, and actionable. Avoid medical advice. Keep tone friendly and motivational.

IMPORTANT: Keep responses very concise. Each field should be brief:
- summary: 1-2 sentences max
- key_observations: 2-3 short bullet points max
- nutrition_highlights: 2-3 short bullet points max  
- recommendations: 2-3 short bullet points max
- motivational_message: 1 sentence max

Please respond with a JSON object containing:
{
  "summary": "Brief overall summary of the day's nutrition (1-2 sentences)",
  "key_observations": ["short observation 1", "short observation 2"],
  "nutrition_highlights": ["short highlight 1", "short highlight 2"],
  "recommendations": ["short recommendation 1", "short recommendation 2"],
  "motivational_message": "Short encouraging message"
}"""
    
    def _get_weekly_system_prompt(self, language: str) -> str:
        """Get system prompt for weekly summary in specified language"""
        if language == 'ru':
            return """Ты эксперт-диетолог, анализирующий недельные паттерны питания. Предоставь комплексные insights о:

1. Недельных трендах и паттернах питания
2. Последовательности в привычках питания
3. Балансе макронутриентов во времени
4. Разнообразии и качестве продуктов
5. Прогрессе по сравнению с предыдущей неделей
6. Конкретных достижениях и областях для улучшения
7. Персонализированных целях на следующую неделю

Будь проницательным, ободряющим и предоставляй практичные рекомендации. Сосредоточься на устойчивых привычках и позитивном подкреплении.

ВАЖНО: Делай ответы очень краткими. Каждое поле должно быть кратким:
- summary: максимум 1-2 предложения
- Каждое поле массива: максимум 2-3 коротких пункта
- Каждый пункт: максимум 1 предложение

Ответь в формате JSON:
{
  "summary": "Краткое недельное резюме (1-2 предложения)",
  "trends_analysis": ["короткий тренд 1", "короткий тренд 2"],
  "nutrition_patterns": ["короткий паттерн 1", "короткий паттерн 2"],
  "achievements": ["короткое достижение 1", "короткое достижение 2"],
  "areas_for_improvement": ["короткая область 1", "короткая область 2"],
  "personalized_recommendations": ["короткая рек. 1", "короткая рек. 2"],
  "next_week_goals": ["короткая цель 1", "короткая цель 2"]
}"""
        else:  # Default to English
            return """You are an expert nutritionist analyzing a week of eating patterns. Provide comprehensive insights about:

1. Weekly nutrition trends and patterns
2. Consistency in eating habits
3. Macronutrient balance over time
4. Food variety and quality
5. Progress compared to previous week
6. Specific achievements and improvements needed
7. Personalized goals for next week

Be insightful, encouraging, and provide actionable recommendations. Focus on sustainable habits and positive reinforcement.

IMPORTANT: Keep responses very concise. Each field should be brief:
- summary: 1-2 sentences max
- Each array field: 2-3 short bullet points max
- Each bullet point: 1 sentence max

Please respond with a JSON object containing:
{
  "summary": "Brief weekly summary (1-2 sentences)",
  "trends_analysis": ["short trend 1", "short trend 2"],
  "nutrition_patterns": ["short pattern 1", "short pattern 2"],
  "achievements": ["short achievement 1", "short achievement 2"],
  "areas_for_improvement": ["short area 1", "short area 2"],
  "personalized_recommendations": ["short rec 1", "short rec 2"],
  "next_week_goals": ["short goal 1", "short goal 2"]
}"""
    
    async def generate_daily_summary(self, telegram_user_id: int, date_str: str, language: str = 'en') -> Optional[DailyInsight]:
        """Generate AI-powered daily nutrition summary"""
        try:
            # Get user's food data for the day
            daily_entries = self._get_daily_nutrition_data(telegram_user_id, date_str)
            
            if not daily_entries:
                return None
            
            # Get recent context (last 7 days for comparison)
            context_data = self._get_recent_context(telegram_user_id, date_str, days=7)
            
            # Prepare data for AI analysis
            nutrition_data = self._format_daily_data_for_ai(daily_entries, context_data, date_str)
            
            system_prompt = self._get_daily_system_prompt(language)

            user_prompt_text = "Analyze today's nutrition data and provide insights:" if language == 'en' else "Проанализируй сегодняшние данные о питании и предоставь insights:"
            concise_instruction = "Please provide a CONCISE daily summary. Keep all responses short and focused - aim for 1-2 sentences per section maximum." if language == 'en' else "Предоставь КРАТКИЙ дневной отчет. Держи все ответы короткими и сфокусированными - стремись к максимум 1-2 предложениям на секцию."
            
            user_prompt = f"""{user_prompt_text}

{nutrition_data}

{concise_instruction}"""

            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="gpt-5-mini",
                max_completion_tokens=2048,
                reasoning_effort="minimal"
            )
            
            if response.choices[0].message.content:
                # Parse the response manually since we're not using structured output
                content = response.choices[0].message.content
                try:
                    import json
                    parsed_data = json.loads(content)
                    return DailyInsight(
                        summary=parsed_data.get('summary', ''),
                        key_observations=parsed_data.get('key_observations', []),
                        nutrition_highlights=parsed_data.get('nutrition_highlights', []),
                        recommendations=parsed_data.get('recommendations', []),
                        motivational_message=parsed_data.get('motivational_message', '')
                    )
                except (json.JSONDecodeError, KeyError):
                    # Fallback: create a simple summary from the content
                    return DailyInsight(
                        summary=content,
                        key_observations=[],
                        nutrition_highlights=[],
                        recommendations=[],
                        motivational_message="Keep up the great work with your nutrition tracking!"
                    )
            return None
            
        except Exception as e:
            print(f"Error generating daily AI summary: {e}")
            return None
    
    async def generate_weekly_summary(self, telegram_user_id: int, language: str = 'en') -> Optional[WeeklyInsight]:
        """Generate AI-powered weekly nutrition analysis"""
        try:
            # Get user's food data for the past week
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            weekly_data = self.database_service.get_weekly_data(
                telegram_user_id, 
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            
            if not weekly_data:
                return None
            
            # Get previous week for comparison
            prev_week_data = self.database_service.get_weekly_data(
                telegram_user_id,
                (start_date - timedelta(days=7)).strftime('%Y-%m-%d'),
                start_date.strftime('%Y-%m-%d')
            )
            
            # Format data for AI analysis
            nutrition_analysis = self._format_weekly_data_for_ai(weekly_data, prev_week_data)
            
            system_prompt = self._get_weekly_system_prompt(language)

            user_prompt_text = "Analyze this week's nutrition data and provide insights:" if language == 'en' else "Проанализируй данные о питании за эту неделю и предоставь insights:"
            concise_instruction = "Please provide a CONCISE weekly analysis. Keep all responses short and focused - aim for 1-2 sentences per bullet point maximum." if language == 'en' else "Предоставь КРАТКИЙ недельный анализ. Держи все ответы короткими и сфокусированными - стремись к максимум 1-2 предложениям на пункт."
            
            user_prompt = f"""{user_prompt_text}

{nutrition_analysis}

{concise_instruction}"""

            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="gpt-5-mini"
            )
            
            if response.choices[0].message.content:
                # Parse the response manually since we're not using structured output
                content = response.choices[0].message.content
                try:
                    import json
                    parsed_data = json.loads(content)
                    return WeeklyInsight(
                        summary=parsed_data.get('summary', ''),
                        trends_analysis=parsed_data.get('trends_analysis', []),
                        nutrition_patterns=parsed_data.get('nutrition_patterns', []),
                        achievements=parsed_data.get('achievements', []),
                        areas_for_improvement=parsed_data.get('areas_for_improvement', []),
                        personalized_recommendations=parsed_data.get('personalized_recommendations', []),
                        next_week_goals=parsed_data.get('next_week_goals', [])
                    )
                except (json.JSONDecodeError, KeyError):
                    # Fallback: create a simple summary from the content
                    return WeeklyInsight(
                        summary=content,
                        trends_analysis=[],
                        nutrition_patterns=[],
                        achievements=[],
                        areas_for_improvement=[],
                        personalized_recommendations=[],
                        next_week_goals=[]
                    )
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