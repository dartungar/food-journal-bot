# === Event Loop Policy Fix for Python 3.10+ (Docker, all platforms) ===
import sys
import asyncio
if sys.version_info >= (3, 10):
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

# === Imports ===
import os
import sys
import logging
import asyncio
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from handlers.food_handler import handle_food_photo, handle_audio, handle_text_message, cancel_clarification, check_clarification_status
from handlers.summary_handler import daily_summary, weekly_summary
from handlers.timezone_handler import set_timezone
from services.ai_summary_service import AISummaryService
from services.scheduler_service import AutomatedSummaryService
from services.database_service import DatabaseService
from services.clarification_service import ClarificationService
from database.database import Database


# === Load environment variables ===
load_dotenv()

# === Logging ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('/app/logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# === Global Services ===


# === Command Handlers ===
async def start(update, context):
    """Start command handler"""
    user_id = update.effective_user.id
    welcome_message = (
        "🍽️ **Welcome to AI Food Journal Bot!**\n\n"
        "📸 **Send me a photo of your food** and I'll analyze it for you!\n"
        "🎤 **Send me a voice message** describing what you ate!\n"
        "📝 **Send me a text message** describing your meal!\n\n"
        "**Available Commands:**\n"
        "/daily - Get AI-generated daily nutrition summary\n"
        "/weekly - Get AI-powered weekly analysis with insights\n"
        "/settimezone <tz> - Set your timezone (e.g., /settimezone Europe/Berlin)\n"
        "/status - Check if you have pending clarification requests\n"
        "/cancel - Cancel pending clarification and start over\n"
        "/help - Show this help message\n\n"
        "**🤖 AI-Powered Features:**\n"
        "🌙 **Smart Daily Summaries** - Delivered at 9 PM with personalized insights\n"
        "📊 **Weekly AI Analysis** - Comprehensive reports every Sunday at 8 PM\n"
        "💡 **Personalized Recommendations** - Based on your actual eating patterns\n"
        "🧠 **Smart Clarification** - I'll ask for clarification when uncertain about your food\n\n"
        "Just send a food photo, voice message, or text description to get started! 🚀"
    )
    await update.message.reply_text(welcome_message, parse_mode='Markdown')
    logger.info(f"New user started: {user_id}")

async def help_command(update, context):
    help_text = (
        "🤖 **AI Food Journal Bot Help**\n\n"
        "**How to use:**\n"
        "1. 📸 Send a photo of your food OR 🎤 Send a voice message OR 📝 Send a text message describing it\n"
        "2. 🤖 I'll analyze it with AI and log the nutrition info\n"
        "3. 🧠 If I'm uncertain, I'll ask for clarification before saving\n"
        "4. 📊 Get personalized AI summaries automatically\n\n"
        "**Commands:**\n"
        "/daily - Get today's AI nutrition analysis\n"
        "/weekly - Get this week's AI-powered insights\n"
        "/settimezone <tz> - Set your timezone (e.g., /settimezone Europe/Berlin)\n"
        "/status - Check if you have pending clarification requests\n"
        "/cancel - Cancel pending clarification and start over\n"
        "/start - Welcome message\n"
        "/help - This help message\n\n"
        "**🧠 Smart Clarification Process:**\n"
        "1. Send your food photo/audio/text\n"
        "2. If I'm uncertain, I'll ask for clarification\n"
        "3. Send another photo/voice/text message to clarify\n"
        "4. I'll combine both to create accurate nutrition data\n\n"
        "**🧠 AI Features:**\n"
        "🌙 **Daily AI Summaries (9 PM):**\n"
        "• Personalized nutrition analysis\n"
        "• Specific observations about your food choices\n"
        "• Tomorrow's recommendations\n\n"
        "📊 **Weekly AI Analysis (Sunday 8 PM):**\n"
        "• Comprehensive eating pattern analysis\n"
        "• Trend identification and achievements\n"
        "• Personalized goals for next week\n\n"
        "**Tips:**\n"
        "• Take clear, well-lit photos of your entire meal\n"
        "• Speak clearly when recording voice messages\n"
        "• Be specific about quantities and ingredients in text descriptions"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

# === Entrypoint ===

def init_database():
    from database.database import Database
    db_path = os.getenv('DATABASE_PATH', '/app/data/food_journal.db')
    db = Database(db_path)
    db.initialize()

async def cleanup_expired_clarifications(context):
    """Periodic cleanup of expired clarifications - job queue callback"""
    try:
        clarification_service = ClarificationService()
        clarification_service.cleanup_expired_clarifications(max_age_hours=24)
        logger.info("Completed clarification cleanup")
    except Exception as e:
        logger.error(f"Error in clarification cleanup: {e}")

if __name__ == "__main__":
    # Initialize database (async, but outside main event loop)
    init_database()

    # Set up Telegram bot
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()

    # Register handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('daily', daily_summary))
    application.add_handler(CommandHandler('weekly', weekly_summary))
    application.add_handler(CommandHandler('settimezone', set_timezone))
    application.add_handler(CommandHandler('cancel', cancel_clarification))
    application.add_handler(CommandHandler('status', check_clarification_status))
    application.add_handler(MessageHandler(filters.PHOTO, handle_food_photo))
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_audio))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # Schedule cleanup job to run every hour
    job_queue = application.job_queue
    job_queue.run_repeating(cleanup_expired_clarifications, interval=3600, first=60)

    # Start polling (blocking call)
    logger.info('Bot started. Listening for messages...')
    application.run_polling()
