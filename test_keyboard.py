#!/usr/bin/env python3
"""
Test script for keyboard functionality in the Telegram bot
"""

import sys
import os

# Add the bot directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))

from telegram import ReplyKeyboardMarkup, KeyboardButton

def create_commands_keyboard(language='en'):
    """Create a keyboard with all available bot commands"""
    if language == 'ru':
        keyboard = [
            [KeyboardButton('📊 /daily - Дневная сводка'), KeyboardButton('📈 /weekly - Недельная сводка')],
            [KeyboardButton('🌍 /settimezone - Часовой пояс'), KeyboardButton('🗣️ /setlanguage - Язык')],
            [KeyboardButton('📋 /status - Статус'), KeyboardButton('❌ /cancel - Отмена')],
            [KeyboardButton('🎯 /keyboard - Клавиатура'), KeyboardButton('❓ /help - Помощь')],
            [KeyboardButton('🔄 /start - Начать')]
        ]
    else:
        keyboard = [
            [KeyboardButton('📊 /daily - Daily Summary'), KeyboardButton('📈 /weekly - Weekly Summary')],
            [KeyboardButton('🌍 /settimezone - Set Timezone'), KeyboardButton('🗣️ /setlanguage - Set Language')],
            [KeyboardButton('📋 /status - Check Status'), KeyboardButton('❌ /cancel - Cancel')],
            [KeyboardButton('🎯 /keyboard - Show Keyboard'), KeyboardButton('❓ /help - Help')],
            [KeyboardButton('🔄 /start - Start')]
        ]
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def test_keyboard():
    """Test keyboard creation"""
    print("Testing English keyboard:")
    en_keyboard = create_commands_keyboard('en')
    print(f"English keyboard created successfully with {len(en_keyboard.keyboard)} rows")
    
    print("\nTesting Russian keyboard:")
    ru_keyboard = create_commands_keyboard('ru')
    print(f"Russian keyboard created successfully with {len(ru_keyboard.keyboard)} rows")
    
    print("\nEnglish keyboard layout:")
    for i, row in enumerate(en_keyboard.keyboard):
        print(f"Row {i+1}: {[btn.text for btn in row]}")
    
    print("\nRussian keyboard layout:")
    for i, row in enumerate(ru_keyboard.keyboard):
        print(f"Row {i+1}: {[btn.text for btn in row]}")
    
    print("\nKeyboard properties:")
    print(f"resize_keyboard: {en_keyboard.resize_keyboard}")
    print(f"one_time_keyboard: {en_keyboard.one_time_keyboard}")

if __name__ == "__main__":
    test_keyboard()
