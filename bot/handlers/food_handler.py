import logging
import os
import base64
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from services.ai_service import AIFoodAnalyzer
from services.clarification_service import ClarificationService
from services.compliment_service import compliment_service
from services.language_service import language_service
from services.database_service import DatabaseService

ai_analyzer = AIFoodAnalyzer(os.getenv('OPENAI_API_KEY'))
clarification_service = ClarificationService()
logger = logging.getLogger(__name__)

# Access control: get allowed user IDs from env variable
def get_allowed_user_ids():
    allowed = os.getenv('ALLOWED_USER_IDS', '')
    return set(int(uid.strip()) for uid in allowed.split(',') if uid.strip().isdigit())

def is_user_allowed(user_id):
    return user_id in get_allowed_user_ids()

def get_user_language(user_id: int, user_input: str = None) -> str:
    """Get user's language preference, with fallback to detection"""
    try:
        db_path = os.getenv('DATABASE_PATH', '/app/data/food_journal.db')
        database_service = DatabaseService(db_path)
        stored_language = database_service.get_user_language(user_id)
        
        # If we have user input and no stored language, detect from input
        if stored_language == 'en' and user_input:
            detected_language = language_service.detect_language(user_input)
            if detected_language != 'en':
                # Update user's language preference
                database_service.create_or_update_user(user_id, language=detected_language)
                return detected_language
        
        return stored_language
    except Exception as e:
        logger.error(f"Error getting user language: {e}")
        # Fallback to detection if database fails
        if user_input:
            return language_service.detect_language(user_input)
        return 'en'

async def store_and_respond_analysis(update: Update, analysis, user_id: int, is_clarification: bool = False, user_language: str = 'en'):
    """Helper function to store analysis in database and send response to user"""
    try:
        # Store in SQLite
        from services.database_service import DatabaseService
        db_path = os.getenv('DATABASE_PATH', '/app/data/food_journal.db')
        database_service = DatabaseService(db_path)
        username = update.effective_user.username or ""
        first_name = update.effective_user.first_name or ""
        logger.info(f"Storing analysis in database for user {user_id}.")
        stored = database_service.store_food_analysis(user_id, username, first_name, analysis, language=user_language)
        
        if stored:
            # Get localized messages
            messages = language_service.get_messages(user_language)
            
            # Format response using language service
            response = language_service.format_nutrition_response(
                user_language, analysis, is_clarification=is_clarification
            )
            
            # Add compliment for healthy food choices
            compliment = compliment_service.generate_response_with_compliment(analysis.food_items, language=user_language)
            if compliment:
                response += f"\n\n{compliment}"
            
            await update.message.reply_text(response, parse_mode='Markdown')
            logger.info(f"Analysis sent to user {user_id}.")
        else:
            messages = language_service.get_messages(user_language)
            logger.error(f"Failed to store analysis in database for user {user_id}.")
            await update.message.reply_text(messages.failed_to_save)
    except Exception as e:
        messages = language_service.get_messages(user_language)
        logger.exception(f"Error storing and responding analysis for user {user_id}: {e}")
        await update.message.reply_text(messages.error_occurred)

