"""
Language detection and localization service for the food journal bot.
Supports English and Russian.
"""
import re
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class LocalizedMessages:
    """Container for localized message templates"""
    
    # Analysis messages
    food_analysis_complete: str
    clarification_processed: str
    analyzing_food: str
    analyzing_audio: str
    analyzing_text: str
    processing_clarification: str
    
    # Nutrition labels
    calories: str
    protein: str
    carbs: str
    fat: str
    total_nutrition: str
    
    # Error messages
    unauthorized: str
    analysis_failed: str
    error_occurred: str
    failed_to_save: str
    
    # Clarification messages
    uncertainty_detected: str
    uncertain_items: str
    uncertainty_reasons: str
    clarification_request: str
    clarification_cancelled: str
    no_pending_clarification: str
    
    # Commands and help
    welcome_message: str
    help_message: str
    language_help_message: str
    language_set_message: str
    
    # Status messages
    transcription: str
    original_description: str
    pending_clarification_status: str


class LanguageService:
    """Service for language detection and localization"""
    
    # Russian alphabet pattern for detection
    CYRILLIC_PATTERN = re.compile(r'[а-яё]', re.IGNORECASE)
    
    # Localized messages
    MESSAGES = {
        'en': LocalizedMessages(
            # Analysis messages
            food_analysis_complete="🍽️ **Food Analysis Complete!**\n\n",
            clarification_processed="✅ **Clarification processed! Final Food Analysis:**\n\n",
            analyzing_food="🔍 Analyzing your food... This may take a moment.",
            analyzing_audio="🎤 Analyzing your audio... This may take a moment.",
            analyzing_text="📝 Analyzing your food description... This may take a moment.",
            processing_clarification="🔍 Processing your clarification... This may take a moment.",
            
            # Nutrition labels
            calories="Calories",
            protein="Protein", 
            carbs="Carbs",
            fat="Fat",
            total_nutrition="**📊 Total Nutrition:**\n",
            
            # Error messages
            unauthorized="🚫 You are not authorized to use this bot.",
            analysis_failed="❌ Could not analyze the food. Please try with a clearer photo or more detailed description.",
            error_occurred="❌ An error occurred while analyzing your food. Please try again.",
            failed_to_save="❌ Failed to save food entry. Please try again.",
            
            # Clarification messages
            uncertainty_detected="⚠️ I have some uncertainties about your food:\n\n",
            uncertain_items="**Uncertain items:**\n",
            uncertainty_reasons="**Reasons for uncertainty:**\n",
            clarification_request="Please send another photo, voice message, or text description with clarification so I can provide accurate nutrition information!",
            clarification_cancelled="✅ Clarification request cancelled. You can now send new food photos, voice messages, or text descriptions.",
            no_pending_clarification="ℹ️ No pending clarification to cancel.",
            
            # Commands and help
            welcome_message="""🍽️ **Welcome to AI Food Journal Bot!**

📸 **Send me a photo of your food** and I'll analyze it for you!
🎤 **Send me a voice message** describing what you ate!
📝 **Send me a text message** describing your meal!

**Available Commands:**
/daily - Get AI-generated daily nutrition summary
/weekly - Get AI-powered weekly analysis with insights
/settimezone <tz> - Set your timezone (e.g., /settimezone Europe/Berlin)
/setlanguage <lang> - Set your language preference (en/ru)
/status - Check if you have pending clarification requests
/cancel - Cancel pending clarification and start over
/help - Show this help message

**🤖 AI-Powered Features:**
🌙 **Smart Daily Summaries** - Delivered at 9 PM with personalized insights
📊 **Weekly AI Analysis** - Comprehensive reports every Sunday at 8 PM
💡 **Personalized Recommendations** - Based on your actual eating patterns
🧠 **Smart Clarification** - I'll ask for clarification when uncertain about your food

Just send a food photo, voice message, or text description to get started! 🚀""",
            
            help_message="""🤖 **AI Food Journal Bot Help**

**How to use:**
1. 📸 Send a photo of your food OR 🎤 Send a voice message OR 📝 Send a text message describing it
2. 🤖 I'll analyze it with AI and log the nutrition info
3. 🧠 If I'm uncertain, I'll ask for clarification before saving
4. 📊 Get personalized AI summaries automatically

**Commands:**
/daily - Get today's AI nutrition analysis
/weekly - Get this week's AI-powered insights
/settimezone <tz> - Set your timezone (e.g., /settimezone Europe/Berlin)
/setlanguage <lang> - Set your language preference (en/ru)
/status - Check if you have pending clarification requests
/cancel - Cancel pending clarification and start over
/start - Welcome message
/help - This help message

**🧠 Smart Clarification Process:**
1. Send your food photo/audio/text
2. If I'm uncertain, I'll ask for clarification
3. Send another photo/voice/text message to clarify
4. I'll combine both to create accurate nutrition data

**Tips:**
• Take clear, well-lit photos of your entire meal
• Speak clearly when recording voice messages
• Be specific about quantities and ingredients in text descriptions""",

            language_help_message="""🌍 **Language Settings**

To change your language preference, use:
/setlanguage en (for English)
/setlanguage ru (for Russian)

Example: `/setlanguage ru`

The bot will automatically detect language from your messages, but you can set a preference with this command.""",

            language_set_message="✅ **Language preference updated!** I'll now respond in English by default.",
            
            # Status messages
            transcription="🎤 **Transcription:**",
            original_description="📝 **Original Description:**",
            pending_clarification_status="⏳ **You have a pending clarification request:**\n\n",
        ),
        
        'ru': LocalizedMessages(
            # Analysis messages
            food_analysis_complete="🍽️ **Анализ пищи завершён!**\n\n",
            clarification_processed="✅ **Уточнение обработано! Финальный анализ пищи:**\n\n",
            analyzing_food="🔍 Анализирую вашу еду... Это может занять несколько минут.",
            analyzing_audio="🎤 Анализирую ваше аудио... Это может занять несколько минут.",
            analyzing_text="📝 Анализирую описание вашей еды... Это может занять несколько минут.",
            processing_clarification="🔍 Обрабатываю ваше уточнение... Это может занять несколько минут.",
            
            # Nutrition labels
            calories="Калории",
            protein="Белки",
            carbs="Углеводы", 
            fat="Жиры",
            total_nutrition="**📊 Общая питательность:**\n",
            
            # Error messages
            unauthorized="🚫 У вас нет доступа к этому боту.",
            analysis_failed="❌ Не удалось проанализировать еду. Пожалуйста, попробуйте с более чётким фото или подробным описанием.",
            error_occurred="❌ Произошла ошибка при анализе вашей еды. Пожалуйста, попробуйте снова.",
            failed_to_save="❌ Не удалось сохранить запись о еде. Пожалуйста, попробуйте снова.",
            
            # Clarification messages
            uncertainty_detected="⚠️ У меня есть некоторые неопределённости относительно вашей еды:\n\n",
            uncertain_items="**Неопределённые продукты:**\n",
            uncertainty_reasons="**Причины неопределённости:**\n",
            clarification_request="Пожалуйста, отправьте другое фото, голосовое сообщение или текстовое описание с уточнениями, чтобы я мог предоставить точную информацию о питательности!",
            clarification_cancelled="✅ Запрос на уточнение отменён. Теперь вы можете отправлять новые фото еды, голосовые сообщения или текстовые описания.",
            no_pending_clarification="ℹ️ Нет ожидающих уточнений для отмены.",
            
            # Commands and help
            welcome_message="""🍽️ **Добро пожаловать в ИИ Бот Дневника Питания!**

📸 **Отправьте мне фото вашей еды**, и я проанализирую её для вас!
🎤 **Отправьте мне голосовое сообщение**, описывающее что вы ели!
📝 **Отправьте мне текстовое сообщение**, описывающее вашу еду!

**Доступные команды:**
/daily - Получить ИИ-анализ питания за день
/weekly - Получить ИИ-анализ питания за неделю с инсайтами
/settimezone <tz> - Установить часовой пояс (например, /settimezone Europe/Moscow)
/setlanguage <lang> - Установить языковые предпочтения (en/ru)
/status - Проверить, есть ли ожидающие запросы на уточнение
/cancel - Отменить ожидающее уточнение и начать заново
/help - Показать это сообщение помощи

**🤖 ИИ-функции:**
🌙 **Умные ежедневные сводки** - Доставляются в 21:00 с персонализированными инсайтами
📊 **Еженедельный ИИ-анализ** - Комплексные отчёты каждое воскресенье в 20:00
💡 **Персонализированные рекомендации** - На основе ваших реальных привычек питания
🧠 **Умные уточнения** - Я попрошу уточнения, когда не уверен в вашей еде

Просто отправьте фото еды, голосовое сообщение или текстовое описание, чтобы начать! 🚀""",
            
            help_message="""🤖 **Помощь по ИИ Боту Дневника Питания**

**Как использовать:**
1. 📸 Отправьте фото вашей еды ИЛИ 🎤 голосовое сообщение ИЛИ 📝 текстовое описание
2. 🤖 Я проанализирую это с помощью ИИ и запишу информацию о питательности
3. 🧠 Если я не уверен, я попрошу уточнения перед сохранением
4. 📊 Получите персонализированные ИИ-сводки автоматически

**Команды:**
/daily - Получить ИИ-анализ питания на сегодня
/weekly - Получить ИИ-инсайты за эту неделю
/settimezone <tz> - Установить часовой пояс (например, /settimezone Europe/Moscow)
/setlanguage <lang> - Установить языковые предпочтения (en/ru)
/status - Проверить, есть ли ожидающие запросы на уточнение
/cancel - Отменить ожидающее уточнение и начать заново
/start - Приветственное сообщение
/help - Это сообщение помощи

**🧠 Процесс умного уточнения:**
1. Отправьте фото/аудио/текст вашей еды
2. Если я не уверен, я попрошу уточнения
3. Отправьте другое фото/голосовое/текстовое сообщение для уточнения
4. Я объединю оба, чтобы создать точные данные о питательности

**Советы:**
• Делайте чёткие, хорошо освещённые фото всей вашей еды
• Говорите чётко при записи голосовых сообщений
• Будьте конкретны в количествах и ингредиентах в текстовых описаниях""",

            language_help_message="""🌍 **Настройки языка**

Чтобы изменить языковые предпочтения, используйте:
/setlanguage en (для английского)
/setlanguage ru (для русского)

Пример: `/setlanguage ru`

Бот автоматически определяет язык из ваших сообщений, но вы можете установить предпочтение этой командой.""",

            language_set_message="✅ **Языковые предпочтения обновлены!** Теперь я буду отвечать на русском языке по умолчанию.",
            
            # Status messages
            transcription="🎤 **Расшифровка:**",
            original_description="📝 **Исходное описание:**",
            pending_clarification_status="⏳ **У вас есть ожидающий запрос на уточнение:**\n\n",
        )
    }
    
    def detect_language(self, text: str) -> str:
        """
        Detect language from text input.
        Returns 'ru' for Russian, 'en' for English (default).
        """
        if not text or not text.strip():
            return 'en'  # Default to English
        
        # Count Cyrillic characters
        cyrillic_chars = len(self.CYRILLIC_PATTERN.findall(text))
        total_letters = len(re.findall(r'[a-zA-Zа-яёА-ЯЁ]', text))
        
        if total_letters == 0:
            return 'en'  # Default to English if no letters
        
        # If more than 30% of letters are Cyrillic, consider it Russian
        cyrillic_ratio = cyrillic_chars / total_letters
        return 'ru' if cyrillic_ratio > 0.3 else 'en'
    
    def get_messages(self, language: str) -> LocalizedMessages:
        """Get localized messages for the specified language"""
        return self.MESSAGES.get(language, self.MESSAGES['en'])
    
    def format_nutrition_response(self, language: str, analysis, description: str = None, 
                                is_clarification: bool = False, is_audio: bool = False, 
                                is_text: bool = False) -> str:
        """Format the nutrition response in the specified language"""
        messages = self.get_messages(language)
        
        # Build response message
        if is_clarification:
            if description:
                if is_audio:
                    response = f"{messages.transcription} \"{description}\"\n\n"
                else:
                    response = f"{messages.original_description} \"{description}\"\n\n"
            else:
                response = ""
            response += messages.clarification_processed
        else:
            if description:
                if is_audio:
                    response = f"{messages.transcription} \"{description}\"\n\n"
                elif is_text:
                    response = f"{messages.original_description} \"{description}\"\n\n"
                else:
                    response = ""
            else:
                response = ""
            response += messages.food_analysis_complete
        
        # Add food items
        for item in analysis.food_items:
            response += f"📍 **{item.name}** ({item.quantity})\n"
            response += f"   • {messages.calories}: {getattr(item.nutrition, 'calories', 0.0):.0f} kcal\n"
            response += f"   • {messages.protein}: {getattr(item.nutrition, 'protein', 0.0):.1f}g\n"
            response += f"   • {messages.carbs}: {getattr(item.nutrition, 'carbs', 0.0):.1f}g\n"
            response += f"   • {messages.fat}: {getattr(item.nutrition, 'fat', 0.0):.1f}g\n\n"
        
        # Add total nutrition
        response += messages.total_nutrition
        response += f"🔥 {messages.calories}: {analysis.total_nutrition.calories:.0f} kcal\n"
        response += f"💪 {messages.protein}: {analysis.total_nutrition.protein:.1f}g\n"
        response += f"🌾 {messages.carbs}: {analysis.total_nutrition.carbs:.1f}g\n"
        response += f"🥑 {messages.fat}: {analysis.total_nutrition.fat:.1f}g"
        
        return response
    
    def format_clarification_request(self, language: str, analysis, description: str = None,
                                   is_audio: bool = False, is_text: bool = False) -> str:
        """Format clarification request in the specified language"""
        messages = self.get_messages(language)
        
        clarification_msg = ""
        
        # Add original description if available
        if description:
            if is_audio:
                clarification_msg += f"{messages.transcription} \"{description}\"\n\n"
            elif is_text:
                clarification_msg += f"{messages.original_description} \"{description}\"\n\n"
        
        clarification_msg += messages.uncertainty_detected
        
        if analysis.uncertainty.uncertain_items:
            clarification_msg += messages.uncertain_items
            for item in analysis.uncertainty.uncertain_items:
                clarification_msg += f"• {item}\n"
            clarification_msg += "\n"
        
        if analysis.uncertainty.uncertainty_reasons:
            clarification_msg += messages.uncertainty_reasons
            for reason in analysis.uncertainty.uncertainty_reasons:
                clarification_msg += f"• {reason}\n"
            clarification_msg += "\n"
        
        clarification_msg += messages.clarification_request
        
        return clarification_msg


# Global language service instance
language_service = LanguageService()
