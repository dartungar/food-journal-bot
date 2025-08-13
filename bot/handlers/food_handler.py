import logging
import os
import base64
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from services.ai_service import AIFoodAnalyzer
from services.clarification_service import ClarificationService
from services.compliment_service import compliment_service

ai_analyzer = AIFoodAnalyzer(os.getenv('OPENAI_API_KEY'))
clarification_service = ClarificationService()
logger = logging.getLogger(__name__)

# Access control: get allowed user IDs from env variable
def get_allowed_user_ids():
    allowed = os.getenv('ALLOWED_USER_IDS', '')
    return set(int(uid.strip()) for uid in allowed.split(',') if uid.strip().isdigit())

def is_user_allowed(user_id):
    return user_id in get_allowed_user_ids()

async def store_and_respond_analysis(update: Update, analysis, user_id: int, is_clarification: bool = False):
    """Helper function to store analysis in database and send response to user"""
    try:
        # Store in SQLite
        from services.database_service import DatabaseService
        db_path = os.getenv('DATABASE_PATH', '/app/data/food_journal.db')
        database_service = DatabaseService(db_path)
        username = update.effective_user.username or ""
        first_name = update.effective_user.first_name or ""
        logger.info(f"Storing analysis in database for user {user_id}.")
        stored = database_service.store_food_analysis(user_id, username, first_name, analysis)
        
        if stored:
            # Format response message
            if is_clarification:
                response = "✅ **Clarification processed! Final Food Analysis:**\n\n"
            else:
                response = "🍽️ **Food Analysis Complete!**\n\n"
                
            for item in analysis.food_items:
                response += f"📍 **{item.name}** ({item.quantity})\n"
                response += f"   • Calories: {getattr(item.nutrition, 'calories', 0.0):.0f} kcal\n"
                response += f"   • Protein: {getattr(item.nutrition, 'protein', 0.0):.1f}g\n"
                response += f"   • Carbs: {getattr(item.nutrition, 'carbs', 0.0):.1f}g\n"
                response += f"   • Fat: {getattr(item.nutrition, 'fat', 0.0):.1f}g\n\n"
            response += f"**📊 Total Nutrition:**\n"
            response += f"🔥 Calories: {analysis.total_nutrition.calories:.0f} kcal\n"
            response += f"💪 Protein: {analysis.total_nutrition.protein:.1f}g\n"
            response += f"🌾 Carbs: {analysis.total_nutrition.carbs:.1f}g\n"
            response += f"🥑 Fat: {analysis.total_nutrition.fat:.1f}g"
            
            # Add compliment for healthy food choices
            compliment = compliment_service.generate_response_with_compliment(analysis.food_items)
            if compliment:
                response += f"\n\n{compliment}"
            
            await update.message.reply_text(response, parse_mode='Markdown')
            logger.info(f"Analysis sent to user {user_id}.")
        else:
            logger.error(f"Failed to store analysis in database for user {user_id}.")
            await update.message.reply_text("❌ Failed to save food entry. Please try again.")
    except Exception as e:
        logger.exception(f"Error storing and responding analysis for user {user_id}: {e}")
        await update.message.reply_text("❌ An error occurred while saving your food entry. Please try again.")