async def handle_food_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle food photo upload and analysis"""
    user_id = update.effective_user.id

    if not is_user_allowed(user_id):
        logger.warning(f"Unauthorized access attempt by user {user_id}.")
        user_language = get_user_language(user_id)
        messages = language_service.get_messages(user_language)
        await update.message.reply_text(messages.unauthorized)
        return

    if not update.message.photo:
        logger.warning(f"User {user_id} sent a message without a photo.")
        user_language = get_user_language(user_id)
        messages = language_service.get_messages(user_language)
        await update.message.reply_text("Please send a photo of your food!" if user_language == 'en' else "Пожалуйста, отправьте фото вашей еды!")
        return

    # Check if user has pending clarification
    if clarification_service.has_pending_clarification(user_id):
        await handle_clarification_photo(update, context)
        return

    # Get user language for last known language (for images we use stored preference)
    user_language = get_user_language(user_id)
    messages = language_service.get_messages(user_language)

    logger.info(f"User {user_id} sent a photo. Starting analysis.")
    await update.message.reply_text(messages.analyzing_food)

    try:
        # Get the largest photo
        photo = update.message.photo[-1]
        logger.info(f"Downloading photo file for user {user_id}.")
        photo_file = await context.bot.get_file(photo.file_id)
        photo_bytes = await photo_file.download_as_bytearray()
        logger.info(f"Photo file downloaded for user {user_id}, size: {len(photo_bytes)} bytes.")

        # Analyze with AI
        logger.info(f"Sending photo to AI analyzer for user {user_id}.")
        analysis = await ai_analyzer.analyze_food_image(bytes(photo_bytes), user_language=user_language)
        logger.info(f"AI analysis result for user {user_id}: {analysis}")

        if analysis:
            # Check for uncertainty
            if analysis.uncertainty and analysis.uncertainty.has_uncertainty:
                # Store pending clarification
                original_data = {
                    'photo_bytes': base64.b64encode(photo_bytes).decode('utf-8'),
                    'analysis_text': str(analysis)  # Store the full analysis for later use
                }
                
                clarification_service.store_pending_clarification(
                    user_id=user_id,
                    original_data=original_data,
                    analysis_text=str(analysis),
                    uncertain_items=analysis.uncertainty.uncertain_items,
                    uncertainty_reasons=analysis.uncertainty.uncertainty_reasons,
                    media_type='photo'
                )
                
                # Ask for clarification in user's language
                clarification_msg = language_service.format_clarification_request(
                    user_language, analysis
                )
                
                await update.message.reply_text(clarification_msg, parse_mode='Markdown')
                logger.info(f"Asked user {user_id} for clarification due to uncertainties.")
                return
            
            # No uncertainty - proceed with storage
            await store_and_respond_analysis(update, analysis, user_id, user_language=user_language)
            
        else:
            logger.warning(f"AI analysis failed or returned no result for user {user_id}.")
            await update.message.reply_text(messages.analysis_failed)
    except Exception as e:
        logger.exception(f"Error handling food photo for user {user_id}: {e}")
        messages = language_service.get_messages(user_language)
        await update.message.reply_text(messages.error_occurred)


async def handle_clarification_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle clarification photo from user"""
    user_id = update.effective_user.id
    
    try:
        pending = clarification_service.get_pending_clarification(user_id)
        if not pending:
            user_language = get_user_language(user_id)
            messages = language_service.get_messages(user_language)
            await update.message.reply_text(messages.no_pending_clarification)
            return
        
        # Get user language
        user_language = get_user_language(user_id)
        messages = language_service.get_messages(user_language)
        
        logger.info(f"Processing clarification photo for user {user_id}.")
        await update.message.reply_text(messages.processing_clarification)
        
        # Get clarification photo
        photo = update.message.photo[-1]
        photo_file = await context.bot.get_file(photo.file_id)
        photo_bytes = await photo_file.download_as_bytearray()
        
        # Combine original analysis with clarification
        analysis = await ai_analyzer.analyze_with_clarification(
            original_analysis_text=pending.analysis_text,
            clarification_data=bytes(photo_bytes),
            clarification_type='photo',
            user_language=user_language
        )
        
        if analysis:
            # Clear pending clarification
            clarification_service.clear_pending_clarification(user_id)
            
            # Store and respond
            await store_and_respond_analysis(update, analysis, user_id, is_clarification=True, user_language=user_language)
        else:
            await update.message.reply_text(messages.analysis_failed)
            
    except Exception as e:
        logger.exception(f"Error handling clarification photo for user {user_id}: {e}")
        user_language = get_user_language(user_id)
        messages = language_service.get_messages(user_language)
        await update.message.reply_text(messages.error_occurred)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages describing food for analysis"""
    user_id = update.effective_user.id

    if not is_user_allowed(user_id):
        logger.warning(f"Unauthorized access attempt by user {user_id}.")
        user_language = get_user_language(user_id)
        messages = language_service.get_messages(user_language)
        await update.message.reply_text(messages.unauthorized)
        return

    if not update.message.text:
        logger.warning(f"User {user_id} sent a message without text.")
        user_language = get_user_language(user_id)
        messages = language_service.get_messages(user_language)
        await update.message.reply_text("Please send a text description of your food!" if user_language == 'en' else "Пожалуйста, отправьте текстовое описание вашей еды!")
        return

    text_description = update.message.text.strip()
    
    # Detect and get user language
    user_language = get_user_language(user_id, text_description)
    messages = language_service.get_messages(user_language)
    
    # Check if user has pending clarification
    if clarification_service.has_pending_clarification(user_id):
        await handle_clarification_text(update, context, text_description)
        return

    logger.info(f"User {user_id} sent text message: {text_description[:100]}...")
    await update.message.reply_text(messages.analyzing_text)

    try:
        # Analyze with AI
        logger.info(f"Sending text to AI analyzer for user {user_id}.")
        analysis = await ai_analyzer.analyze_food_text(text_description, user_language=user_language)
        logger.info(f"AI analysis result for user {user_id}: {analysis}")

        if analysis:
            # Check for uncertainty
            if analysis.uncertainty and analysis.uncertainty.has_uncertainty:
                # Store pending clarification
                original_data = {
                    'text_description': text_description,
                    'analysis_text': str(analysis)
                }
                
                clarification_service.store_pending_clarification(
                    user_id=user_id,
                    original_data=original_data,
                    analysis_text=str(analysis),
                    uncertain_items=analysis.uncertainty.uncertain_items,
                    uncertainty_reasons=analysis.uncertainty.uncertainty_reasons,
                    media_type='text'
                )
                
                # Ask for clarification in user's language
                clarification_msg = language_service.format_clarification_request(
                    user_language, analysis, description=text_description, is_text=True
                )
                
                await update.message.reply_text(clarification_msg, parse_mode='Markdown')
                logger.info(f"Asked user {user_id} for clarification due to uncertainties in text.")
                return
            
            # No uncertainty - proceed with storage
            await store_and_respond_text_analysis(update, analysis, text_description, user_id, user_language=user_language)
            
        else:
            logger.warning(f"AI analysis failed or returned no result for user {user_id}.")
            await update.message.reply_text(messages.analysis_failed)
    except Exception as e:
        logger.exception(f"Error handling text message for user {user_id}: {e}")
        await update.message.reply_text(messages.error_occurred)


async def handle_clarification_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text_description: str):
    """Handle clarification text from user"""
    user_id = update.effective_user.id
    
    try:
        pending = clarification_service.get_pending_clarification(user_id)
        if not pending:
            user_language = get_user_language(user_id, text_description)
            messages = language_service.get_messages(user_language)
            await update.message.reply_text(messages.no_pending_clarification)
            return
        
        # Detect language from clarification text
        user_language = get_user_language(user_id, text_description)
        messages = language_service.get_messages(user_language)
        
        logger.info(f"Processing clarification text for user {user_id}.")
        await update.message.reply_text(messages.processing_clarification)
        
        # For text clarification, we can use the analyze_food_text method with clarification
        original_text = pending.original_data.get('text_description', '')
        analysis = await ai_analyzer.analyze_food_text(
            text_description=original_text,
            clarification_text=text_description,
            user_language=user_language
        )
        
        if analysis:
            # Clear pending clarification
            clarification_service.clear_pending_clarification(user_id)
            
            # Store and respond with the original text description
            original_text = pending.original_data.get('text_description', 'Text clarification provided')
            await store_and_respond_text_analysis(update, analysis, original_text, user_id, is_clarification=True, user_language=user_language)
        else:
            await update.message.reply_text(messages.analysis_failed)
            
    except Exception as e:
        logger.exception(f"Error handling clarification text for user {user_id}: {e}")
        user_language = get_user_language(user_id, text_description)
        messages = language_service.get_messages(user_language)
        await update.message.reply_text(messages.error_occurred)


async def store_and_respond_text_analysis(update: Update, analysis, text_description: str, user_id: int, is_clarification: bool = False, user_language: str = 'en'):
    """Helper function to store text analysis in database and send response to user"""
    try:
        # Store in SQLite
        from services.database_service import DatabaseService
        db_path = os.getenv('DATABASE_PATH', '/app/data/food_journal.db')
        database_service = DatabaseService(db_path)
        username = update.effective_user.username or ""
        first_name = update.effective_user.first_name or ""
        logger.info(f"Storing analysis in database for user {user_id}.")
        stored = database_service.store_food_analysis(user_id, username, first_name, analysis, language=user_language)

        if stored:
            # Format response using language service
            response = language_service.format_nutrition_response(
                user_language, analysis, description=text_description, 
                is_clarification=is_clarification, is_text=True
            )
            
            # Add compliment for healthy food choices
            compliment = compliment_service.generate_response_with_compliment(analysis.food_items, language=user_language)
            if compliment:
                response += f"\n\n{compliment}"
            
            await update.message.reply_text(response, parse_mode='Markdown')
            logger.info(f"Analysis sent to user {user_id}.")
        else:
            messages = language_service.get_messages(user_language)
            logger.error(f"Failed to store analysis in database for user {user_id}.")
            await update.message.reply_text(messages.failed_to_save)
    except Exception as e:
        messages = language_service.get_messages(user_language)
        logger.exception(f"Error storing and responding text analysis for user {user_id}: {e}")
        await update.message.reply_text(messages.error_occurred)


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle audio messages and voice notes for food analysis"""
    user_id = update.effective_user.id
    
    if not is_user_allowed(user_id):
        logger.warning(f"Unauthorized access attempt by user {user_id}.")
        user_language = get_user_language(user_id)
        messages = language_service.get_messages(user_language)
        await update.message.reply_text(messages.unauthorized)
        return
    
    # Check for both voice and audio messages
    audio_file = None
    filename = "audio.ogg"
    
    if update.message.voice:
        audio_file = update.message.voice
        filename = "voice_message.ogg"
        logger.info(f"User {user_id} sent a voice message.")
    elif update.message.audio:
        audio_file = update.message.audio
        filename = getattr(audio_file, 'file_name', 'audio_message.mp3')
        logger.info(f"User {user_id} sent an audio file.")
    else:
        logger.warning(f"User {user_id} sent a message without audio or voice.")
        user_language = get_user_language(user_id)
        messages = language_service.get_messages(user_language)
        await update.message.reply_text("Please send a voice message or audio file describing your food!" if user_language == 'en' else "Пожалуйста, отправьте голосовое сообщение или аудиофайл, описывающий вашу еду!")
        return
    
    # Check if user has pending clarification
    if clarification_service.has_pending_clarification(user_id):
        await handle_clarification_audio(update, context, audio_file, filename)
        return
    
    # Get user language (will be determined after transcription)
    user_language = get_user_language(user_id)
    messages = language_service.get_messages(user_language)
    
    logger.info(f"User {user_id} sent audio. Starting analysis.")
    await update.message.reply_text(messages.analyzing_audio)
    
    try:
        # Download audio file
        logger.info(f"Downloading audio file for user {user_id}.")
        audio_telegram_file = await context.bot.get_file(audio_file.file_id)
        audio_bytes = await audio_telegram_file.download_as_bytearray()
        logger.info(f"Audio file downloaded for user {user_id}, size: {len(audio_bytes)} bytes.")

        # Analyze with AI (transcription + food analysis)
        logger.info(f"Sending audio to AI analyzer for user {user_id}.")
        result = await ai_analyzer.analyze_food_audio(bytes(audio_bytes), filename, user_language=user_language)
        
        if result:
            analysis, transcribed_text = result
            
            # Update user language based on transcription if needed
            detected_language = language_service.detect_language(transcribed_text)
            if detected_language != user_language:
                user_language = get_user_language(user_id, transcribed_text)
                messages = language_service.get_messages(user_language)
            
            logger.info(f"AI analysis result for user {user_id}: {analysis}")
            logger.info(f"Transcription for user {user_id}: {transcribed_text[:100]}...")

            # Check for uncertainty
            if analysis.uncertainty and analysis.uncertainty.has_uncertainty:
                # Store pending clarification
                original_data = {
                    'audio_bytes': base64.b64encode(audio_bytes).decode('utf-8'),
                    'filename': filename,
                    'transcribed_text': transcribed_text,
                    'analysis_text': str(analysis)
                }
                
                clarification_service.store_pending_clarification(
                    user_id=user_id,
                    original_data=original_data,
                    analysis_text=str(analysis),
                    uncertain_items=analysis.uncertainty.uncertain_items,
                    uncertainty_reasons=analysis.uncertainty.uncertainty_reasons,
                    media_type='audio'
                )
                
                # Ask for clarification in user's language
                clarification_msg = language_service.format_clarification_request(
                    user_language, analysis, description=transcribed_text, is_audio=True
                )
                
                await update.message.reply_text(clarification_msg, parse_mode='Markdown')
                logger.info(f"Asked user {user_id} for clarification due to uncertainties in audio.")
                return

            # No uncertainty - proceed with storage
            await store_and_respond_audio_analysis(update, analysis, transcribed_text, user_id, user_language=user_language)

        else:
            logger.warning(f"AI analysis failed or returned no result for user {user_id}.")
            await update.message.reply_text(messages.analysis_failed)
            
    except Exception as e:
        logger.exception(f"Error handling audio for user {user_id}: {e}")
        messages = language_service.get_messages(user_language)
        await update.message.reply_text(messages.error_occurred)


