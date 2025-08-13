#!/usr/bin/env python3
"""
Test the simplified keyboard button mapping
"""

def test_simplified_keyboard_mapping():
    """Test the new button to command mapping"""
    
    button_to_command = {
        # English buttons
        '📊 Daily Summary': 'daily',
        '📈 Weekly Summary': 'weekly', 
        '❓ Help': 'help',
        '❌ Cancel': 'cancel',
        # Russian buttons
        '📊 Дневная сводка': 'daily',
        '📈 Недельная сводка': 'weekly',
        '❓ Помощь': 'help',
        '❌ Отмена': 'cancel'
    }
    
    test_cases = [
        '📊 Daily Summary',
        '📈 Weekly Summary', 
        '❓ Help',
        '❌ Cancel',
        '📊 Дневная сводка',
        '📈 Недельная сводка',
        '❓ Помощь',
        '❌ Отмена',
        'Some regular food text',  # Should not match
        'Pizza with cheese'        # Should not match
    ]
    
    for test_text in test_cases:
        print(f"Input: '{test_text}'")
        
        if test_text in button_to_command:
            command = button_to_command[test_text]
            print(f"  ✅ Mapped to command: {command}")
        else:
            print(f"  ❌ Not a keyboard button (will be processed as food text)")
        print()

if __name__ == "__main__":
    test_simplified_keyboard_mapping()
