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
from handlers.food_handler import handle_food_photo, handle_audio, handle_text_message, cancel_clarification, check_clarification_status, get_user_language
from handlers.summary_handler import daily_summary, weekly_summary
from handlers.timezone_handler import set_timezone
from services.ai_summary_service import AISummaryService
from services.scheduler_service import AutomatedSummaryService
from services.database_service import DatabaseService
from services.clarification_service import ClarificationService
from services.language_service import language_service
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
    
    # Detect language from any additional text in the command
    command_text = update.message.text if update.message.text else ""
    user_language = get_user_language(user_id, command_text)
    messages = language_service.get_messages(user_language)
    
    await update.message.reply_text(messages.welcome_message, parse_mode='Markdown')
    logger.info(f"New user started: {user_id} (language: {user_language})")

async def help_command(update, context):
    user_id = update.effective_user.id
    
    # Detect language
    command_text = update.message.text if update.message.text else ""
    user_language = get_user_language(user_id, command_text)
    messages = language_service.get_messages(user_language)
    
    await update.message.reply_text(messages.help_message, parse_mode='Markdown')

async def set_language(update, context):
    """Set language preference command handler"""
    user_id = update.effective_user.id
    
    # Check if language was provided
    if context.args and len(context.args) > 0:
        requested_language = context.args[0].lower()
        
        if requested_language in ['en', 'english', 'английский']:
            new_language = 'en'
        elif requested_language in ['ru', 'russian', 'русский']:
            new_language = 'ru'
        else:
            # Default to detecting from the command text
            command_text = update.message.text if update.message.text else ""
            current_language = get_user_language(user_id, command_text)
            messages = language_service.get_messages(current_language)
            await update.message.reply_text(messages.language_help_message)
            return
        
        # Update user language in database
        from services.database_service import DatabaseService
        db_path = os.getenv('DATABASE_PATH', '/app/data/food_journal.db')
        db_service = DatabaseService(db_path)
        db_service.update_user_language(user_id, new_language)
        
        # Send confirmation in the new language
        messages = language_service.get_messages(new_language)
        await update.message.reply_text(messages.language_set_message)
        logger.info(f"User {user_id} changed language to {new_language}")
    else:
        # No arguments provided, show help
        current_language = get_user_language(user_id, "")
        messages = language_service.get_messages(current_language)
        await update.message.reply_text(messages.language_help_message)

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
    application.add_handler(CommandHandler('setlanguage', set_language))
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