async def handle_clarification_audio(update: Update, context: ContextTypes.DEFAULT_TYPE, audio_file, filename: str):
    """Handle clarification audio from user"""
    user_id = update.effective_user.id
    
    try:
        pending = clarification_service.get_pending_clarification(user_id)
        if not pending:
            user_language = get_user_language(user_id)
            messages = language_service.get_messages(user_language)
            await update.message.reply_text(messages.no_pending_clarification)
            return
        
        # Get user language
        user_language = get_user_language(user_id)
        messages = language_service.get_messages(user_language)
        
        logger.info(f"Processing clarification audio for user {user_id}.")
        await update.message.reply_text(messages.processing_clarification)
        
        # Get clarification audio
        audio_telegram_file = await context.bot.get_file(audio_file.file_id)
        audio_bytes = await audio_telegram_file.download_as_bytearray()
        
        # Combine original analysis with clarification
        analysis = await ai_analyzer.analyze_with_clarification(
            original_analysis_text=pending.analysis_text,
            clarification_data=bytes(audio_bytes),
            clarification_type='audio',
            filename=filename,
            user_language=user_language
        )
        
        if analysis:
            # Clear pending clarification
            clarification_service.clear_pending_clarification(user_id)
            
            # For audio clarification, we need to get the transcription too
            if pending.media_type == 'audio':
                # Use original transcription if available
                transcribed_text = pending.original_data.get('transcribed_text', 'Audio clarification provided')
                await store_and_respond_audio_analysis(update, analysis, transcribed_text, user_id, is_clarification=True, user_language=user_language)
            else:
                await store_and_respond_analysis(update, analysis, user_id, is_clarification=True, user_language=user_language)
        else:
            await update.message.reply_text(messages.analysis_failed)
            
    except Exception as e:
        logger.exception(f"Error handling clarification audio for user {user_id}: {e}")
        user_language = get_user_language(user_id)
        messages = language_service.get_messages(user_language)
        await update.message.reply_text(messages.error_occurred)


