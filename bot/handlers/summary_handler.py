import os
from telegram import Update
from telegram.ext import ContextTypes
from services.ai_summary_service import AISummaryService
from services.database_service import DatabaseService
from datetime import datetime, timedelta

db_path = os.getenv('DATABASE_PATH', '/app/data/food_journal.db')
database_service = DatabaseService(db_path)
ai_summary_service = AISummaryService(os.getenv('OPENAI_API_KEY'), database_service)

async def daily_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provide AI-generated daily nutrition summary"""
    user_id = update.effective_user.id
    today = datetime.now().strftime('%Y-%m-%d')
    
    await update.message.reply_text("🤖 Generating your personalized daily summary... This may take a moment.")
    
    try:
        ai_summary = await ai_summary_service.generate_daily_summary(user_id, today)
        
        if ai_summary:
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
            await update.message.reply_text("📅 No food entries found for today, or unable to generate AI analysis. Start logging your meals! 📸")
            
    except Exception as e:
        print(f"Error generating daily AI summary: {e}")
        await update.message.reply_text("❌ Unable to generate AI summary right now. Please try again later.")

async def weekly_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provide AI-generated weekly nutrition summary"""
    user_id = update.effective_user.id
    
    await update.message.reply_text("🤖 Analyzing your weekly nutrition patterns... This may take a moment.")
    
    try:
        ai_summary = await ai_summary_service.generate_weekly_summary(user_id)
        
        if ai_summary:
            message = f"📊 **AI Weekly Nutrition Analysis**\n\n"
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
            await update.message.reply_text("📊 Not enough data for AI weekly analysis. Keep logging your meals!")
            
    except Exception as e:
        print(f"Error generating weekly AI summary: {e}")
        await update.message.reply_text("❌ Unable to generate AI weekly analysis right now. Please try again later.")