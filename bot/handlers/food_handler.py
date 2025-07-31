import logging
from telegram import Update
from telegram.ext import ContextTypes
from services.ai_service import AIFoodAnalyzer
import os

ai_analyzer = AIFoodAnalyzer(os.getenv('OPENAI_API_KEY'))

logger = logging.getLogger(__name__)

async def handle_food_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle food photo upload and analysis"""
    user_id = update.effective_user.id
    
    if not update.message.photo:
        logger.warning(f"User {user_id} sent a message without a photo.")
        await update.message.reply_text("Please send a photo of your food!")
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
                await update.message.reply_text(response, parse_mode='Markdown')
                logger.info(f"Analysis sent to user {user_id}.")
            else:
                logger.error(f"Failed to store analysis in database for user {user_id}.")
                await update.message.reply_text("❌ Failed to save food entry. Please try again.")
        else:
            logger.warning(f"AI analysis failed or returned no result for user {user_id}.")
            await update.message.reply_text("❌ Could not analyze the food image. Please try with a clearer photo.")
    except Exception as e:
        logger.exception(f"Error handling food photo for user {user_id}: {e}")
        await update.message.reply_text("❌ An error occurred while analyzing your food. Please try again.")


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle audio messages and voice notes for food analysis"""
    user_id = update.effective_user.id
    
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
                
                await update.message.reply_text(response, parse_mode='Markdown')
                logger.info(f"Analysis sent to user {user_id}.")
            else:
                logger.error(f"Failed to store analysis in database for user {user_id}.")
                await update.message.reply_text("❌ Failed to save food entry. Please try again.")
        else:
            logger.warning(f"AI analysis failed or returned no result for user {user_id}.")
            await update.message.reply_text("❌ Could not analyze the audio. Please try speaking more clearly or describing your food in more detail.")
            
    except Exception as e:
        logger.exception(f"Error handling audio for user {user_id}: {e}")
        await update.message.reply_text("❌ An error occurred while processing your audio. Please try again.")