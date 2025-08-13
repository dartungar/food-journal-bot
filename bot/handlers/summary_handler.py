import os
import pytz
from telegram import Update
from telegram.ext import ContextTypes
from services.ai_summary_service import AISummaryService
from services.database_service import DatabaseService
from datetime import datetime, timedelta
from handlers.food_handler import get_user_language

db_path = os.getenv('DATABASE_PATH', '/app/data/food_journal.db')
database_service = DatabaseService(db_path)
ai_summary_service = AISummaryService(os.getenv('OPENAI_API_KEY'), database_service)

def get_user_today_date(user_id: int) -> str:
    """Get today's date in the user's timezone, fallback to UTC"""
    try:
        user = database_service.get_user_by_telegram_id(user_id)
        if user and user.get('timezone'):
            user_tz = pytz.timezone(user['timezone'])
            now_in_user_tz = datetime.now(user_tz)
            return now_in_user_tz.strftime('%Y-%m-%d')
    except Exception:
        pass  # Fallback to UTC
    
    # Fallback to UTC if no timezone is set or error occurs
    return datetime.now(pytz.UTC).strftime('%Y-%m-%d')

async def daily_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provide AI-generated daily nutrition summary"""
    user_id = update.effective_user.id
    today = get_user_today_date(user_id)
    user_language = get_user_language(user_id)
    
    loading_message = "🤖 Generating your personalized daily summary... This may take a moment." if user_language == 'en' else "🤖 Генерирую твой персонализированный дневной отчет... Это может занять некоторое время."
    no_data_message = "📅 No food entries found for today, or unable to generate AI analysis. Start logging your meals! 📸" if user_language == 'en' else "📅 Записи о еде на сегодня не найдены или не удается сгенерировать AI анализ. Начните логировать ваши приемы пищи! 📸"
    error_message = "❌ Unable to generate AI summary right now. Please try again later." if user_language == 'en' else "❌ Не удается сгенерировать AI отчет прямо сейчас. Попробуйте еще раз позже."
    
    await update.message.reply_text(loading_message)
    
    try:
        ai_summary = await ai_summary_service.generate_daily_summary(user_id, today, user_language)
        
        if ai_summary:
            if user_language == 'ru':
                message = f"🌙 **AI Дневной отчет о питании - {today}**\n\n"
                message += f"📋 **Резюме:**\n{ai_summary.summary}\n\n"
                
                if ai_summary.key_observations:
                    message += "🔍 **Ключевые наблюдения:**\n"
                    for obs in ai_summary.key_observations:
                        message += f"• {obs}\n"
                    message += "\n"
                
                if ai_summary.nutrition_highlights:
                    message += "⭐ **Особенности питания:**\n"
                    for highlight in ai_summary.nutrition_highlights:
                        message += f"• {highlight}\n"
                    message += "\n"
                
                if ai_summary.recommendations:
                    message += "💡 **Рекомендации:**\n"
                    for rec in ai_summary.recommendations:
                        message += f"• {rec}\n"
                    message += "\n"
            else:  # English
                message = f"🌙 **AI Daily Nutrition Summary - {today}**\n\n"
                message += f"📋 **Summary:**\n{ai_summary.summary}\n\n"
                
                if ai_summary.key_observations:
                    message += "🔍 **Key Observations:**\n"
                    for obs in ai_summary.key_observations:
                        message += f"• {obs}\n"
                    message += "\n"
                
                if ai_summary.nutrition_highlights:
                    message += "⭐ **Nutrition Highlights:**\n"
                    for highlight in ai_summary.nutrition_highlights:
                        message += f"• {highlight}\n"
                    message += "\n"
                
                if ai_summary.recommendations:
                    message += "💡 **Recommendations:**\n"
                    for rec in ai_summary.recommendations:
                        message += f"• {rec}\n"
                    message += "\n"
            
            message += f"🌟 **{ai_summary.motivational_message}**"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text(no_data_message)
            
    except Exception as e:
        print(f"Error generating daily AI summary: {e}")
        await update.message.reply_text(error_message)

async def weekly_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provide AI-generated weekly nutrition summary"""
    user_id = update.effective_user.id
    user_language = get_user_language(user_id)
    
    loading_message = "🤖 Analyzing your weekly nutrition patterns... This may take a moment." if user_language == 'en' else "🤖 Анализирую ваши недельные паттерны питания... Это может занять некоторое время."
    no_data_message = "📊 Not enough data for AI weekly analysis. Keep logging your meals!" if user_language == 'en' else "📊 Недостаточно данных для AI недельного анализа. Продолжайте логировать ваши приемы пищи!"
    error_message = "❌ Unable to generate AI weekly analysis right now. Please try again later." if user_language == 'en' else "❌ Не удается сгенерировать AI недельный анализ прямо сейчас. Попробуйте еще раз позже."
    
    await update.message.reply_text(loading_message)
    
    try:
        ai_summary = await ai_summary_service.generate_weekly_summary(user_id, user_language)
        
        if ai_summary:
            if user_language == 'ru':
                message = f"📊 **AI Недельный анализ питания**\n\n"
                message += f"📝 **Недельное резюме:**\n{ai_summary.summary}\n\n"
                
                if ai_summary.trends_analysis:
                    message += "📈 **Анализ трендов:**\n"
                    for trend in ai_summary.trends_analysis:
                        message += f"• {trend}\n"
                    message += "\n"
                
                if ai_summary.achievements:
                    message += "🏆 **Достижения этой недели:**\n"
                    for achievement in ai_summary.achievements:
                        message += f"• {achievement}\n"
                    message += "\n"
                
                if ai_summary.areas_for_improvement:
                    message += "🎯 **Области для улучшения:**\n"
                    for area in ai_summary.areas_for_improvement:
                        message += f"• {area}\n"
                    message += "\n"
                
                if ai_summary.personalized_recommendations:
                    message += "� **Персональные рекомендации:**\n"
                    for rec in ai_summary.personalized_recommendations:
                        message += f"• {rec}\n"
                    message += "\n"
                
                if ai_summary.next_week_goals:
                    message += "🚀 **Цели на следующую неделю:**\n"
                    for goal in ai_summary.next_week_goals:
                        message += f"• {goal}\n"
            else:  # English
                message = f"�📊 **AI Weekly Nutrition Analysis**\n\n"
                message += f"📝 **Weekly Summary:**\n{ai_summary.summary}\n\n"
                
                if ai_summary.trends_analysis:
                    message += "📈 **Trends Analysis:**\n"
                    for trend in ai_summary.trends_analysis:
                        message += f"• {trend}\n"
                    message += "\n"
                
                if ai_summary.achievements:
                    message += "🏆 **This Week's Achievements:**\n"
                    for achievement in ai_summary.achievements:
                        message += f"• {achievement}\n"
                    message += "\n"
                
                if ai_summary.areas_for_improvement:
                    message += "🎯 **Areas for Improvement:**\n"
                    for area in ai_summary.areas_for_improvement:
                        message += f"• {area}\n"
                    message += "\n"
                
                if ai_summary.personalized_recommendations:
                    message += "💡 **Personalized Recommendations:**\n"
                    for rec in ai_summary.personalized_recommendations:
                        message += f"• {rec}\n"
                    message += "\n"
                
                if ai_summary.next_week_goals:
                    message += "🚀 **Goals for Next Week:**\n"
                    for goal in ai_summary.next_week_goals:
                        message += f"• {goal}\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text(no_data_message)
            
    except Exception as e:
        print(f"Error generating weekly AI summary: {e}")
        await update.message.reply_text(error_message)