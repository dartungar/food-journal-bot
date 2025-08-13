"""
Test script to verify the compliment feature works correctly in the food journal bot.
"""
import os
import sys

# Set up environment
os.environ['OPENAI_API_KEY'] = 'test-key'
os.environ['ALLOWED_USER_IDS'] = '123'
os.environ['DATABASE_PATH'] = 'test.db'

# Test the complete flow
from bot.services.compliment_service import compliment_service
from bot.models.nutrition_models import FoodItem, NutritionInfo

print("🧪 Testing Compliment Service Integration")
print("=" * 50)

# Test Case 1: Healthy foods should get compliments
print("\n✅ Test 1: Healthy foods (should get compliments)")
nutrition = NutritionInfo(calories=80, protein=3, carbs=15, fat=1)

healthy_foods = [
    FoodItem(name='Apple', quantity='1 medium', nutrition=nutrition),
    FoodItem(name='Broccoli', quantity='1 cup steamed', nutrition=nutrition),
    FoodItem(name='Quinoa', quantity='0.5 cup cooked', nutrition=nutrition),
    FoodItem(name='Salmon', quantity='4 oz grilled', nutrition=nutrition),
    FoodItem(name='Almonds', quantity='1 oz', nutrition=nutrition)
]

for food in healthy_foods:
    compliment = compliment_service.generate_response_with_compliment([food])
    status = "✅ Got compliment" if compliment else "❌ No compliment"
    print(f"  {food.name}: {status}")
    if compliment:
        print(f"    → {compliment}")

# Test Case 2: Mix of healthy and junk foods
print("\n🥗 Test 2: Mixed foods (should compliment only healthy ones)")
mixed_foods = [
    FoodItem(name='Spinach salad', quantity='1 bowl', nutrition=nutrition),
    FoodItem(name='Pizza slice', quantity='1 slice', nutrition=nutrition),
    FoodItem(name='Grilled chicken breast', quantity='1 piece', nutrition=nutrition)
]

compliment = compliment_service.generate_response_with_compliment(mixed_foods)
if compliment:
    print(f"  ✅ Got compliment for mixed foods: {compliment}")
else:
    print("  ❌ No compliment for mixed foods")

# Test Case 3: Only junk foods should get no compliments
print("\n🍕 Test 3: Junk foods only (should get no compliments)")
junk_foods = [
    FoodItem(name='Pizza', quantity='2 slices', nutrition=nutrition),
    FoodItem(name='Soda', quantity='1 can', nutrition=nutrition),
    FoodItem(name='Candy bar', quantity='1 bar', nutrition=nutrition)
]

compliment = compliment_service.generate_response_with_compliment(junk_foods)
if compliment:
    print(f"  ❌ Unexpectedly got compliment: {compliment}")
else:
    print("  ✅ Correctly no compliment for junk foods")

# Test Case 4: Edge cases
print("\n🔍 Test 4: Edge cases")
edge_cases = [
    FoodItem(name='Sweet potato fries', quantity='1 serving', nutrition=nutrition),  # Should get compliment (sweet potato)
    FoodItem(name='Dark chocolate', quantity='1 oz', nutrition=nutrition),  # Should not get compliment
    FoodItem(name='Greek yogurt with berries', quantity='1 cup', nutrition=nutrition)  # Should get compliment
]

for food in edge_cases:
    compliment = compliment_service.generate_response_with_compliment([food])
    status = "✅ Got compliment" if compliment else "❌ No compliment"
    print(f"  {food.name}: {status}")
    if compliment:
        print(f"    → {compliment}")

print("\n🎉 Compliment service testing complete!")
print("The bot will now compliment healthy food choices without disparaging junk food.")