async def handle_food_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle food photo upload and analysis"""
    user_id = update.effective_user.id

    if not is_user_allowed(user_id):
        logger.warning(f"Unauthorized access attempt by user {user_id}.")
        await update.message.reply_text("🚫 You are not authorized to use this bot.")
        return

    if not update.message.photo:
        logger.warning(f"User {user_id} sent a message without a photo.")
        await update.message.reply_text("Please send a photo of your food!")
        return

    # Check if user has pending clarification
    if clarification_service.has_pending_clarification(user_id):
        await handle_clarification_photo(update, context)
        return

    logger.info(f"User {user_id} sent a photo. Starting analysis.")
    await update.message.reply_text("🔍 Analyzing your food... This may take a moment.")

    try:
        # Get the largest photo
        photo = update.message.photo[-1]
        logger.info(f"Downloading photo file for user {user_id}.")
        photo_file = await context.bot.get_file(photo.file_id)
        photo_bytes = await photo_file.download_as_bytearray()
        logger.info(f"Photo file downloaded for user {user_id}, size: {len(photo_bytes)} bytes.")

        # Analyze with AI
        logger.info(f"Sending photo to AI analyzer for user {user_id}.")
        analysis = await ai_analyzer.analyze_food_image(bytes(photo_bytes))
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
                
                # Ask for clarification
                clarification_msg = "⚠️ I have some uncertainties about your food:\n\n"
                
                if analysis.uncertainty.uncertain_items:
                    clarification_msg += "**Uncertain items:**\n"
                    for item in analysis.uncertainty.uncertain_items:
                        clarification_msg += f"• {item}\n"
                    clarification_msg += "\n"
                
                if analysis.uncertainty.uncertainty_reasons:
                    clarification_msg += "**Reasons for uncertainty:**\n"
                    for reason in analysis.uncertainty.uncertainty_reasons:
                        clarification_msg += f"• {reason}\n"
                    clarification_msg += "\n"
                
                clarification_msg += (
                    "Please send another photo, voice message, or text description with clarification "
                    "so I can provide accurate nutrition information!"
                )
                
                await update.message.reply_text(clarification_msg, parse_mode='Markdown')
                logger.info(f"Asked user {user_id} for clarification due to uncertainties.")
                return
            
            # No uncertainty - proceed with storage
            await store_and_respond_analysis(update, analysis, user_id)
            
        else:
            logger.warning(f"AI analysis failed or returned no result for user {user_id}.")
            await update.message.reply_text("❌ Could not analyze the food image. Please try with a clearer photo.")
    except Exception as e:
        logger.exception(f"Error handling food photo for user {user_id}: {e}")
        await update.message.reply_text("❌ An error occurred while analyzing your food. Please try again.")


async def handle_clarification_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle clarification photo from user"""
    user_id = update.effective_user.id
    
    try:
        pending = clarification_service.get_pending_clarification(user_id)
        if not pending:
            await update.message.reply_text("❌ No pending clarification found.")
            return
        
        logger.info(f"Processing clarification photo for user {user_id}.")
        await update.message.reply_text("🔍 Processing your clarification... This may take a moment.")
        
        # Get clarification photo
        photo = update.message.photo[-1]
        photo_file = await context.bot.get_file(photo.file_id)
        photo_bytes = await photo_file.download_as_bytearray()
        
        # Combine original analysis with clarification
        analysis = await ai_analyzer.analyze_with_clarification(
            original_analysis_text=pending.analysis_text,
            clarification_data=bytes(photo_bytes),
            clarification_type='photo'
        )
        
        if analysis:
            # Clear pending clarification
            clarification_service.clear_pending_clarification(user_id)
            
            # Store and respond
            await store_and_respond_analysis(update, analysis, user_id, is_clarification=True)
        else:
            await update.message.reply_text("❌ Could not process clarification. Please try again.")
            
    except Exception as e:
        logger.exception(f"Error handling clarification photo for user {user_id}: {e}")
        await update.message.reply_text("❌ An error occurred while processing clarification. Please try again.")


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages describing food for analysis"""
    user_id = update.effective_user.id

    if not is_user_allowed(user_id):
        logger.warning(f"Unauthorized access attempt by user {user_id}.")
        await update.message.reply_text("🚫 You are not authorized to use this bot.")
        return

    if not update.message.text:
        logger.warning(f"User {user_id} sent a message without text.")
        await update.message.reply_text("Please send a text description of your food!")
        return

    text_description = update.message.text.strip()
    
    # Check if user has pending clarification
    if clarification_service.has_pending_clarification(user_id):
        await handle_clarification_text(update, context, text_description)
        return

    logger.info(f"User {user_id} sent text message: {text_description[:100]}...")
    await update.message.reply_text("📝 Analyzing your food description... This may take a moment.")

    try:
        # Analyze with AI
        logger.info(f"Sending text to AI analyzer for user {user_id}.")
        analysis = await ai_analyzer.analyze_food_text(text_description)
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
                
                # Ask for clarification
                clarification_msg = f"📝 **Your description:** \"{text_description}\"\n\n"
                clarification_msg += "⚠️ I have some uncertainties about your food:\n\n"
                
                if analysis.uncertainty.uncertain_items:
                    clarification_msg += "**Uncertain items:**\n"
                    for item in analysis.uncertainty.uncertain_items:
                        clarification_msg += f"• {item}\n"
                    clarification_msg += "\n"
                
                if analysis.uncertainty.uncertainty_reasons:
                    clarification_msg += "**Reasons for uncertainty:**\n"
                    for reason in analysis.uncertainty.uncertainty_reasons:
                        clarification_msg += f"• {reason}\n"
                    clarification_msg += "\n"
                
                clarification_msg += (
                    "Please send another text message, photo, or voice message with clarification "
                    "so I can provide accurate nutrition information!"
                )
                
                await update.message.reply_text(clarification_msg, parse_mode='Markdown')
                logger.info(f"Asked user {user_id} for clarification due to uncertainties in text.")
                return
            
            # No uncertainty - proceed with storage
            await store_and_respond_text_analysis(update, analysis, text_description, user_id)
            
        else:
            logger.warning(f"AI analysis failed or returned no result for user {user_id}.")
            await update.message.reply_text("❌ Could not analyze the food description. Please try describing your food in more detail.")
    except Exception as e:
        logger.exception(f"Error handling text message for user {user_id}: {e}")
        await update.message.reply_text("❌ An error occurred while analyzing your food description. Please try again.")


async def handle_clarification_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text_description: str):
    """Handle clarification text from user"""
    user_id = update.effective_user.id
    
    try:
        pending = clarification_service.get_pending_clarification(user_id)
        if not pending:
            await update.message.reply_text("❌ No pending clarification found.")
            return
        
        logger.info(f"Processing clarification text for user {user_id}.")
        await update.message.reply_text("📝 Processing your clarification... This may take a moment.")
        
        # For text clarification, we can use the analyze_food_text method with clarification
        original_text = pending.original_data.get('text_description', '')
        analysis = await ai_analyzer.analyze_food_text(
            text_description=original_text,
            clarification_text=text_description
        )
        
        if analysis:
            # Clear pending clarification
            clarification_service.clear_pending_clarification(user_id)
            
            # Store and respond with the original text description
            original_text = pending.original_data.get('text_description', 'Text clarification provided')
            await store_and_respond_text_analysis(update, analysis, original_text, user_id, is_clarification=True)
        else:
            await update.message.reply_text("❌ Could not process clarification. Please try again.")
            
    except Exception as e:
        logger.exception(f"Error handling clarification text for user {user_id}: {e}")
        await update.message.reply_text("❌ An error occurred while processing clarification. Please try again.")


async def store_and_respond_text_analysis(update: Update, analysis, text_description: str, user_id: int, is_clarification: bool = False):
    """Helper function to store text analysis in database and send response to user"""
    try:
        # Store in SQLite
        from services.database_service import DatabaseService
        db_path = os.getenv('DATABASE_PATH', '/app/data/food_journal.db')
        database_service = DatabaseService(db_path)
        username = update.effective_user.username or ""
        first_name = update.effective_user.first_name or ""
        logger.info(f"Storing analysis in database for user {user_id}.")
        stored = database_service.store_food_analysis(user_id, username, first_name, analysis)

        if stored:
            # Format response message with original text
            if is_clarification:
                response = f"📝 **Original Description:** \"{text_description}\"\n\n"
                response += "✅ **Clarification processed! Final Food Analysis:**\n\n"
            else:
                response = f"📝 **Your Description:** \"{text_description}\"\n\n"
                response += "🍽️ **Food Analysis Complete!**\n\n"
                
            for item in analysis.food_items:
                response += f"📍 **{item.name}** ({item.quantity})\n"
                response += f"   • Calories: {getattr(item.nutrition, 'calories', 0.0):.0f} kcal\n"
                response += f"   • Protein: {getattr(item.nutrition, 'protein', 0.0):.1f}g\n"
                response += f"   • Carbs: {getattr(item.nutrition, 'carbs', 0.0):.1f}g\n"
                response += f"   • Fat: {getattr(item.nutrition, 'fat', 0.0):.1f}g\n\n"
            response += f"**📊 Total Nutrition:**\n"
            response += f"🔥 Calories: {analysis.total_nutrition.calories:.0f} kcal\n"
            response += f"💪 Protein: {analysis.total_nutrition.protein:.1f}g\n"
            response += f"🌾 Carbs: {analysis.total_nutrition.carbs:.1f}g\n"
            response += f"🥑 Fat: {analysis.total_nutrition.fat:.1f}g"
            
            # Add compliment for healthy food choices
            compliment = compliment_service.generate_response_with_compliment(analysis.food_items)
            if compliment:
                response += f"\n\n{compliment}"
            
            await update.message.reply_text(response, parse_mode='Markdown')
            logger.info(f"Analysis sent to user {user_id}.")
        else:
            logger.error(f"Failed to store analysis in database for user {user_id}.")
            await update.message.reply_text("❌ Failed to save food entry. Please try again.")
    except Exception as e:
        logger.exception(f"Error storing and responding text analysis for user {user_id}: {e}")
        await update.message.reply_text("❌ An error occurred while saving your food entry. Please try again.")


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle audio messages and voice notes for food analysis"""
    user_id = update.effective_user.id
    
    if not is_user_allowed(user_id):
        logger.warning(f"Unauthorized access attempt by user {user_id}.")
        await update.message.reply_text("🚫 You are not authorized to use this bot.")
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
        await update.message.reply_text("Please send a voice message or audio file describing your food!")
        return
    
    # Check if user has pending clarification
    if clarification_service.has_pending_clarification(user_id):
        await handle_clarification_audio(update, context, audio_file, filename)
        return
    
    logger.info(f"User {user_id} sent audio. Starting analysis.")
    await update.message.reply_text("🎤 Analyzing your audio... This may take a moment.")
    
    try:
        # Download audio file
        logger.info(f"Downloading audio file for user {user_id}.")
        audio_telegram_file = await context.bot.get_file(audio_file.file_id)
        audio_bytes = await audio_telegram_file.download_as_bytearray()
        logger.info(f"Audio file downloaded for user {user_id}, size: {len(audio_bytes)} bytes.")

        # Analyze with AI (transcription + food analysis)
        logger.info(f"Sending audio to AI analyzer for user {user_id}.")
        result = await ai_analyzer.analyze_food_audio(bytes(audio_bytes), filename)
        
        if result:
            analysis, transcribed_text = result
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
                
                # Ask for clarification
                clarification_msg = f"🎤 **Transcription:** \"{transcribed_text}\"\n\n"
                clarification_msg += "⚠️ I have some uncertainties about your food:\n\n"
                
                if analysis.uncertainty.uncertain_items:
                    clarification_msg += "**Uncertain items:**\n"
                    for item in analysis.uncertainty.uncertain_items:
                        clarification_msg += f"• {item}\n"
                    clarification_msg += "\n"
                
                if analysis.uncertainty.uncertainty_reasons:
                    clarification_msg += "**Reasons for uncertainty:**\n"
                    for reason in analysis.uncertainty.uncertainty_reasons:
                        clarification_msg += f"• {reason}\n"
                    clarification_msg += "\n"
                
                clarification_msg += (
                    "Please send another photo, voice message, or text description with clarification "
                    "so I can provide accurate nutrition information!"
                )
                
                await update.message.reply_text(clarification_msg, parse_mode='Markdown')
                logger.info(f"Asked user {user_id} for clarification due to uncertainties in audio.")
                return

            # No uncertainty - proceed with storage
            await store_and_respond_audio_analysis(update, analysis, transcribed_text, user_id)

        else:
            logger.warning(f"AI analysis failed or returned no result for user {user_id}.")
            await update.message.reply_text("❌ Could not analyze the audio. Please try speaking more clearly or describing your food in more detail.")
            
    except Exception as e:
        logger.exception(f"Error handling audio for user {user_id}: {e}")
        await update.message.reply_text("❌ An error occurred while processing your audio. Please try again.")


