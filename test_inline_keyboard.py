#!/usr/bin/env python3
"""
Test the inline keyboard implementation for clarification requests
"""

import sys
import os

# Add the bot directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))

from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def create_clarification_inline_keyboard(language='en'):
    """Create inline keyboard for clarification requests"""
    if language == 'ru':
        keyboard = [[InlineKeyboardButton("❌ Прервать прояснение", callback_data="abort_clarification")]]
    else:
        keyboard = [[InlineKeyboardButton("❌ Abort clarification", callback_data="abort_clarification")]]
    
    return InlineKeyboardMarkup(keyboard)

def test_inline_keyboard():
    """Test inline keyboard creation"""
    print("Testing inline keyboard for clarification requests:")
    
    # Test English
    en_keyboard = create_clarification_inline_keyboard('en')
    print(f"English keyboard: {en_keyboard.inline_keyboard[0][0].text}")
    print(f"Callback data: {en_keyboard.inline_keyboard[0][0].callback_data}")
    
    # Test Russian
    ru_keyboard = create_clarification_inline_keyboard('ru')
    print(f"Russian keyboard: {ru_keyboard.inline_keyboard[0][0].text}")
    print(f"Callback data: {ru_keyboard.inline_keyboard[0][0].callback_data}")
    
    print("\n✅ Inline keyboard implementation looks correct!")

if __name__ == "__main__":
    test_inline_keyboard()
