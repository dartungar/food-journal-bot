import base64
from openai import OpenAI
from typing import Optional, List
from models.nutrition_models import FoodAnalysisResponse
from datetime import datetime
from pydantic import BaseModel
import io

# Pydantic models for structured output
class NutritionData(BaseModel):
    calories: float
    protein: float
    carbs: float
    fat: float

class FoodItemData(BaseModel):
    name: str
    quantity: str
    nutrition: NutritionData

class NutritionParseResponse(BaseModel):
    food_items: List[FoodItemData]
    total_nutrition: NutritionData

class AIFoodAnalyzer:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    def encode_image(self, image_bytes: bytes) -> str:
        return base64.b64encode(image_bytes).decode('utf-8')
    
    async def analyze_food_image(self, image_bytes: bytes) -> Optional[FoodAnalysisResponse]:
        import re
        encoded_image = self.encode_image(image_bytes)
        system_prompt = (
            "You are a Nutritionist's assistant. "
            "You analyze pictures of food and provide detailed description for Nutritionist, "
            "so that he can analyze food and provide nutrition data."
        )
        try:
            import asyncio
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{encoded_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1024
            )
            if response.choices and response.choices[0].message and response.choices[0].message.content:
                text = response.choices[0].message.content
                print(f"AI response: {text}")
                # Use OpenAI to parse nutrition info into structured format
                return await self._parse_nutrition_response(text)
            else:
                print("No valid response from OpenAI.")
                return None
        except Exception as e:
            print(f"Error analyzing food image: {e}")
            return None

    async def analyze_food_audio(self, audio_bytes: bytes, filename: str = "audio.ogg") -> Optional[tuple[FoodAnalysisResponse, str]]:
        """Analyze food audio by transcribing and then analyzing the description"""
        try:
            import asyncio
            
            # Create BytesIO object for OpenAI API
            audio_bytes_io = io.BytesIO(audio_bytes)
            audio_bytes_io.name = filename
            
            print(f"Starting audio transcription for file: {filename}")
            
            # Step 1: Transcribe audio using Whisper
            transcription = await asyncio.to_thread(
                self.client.audio.transcriptions.create,
                model="gpt-4o-mini-transcribe",
                file=audio_bytes_io,
                language="en"  # You can make this configurable
            )
            
            transcribed_text = transcription.text
            print(f"Transcription completed: {transcribed_text[:100]}...")
            
            if not transcribed_text.strip():
                print("Empty transcription received.")
                return None
            
            # Step 2: Analyze the transcribed text for food and nutrition
            system_prompt = (
                "You are a Nutritionist's assistant. "
                "You analyze food descriptions and provide detailed nutritional information. "
                "Based on the food description, estimate portions and provide nutrition data including "
                "calories, protein, carbs, and fat for each food item mentioned."
            )
            
            print("Starting food analysis from transcription...")
            
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user", 
                        "content": f"Analyze this food description and provide nutritional information: {transcribed_text}"
                    }
                ],
                max_tokens=1024
            )
            
            if response.choices and response.choices[0].message and response.choices[0].message.content:
                text = response.choices[0].message.content
                print(f"AI food analysis response: {text}")
                
                # Parse the nutrition response using OpenAI
                analysis = await self._parse_nutrition_response(text)
                if analysis:
                    # Return both the analysis and the transcribed text
                    return (analysis, transcribed_text)
                else:
                    print("Failed to parse nutrition response.")
                    return None
            else:
                print("No valid response from OpenAI for food analysis.")
                return None
                
        except Exception as e:
            print(f"Error analyzing food audio: {e}")
            return None

    async def _parse_nutrition_response(self, text: str) -> Optional[FoodAnalysisResponse]:
        """Convert unstructured nutrition text to structured data using OpenAI"""
        from models.nutrition_models import FoodItem, NutritionInfo
        
        try:
            import asyncio
            
            system_prompt = """Extract nutritional information from the food analysis text.

Rules:
- Identify all food items mentioned and their nutritional information
- If nutritional values are not specified, estimate reasonable values based on typical food content
- Quantities should be descriptive (e.g., "1 medium apple", "2 slices", "1 cup")  
- Calculate total_nutrition as the sum of all food items' nutrition
- If no food is identified, return empty food_items array with zero totals"""

            print("Requesting structured nutrition data from OpenAI...")
            
            response = await asyncio.to_thread(
                self.client.responses.parse,
                model="gpt-4o-2024-08-06",
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Parse this nutrition analysis:\n\n{text}"}
                ],
                text_format=NutritionParseResponse
            )
            
            parsed_data = response.output_parsed
            print(f"Successfully parsed {len(parsed_data.food_items)} food items")
            
            # Convert to your existing models
            food_items = []
            for item_data in parsed_data.food_items:
                nutrition = NutritionInfo(
                    calories=item_data.nutrition.calories,
                    protein=item_data.nutrition.protein,
                    carbs=item_data.nutrition.carbs,
                    fat=item_data.nutrition.fat
                )
                
                food_item = FoodItem(
                    name=item_data.name,
                    quantity=item_data.quantity,
                    nutrition=nutrition
                )
                food_items.append(food_item)
            
            # Create total nutrition
            total_nutrition = NutritionInfo(
                calories=parsed_data.total_nutrition.calories,
                protein=parsed_data.total_nutrition.protein,
                carbs=parsed_data.total_nutrition.carbs,
                fat=parsed_data.total_nutrition.fat
            )
            
            # Create and return FoodAnalysisResponse
            analysis = FoodAnalysisResponse(
                food_items=food_items,
                total_nutrition=total_nutrition,
                analysis_timestamp=datetime.now()
            )
            
            return analysis
                
        except Exception as e:
            print(f"Error parsing nutrition response: {e}")
            return None