async def handle_clarification_audio(update: Update, context: ContextTypes.DEFAULT_TYPE, audio_file, filename: str):
    """Handle clarification audio from user"""
    user_id = update.effective_user.id
    
    try:
        pending = clarification_service.get_pending_clarification(user_id)
        if not pending:
            await update.message.reply_text("❌ No pending clarification found.")
            return
        
        logger.info(f"Processing clarification audio for user {user_id}.")
        await update.message.reply_text("🎤 Processing your clarification... This may take a moment.")
        
        # Get clarification audio
        audio_telegram_file = await context.bot.get_file(audio_file.file_id)
        audio_bytes = await audio_telegram_file.download_as_bytearray()
        
        # Combine original analysis with clarification
        analysis = await ai_analyzer.analyze_with_clarification(
            original_analysis_text=pending.analysis_text,
            clarification_data=bytes(audio_bytes),
            clarification_type='audio',
            filename=filename
        )
        
        if analysis:
            # Clear pending clarification
            clarification_service.clear_pending_clarification(user_id)
            
            # For audio clarification, we need to get the transcription too
            if pending.media_type == 'audio':
                # Use original transcription if available
                transcribed_text = pending.original_data.get('transcribed_text', 'Audio clarification provided')
                await store_and_respond_audio_analysis(update, analysis, transcribed_text, user_id, is_clarification=True)
            else:
                await store_and_respond_analysis(update, analysis, user_id, is_clarification=True)
        else:
            await update.message.reply_text("❌ Could not process clarification. Please try again.")
            
    except Exception as e:
        logger.exception(f"Error handling clarification audio for user {user_id}: {e}")
        await update.message.reply_text("❌ An error occurred while processing clarification. Please try again.")


