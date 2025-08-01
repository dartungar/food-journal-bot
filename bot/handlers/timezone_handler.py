import pytz
from telegram import Update
from telegram.ext import ContextTypes
from services.database_service import DatabaseService
import os
import logging

logger = logging.getLogger(__name__)

# Set up database service
DB_PATH = os.getenv('DATABASE_PATH', '/app/data/food_journal.db')
database_service = DatabaseService(DB_PATH)

async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set the user's timezone. Usage: /settimezone Europe/Berlin"""
    user_id = update.effective_user.id
    args = context.args
    try:
        if not args:
            logger.info(f"User {user_id} did not provide a timezone argument.")
            await update.message.reply_text(
                "Please provide a timezone. Example: /settimezone Europe/Berlin\n"
                "See the list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"
            )
            return
        tz = args[0]
        if tz not in pytz.all_timezones:
            logger.warning(f"User {user_id} provided invalid timezone: {tz}")
            await update.message.reply_text(
                f"'{tz}' is not a valid timezone. Please use a valid tz name (e.g., Europe/Berlin).\n"
                "See: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"
            )
            return
        # Update user timezone in DB
        try:
            # Use DatabaseService methods, not .db
            user = database_service.get_user_by_telegram_id(user_id)
            if user:
                db_username = user.get('username')
                db_first_name = user.get('first_name')
                database_service.create_or_update_user(user_id, db_username, db_first_name, tz)
                logger.info(f"Updated timezone for user {user_id} to {tz}")
            else:
                database_service.create_or_update_user(user_id, timezone=tz)
                logger.info(f"Created user {user_id} with timezone {tz}")
            await update.message.reply_text(f"Your timezone has been set to: {tz}")
        except Exception as db_exc:
            logger.error(f"Database error while setting timezone for user {user_id}: {db_exc}")
            await update.message.reply_text("❌ Failed to update your timezone due to a server error. Please try again later.")
    except Exception as exc:
        logger.error(f"Unexpected error in set_timezone for user {user_id}: {exc}")
        await update.message.reply_text("❌ An unexpected error occurred. Please try again later.")
