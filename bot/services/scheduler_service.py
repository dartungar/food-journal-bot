import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from services.ai_summary_service import AISummaryService
from services.database_service import DatabaseService
from telegram import Bot
import os
import logging

logger = logging.getLogger(__name__)

class AutomatedSummaryService:
    def __init__(self, bot: Bot, database_service: DatabaseService, ai_summary_service: AISummaryService):
        self.bot = bot
        self.database_service = database_service
        self.ai_summary_service = ai_summary_service
        self.scheduler = AsyncIOScheduler()
        
    def start_scheduler(self):
        """Start the automated AI summary scheduler"""
        # Daily AI summary at 9 PM every day
        self.scheduler.add_job(
            self.send_daily_ai_summaries,
            CronTrigger(hour=21, minute=0),  # 9:00 PM
            id='daily_ai_summary',
            replace_existing=True
        )

        # Weekly AI summary on Sundays at 8 PM
        self.scheduler.add_job(
            self.send_weekly_ai_summaries,
            CronTrigger(day_of_week=6, hour=20, minute=0),  # Sunday 8:00 PM
            id='weekly_ai_summary',
            replace_existing=True
        )

        # Food tracking reminders at 10:00, 15:00, and 20:00 every day
        self.scheduler.add_job(
            self.send_food_reminder,
            CronTrigger(hour=10, minute=0),
            id='food_reminder_10',
            replace_existing=True
        )
        self.scheduler.add_job(
            self.send_food_reminder,
            CronTrigger(hour=15, minute=0),
            id='food_reminder_15',
            replace_existing=True
        )
        self.scheduler.add_job(
            self.send_food_reminder,
            CronTrigger(hour=20, minute=0),
            id='food_reminder_20',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Automated AI summary scheduler started")
    async def send_food_reminder(self):
        """Send a reminder to all users to track their food"""
        try:
            user_ids = self.database_service.db.get_all_user_ids()
            reminder_message = (
                "⏰ **Don't forget to track your food!**\n\n"
                "Send a photo or description of your meal to keep your nutrition log up to date.\n\n"
                "Consistent tracking helps you get the best AI insights! 📸🥗"
            )
            for user_id in user_ids:
                try:
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=reminder_message,
                        parse_mode='Markdown'
                    )
                    await asyncio.sleep(0.5)  # Avoid rate limiting
                except Exception as e:
                    logger.error(f"Error sending food reminder to user {user_id}: {e}")
        except Exception as e:
            logger.error(f"Error in send_food_reminder: {e}")
    
    async def send_daily_ai_summaries(self):
        """Send AI-generated daily summaries to all users"""
        try:
            user_ids = self.database_service.db.get_all_user_ids()
            today = datetime.now().strftime('%Y-%m-%d')
            
            logger.info(f"Generating AI daily summaries for {len(user_ids)} users")
            
            for user_id in user_ids:
                try:
                    # Generate AI summary
                    ai_summary = await self.ai_summary_service.generate_daily_summary(user_id, today)
                    
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
                            message += "💡 **Recommendations for Tomorrow:**\n"
                            for rec in ai_summary.recommendations:
                                message += f"• {rec}\n"
                            message += "\n"
                        
                        message += f"🌟 **{ai_summary.motivational_message}**"
                        
                        await self.bot.send_message(
                            chat_id=user_id,
                            text=message,
                            parse_mode='Markdown'
                        )
                        
                        logger.info(f"Sent AI daily summary to user {user_id}")
                        
                        # Small delay to avoid rate limiting
                        await asyncio.sleep(1)
                    else:
                        # Send simple message if no data or AI analysis failed
                        fallback_msg = "🌙 **Daily Check-in**\n\nNo meals logged today. Don't forget to track your nutrition tomorrow! 📸"
                        await self.bot.send_message(
                            chat_id=user_id,
                            text=fallback_msg,
                            parse_mode='Markdown'
                        )
                        
                except Exception as e:
                    logger.error(f"Error sending daily AI summary to user {user_id}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in send_daily_ai_summaries: {e}")
    
    async def send_weekly_ai_summaries(self):
        """Send AI-generated weekly summaries to all users"""
        try:
            user_ids = self.database_service.db.get_all_user_ids()
            
            logger.info(f"Generating AI weekly summaries for {len(user_ids)} users")
            
            for user_id in user_ids:
                try:
                    # Generate AI weekly analysis
                    ai_summary = await self.ai_summary_service.generate_weekly_summary(user_id)
                    
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
                            message += "\n"
                        
                        message += "Keep up the fantastic work! 🌟"
                        
                        await self.bot.send_message(
                            chat_id=user_id,
                            text=message,
                            parse_mode='Markdown'
                        )
                        
                        logger.info(f"Sent AI weekly summary to user {user_id}")
                        
                        # Small delay to avoid rate limiting
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    logger.error(f"Error sending weekly AI summary to user {user_id}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in send_weekly_ai_summaries: {e}")
    
    def stop_scheduler(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Automated AI summary scheduler stopped")