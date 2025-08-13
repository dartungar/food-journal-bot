#!/usr/bin/env python3
"""
Test the keyboard button parsing logic
"""

def test_keyboard_button_parsing():
    """Test parsing keyboard button text"""
    
    test_cases = [
        "🎯 /keyboard - Show Keyboard",
        "📊 /daily - Daily Summary", 
        "📈 /weekly - Weekly Summary",
        "🌍 /settimezone - Set Timezone",
        "🗣️ /setlanguage - Set Language",
        "📋 /status - Check Status",
        "❌ /cancel - Cancel",
        "❓ /help - Help",
        "🔄 /start - Start"
    ]
    
    for test_text in test_cases:
        print(f"Input: {test_text}")
        
        # Extract command like the bot does
        command_part = test_text.split(' - ')[0]  # Get the part before the description
        command = command_part.split(' ')[1] if ' ' in command_part else command_part  # Extract /command
        
        print(f"  -> Command part: {command_part}")
        print(f"  -> Extracted command: {command}")
        print(f"  -> Starts with emoji command: {test_text.startswith(('📊 /daily', '📈 /weekly', '🌍 /settimezone', '🗣️ /setlanguage', '📋 /status', '❌ /cancel', '🎯 /keyboard', '❓ /help', '🔄 /start'))}")
        print()

if __name__ == "__main__":
    test_keyboard_button_parsing()