async def store_and_respond_audio_analysis(update: Update, analysis, transcribed_text: str, user_id: int, is_clarification: bool = False):
    """Helper function to store audio analysis in database and send response to user"""
    try:
        # Store in SQLite
        from services.database_service import DatabaseService
        db_path = os.getenv('DATABASE_PATH', '/app/data/food_journal.db')
        database_service = DatabaseService(db_path)
        username = update.effective_user.username or ""
        first_name = update.effective_user.first_name or ""
        logger.info(f"Storing analysis in database for user {user_id}.")
        stored = database_service.store_food_analysis(user_id, username, first_name, analysis)

        if stored:
            # Format response message with transcription
            if is_clarification:
                response = f"🎤 **Original Transcription:** \"{transcribed_text}\"\n\n"
                response += "✅ **Clarification processed! Final Food Analysis:**\n\n"
            else:
                response = f"🎤 **Transcription:** \"{transcribed_text}\"\n\n"
                response += "🍽️ **Food Analysis Complete!**\n\n"
                
            for item in analysis.food_items:
                response += f"📍 **{item.name}** ({item.quantity})\n"
                response += f"   • Calories: {getattr(item.nutrition, 'calories', 0.0):.0f} kcal\n"
                response += f"   • Protein: {getattr(item.nutrition, 'protein', 0.0):.1f}g\n"
                response += f"   • Carbs: {getattr(item.nutrition, 'carbs', 0.0):.1f}g\n"
                response += f"   • Fat: {getattr(item.nutrition, 'fat', 0.0):.1f}g\n\n"
            response += f"**📊 Total Nutrition:**\n"
            response += f"🔥 Calories: {analysis.total_nutrition.calories:.0f} kcal\n"
            response += f"💪 Protein: {analysis.total_nutrition.protein:.1f}g\n"
            response += f"🌾 Carbs: {analysis.total_nutrition.carbs:.1f}g\n"
            response += f"🥑 Fat: {analysis.total_nutrition.fat:.1f}g"
            
            # Add compliment for healthy food choices
            compliment = compliment_service.generate_response_with_compliment(analysis.food_items)
            if compliment:
                response += f"\n\n{compliment}"
            
            await update.message.reply_text(response, parse_mode='Markdown')
            logger.info(f"Analysis sent to user {user_id}.")
        else:
            logger.error(f"Failed to store analysis in database for user {user_id}.")
            await update.message.reply_text("❌ Failed to save food entry. Please try again.")
    except Exception as e:
        logger.exception(f"Error storing and responding audio analysis for user {user_id}: {e}")
        await update.message.reply_text("❌ An error occurred while saving your food entry. Please try again.")