async def store_and_respond_audio_analysis(update: Update, analysis, transcribed_text: str, user_id: int, is_clarification: bool = False, user_language: str = 'en'):
    """Helper function to store audio analysis in database and send response to user"""
    try:
        # Store in SQLite
        from services.database_service import DatabaseService
        db_path = os.getenv('DATABASE_PATH', '/app/data/food_journal.db')
        database_service = DatabaseService(db_path)
        username = update.effective_user.username or ""
        first_name = update.effective_user.first_name or ""
        logger.info(f"Storing analysis in database for user {user_id}.")
        stored = database_service.store_food_analysis(user_id, username, first_name, analysis, language=user_language)

        if stored:
            # Format response using language service
            response = language_service.format_nutrition_response(
                user_language, analysis, description=transcribed_text, 
                is_clarification=is_clarification, is_audio=True
            )
            
            # Add compliment for healthy food choices
            compliment = compliment_service.generate_response_with_compliment(analysis.food_items, language=user_language)
            if compliment:
                response += f"\n\n{compliment}"
            
            await update.message.reply_text(response, parse_mode='Markdown')
            logger.info(f"Analysis sent to user {user_id}.")
        else:
            messages = language_service.get_messages(user_language)
            logger.error(f"Failed to store analysis in database for user {user_id}.")
            await update.message.reply_text(messages.failed_to_save)
    except Exception as e:
        messages = language_service.get_messages(user_language)
        logger.exception(f"Error storing and responding audio analysis for user {user_id}: {e}")
        await update.message.reply_text(messages.error_occurred)


