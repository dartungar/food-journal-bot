#!/usr/bin/env python3
"""
Test script for multi-language functionality
"""
import os
import sys
sys.path.append('./bot')

from services.language_service import language_service

def test_language_detection():
    """Test language detection functionality"""
    print("=== Language Detection Tests ===")
    
    test_cases = [
        ("I ate an apple and some bread", "en"),
        ("Я ел яблоко и хлеб", "ru"),
        ("apple яблоко bread", "ru"),  # Mixed with Cyrillic should detect as Russian
        ("Hello world", "en"),
        ("Привет мир", "ru"),
        ("", "en"),  # Empty should default to English
        ("123 !@#", "en"),  # No letters should default to English
    ]
    
    for text, expected in test_cases:
        detected = language_service.detect_language(text)
        status = "✅" if detected == expected else "❌"
        print(f'{status} "{text}" -> {detected} (expected: {expected})')

def test_localized_messages():
    """Test localized message retrieval"""
    print("\n=== Localized Messages Test ===")
    
    en_msgs = language_service.get_messages('en')
    ru_msgs = language_service.get_messages('ru')
    
    print(f"English analyzing food: {en_msgs.analyzing_food}")
    print(f"Russian analyzing food: {ru_msgs.analyzing_food}")
    print(f"English calories: {en_msgs.calories}")
    print(f"Russian calories: {ru_msgs.calories}")
    print(f"English unauthorized: {en_msgs.unauthorized}")
    print(f"Russian unauthorized: {ru_msgs.unauthorized}")

def test_compliment_service():
    """Test compliment service with languages"""
    print("\n=== Compliment Service Test ===")
    
    from services.compliment_service import compliment_service
    from models.nutrition_models import FoodItem, NutritionInfo
    
    # Create a test food item
    nutrition = NutritionInfo(calories=100, protein=5, carbs=20, fat=2)
    apple = FoodItem(name="apple", quantity="1 medium", nutrition=nutrition, confidence=0.9)
    
    # Test compliments in both languages
    en_compliment = compliment_service.generate_response_with_compliment([apple], language='en')
    ru_compliment = compliment_service.generate_response_with_compliment([apple], language='ru')
    
    print(f"English compliment: {en_compliment}")
    print(f"Russian compliment: {ru_compliment}")

if __name__ == "__main__":
    test_language_detection()
    test_localized_messages()
    test_compliment_service()
    print("\n✅ All tests completed!")