async def cancel_clarification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel pending clarification request"""
    user_id = update.effective_user.id
    
    if not is_user_allowed(user_id):
        logger.warning(f"Unauthorized access attempt by user {user_id}.")
        await update.message.reply_text("🚫 You are not authorized to use this bot.")
        return
    
    if clarification_service.has_pending_clarification(user_id):
        clarification_service.clear_pending_clarification(user_id)
        await update.message.reply_text("✅ Clarification request cancelled. You can now send new food photos, voice messages, or text descriptions.")
        logger.info(f"User {user_id} cancelled pending clarification.")
    else:
        await update.message.reply_text("ℹ️ No pending clarification to cancel.")


async def check_clarification_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if user has pending clarification"""
    user_id = update.effective_user.id
    
    if not is_user_allowed(user_id):
        logger.warning(f"Unauthorized access attempt by user {user_id}.")
        await update.message.reply_text("🚫 You are not authorized to use this bot.")
        return
    
    if clarification_service.has_pending_clarification(user_id):
        pending = clarification_service.get_pending_clarification(user_id)
        time_diff = datetime.now() - pending.timestamp
        
        status_msg = "⏳ **You have a pending clarification request:**\n\n"
        status_msg += f"**Time:** {time_diff.seconds // 60} minutes ago\n"
        status_msg += f"**Media Type:** {pending.media_type.title()}\n"
        status_msg += f"**Uncertain Items:** {', '.join(pending.uncertain_items) if pending.uncertain_items else 'None specified'}\n\n"
        status_msg += "Please send clarification (photo, voice message, or text description) or use /cancel to start over."
        
        await update.message.reply_text(status_msg, parse_mode='Markdown')
    else:
        await update.message.reply_text("ℹ️ No pending clarification requests. Send a food photo, voice message, or text description to get started!")