async def cancel_clarification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel pending clarification request"""
    user_id = update.effective_user.id
    
    if not is_user_allowed(user_id):
        logger.warning(f"Unauthorized access attempt by user {user_id}.")
        user_language = get_user_language(user_id)
        messages = language_service.get_messages(user_language)
        await update.message.reply_text(messages.unauthorized)
        return
    
    user_language = get_user_language(user_id)
    messages = language_service.get_messages(user_language)
    
    if clarification_service.has_pending_clarification(user_id):
        clarification_service.clear_pending_clarification(user_id)
        await update.message.reply_text(messages.clarification_cancelled)
        logger.info(f"User {user_id} cancelled pending clarification.")
    else:
        await update.message.reply_text(messages.no_pending_clarification)


async def check_clarification_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if user has pending clarification"""
    user_id = update.effective_user.id
    
    if not is_user_allowed(user_id):
        logger.warning(f"Unauthorized access attempt by user {user_id}.")
        user_language = get_user_language(user_id)
        messages = language_service.get_messages(user_language)
        await update.message.reply_text(messages.unauthorized)
        return
    
    user_language = get_user_language(user_id)
    messages = language_service.get_messages(user_language)
    
    if clarification_service.has_pending_clarification(user_id):
        pending = clarification_service.get_pending_clarification(user_id)
        time_diff = datetime.now() - pending.timestamp
        
        status_msg = messages.pending_clarification_status
        if user_language == 'ru':
            status_msg += f"**Время:** {time_diff.seconds // 60} минут назад\n"
            status_msg += f"**Тип медиа:** {pending.media_type.title()}\n"
            status_msg += f"**Неопределённые продукты:** {', '.join(pending.uncertain_items) if pending.uncertain_items else 'Не указано'}\n\n"
            status_msg += "Пожалуйста, отправьте уточнение (фото, голосовое сообщение или текстовое описание) или используйте /cancel для начала заново."
        else:
            status_msg += f"**Time:** {time_diff.seconds // 60} minutes ago\n"
            status_msg += f"**Media Type:** {pending.media_type.title()}\n"
            status_msg += f"**Uncertain Items:** {', '.join(pending.uncertain_items) if pending.uncertain_items else 'None specified'}\n\n"
            status_msg += "Please send clarification (photo, voice message, or text description) or use /cancel to start over."
        
        await update.message.reply_text(status_msg, parse_mode='Markdown')
    else:
        if user_language == 'ru':
            await update.message.reply_text("ℹ️ Нет ожидающих запросов на уточнение. Отправьте фото еды, голосовое сообщение или текстовое описание, чтобы начать!")
        else:
            await update.message.reply_text("ℹ️ No pending clarification requests. Send a food photo, voice message, or text description to get started!")