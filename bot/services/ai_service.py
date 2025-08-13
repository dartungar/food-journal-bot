import base64
from openai import OpenAI
from typing import Optional, List, Tuple
from models.nutrition_models import FoodAnalysisResponse, UncertaintyInfo
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

class UncertaintyData(BaseModel):
    has_uncertainty: bool
    uncertain_items: List[str]
    uncertainty_reasons: List[str]
    confidence_score: float

class NutritionParseResponse(BaseModel):
    food_items: List[FoodItemData]
    total_nutrition: NutritionData
    uncertainty: UncertaintyData

class AIFoodAnalyzer:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    def encode_image(self, image_bytes: bytes) -> str:
        return base64.b64encode(image_bytes).decode('utf-8')
    
    async def analyze_food_image(self, image_bytes: bytes, clarification_text: str = None) -> Optional[FoodAnalysisResponse]:
        import re
        encoded_image = self.encode_image(image_bytes)
        
        # Modify system prompt based on whether this is initial analysis or clarification
        if clarification_text:
            system_prompt = (
                "You are a Nutritionist's assistant. "
                "You previously analyzed a food image but had some uncertainties. "
                "The user has now provided clarification. "
                "Re-analyze the image using the clarification to provide accurate nutrition data. "
                "Be more confident in your analysis now that you have clarification."
            )
            user_message = f"Re-analyze this food image with the following clarification: {clarification_text}"
        else:
            system_prompt = (
                "You are a Nutritionist's assistant. "
                "You analyze pictures of food and provide detailed description for Nutritionist, "
                "so that he can analyze food and provide nutrition data. "
                "If you're uncertain about food identification, quantities, or nutritional content, "
                "clearly indicate your uncertainties in your response."
            )
            user_message = "Analyze this food image and provide nutritional information."
        
        try:
            import asyncio
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_message
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{encoded_image}"
                                }
                            }
                        ]
                    }
                ],
                max_completion_tokens=2048
            )
            if response.choices and response.choices[0].message and response.choices[0].message.content:
                text = response.choices[0].message.content
                print(f"AI response: {text}")
                # Use OpenAI to parse nutrition info into structured format
                return await self._parse_nutrition_response(text, is_clarification=bool(clarification_text))
            else:
                print("No valid response from OpenAI.")
                return None
        except Exception as e:
            print(f"Error analyzing food image: {e}")
            return None

    async def analyze_food_audio(self, audio_bytes: bytes, filename: str = "audio.ogg", clarification_text: str = None) -> Optional[Tuple[FoodAnalysisResponse, str]]:
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
            if clarification_text:
                system_prompt = (
                    "You are a Nutritionist's assistant. "
                    "You previously analyzed a food description but had some uncertainties. "
                    "The user has now provided clarification. "
                    "Re-analyze the food description using the clarification to provide accurate nutrition data. "
                    "Be more confident in your analysis now that you have clarification."
                )
                user_message = f"Original description: {transcribed_text}\n\nClarification: {clarification_text}\n\nProvide accurate nutritional information."
            else:
                system_prompt = (
                    "You are a Nutritionist's assistant. "
                    "You analyze food descriptions and provide detailed nutritional information. "
                    "Based on the food description, estimate portions and provide nutrition data including "
                    "calories, protein, carbs, and fat for each food item mentioned. "
                    "If you're uncertain about food identification, quantities, or nutritional content, "
                    "clearly indicate your uncertainties in your response."
                )
                user_message = f"Analyze this food description and provide nutritional information: {transcribed_text}"
            
            print("Starting food analysis from transcription...")
            
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_completion_tokens=2048
            )
            
            print(f"OpenAI chat completions response: {response}")
            print(f"Response choices: {response.choices if response.choices else 'None'}")
            if response.choices and response.choices[0].message:
                print(f"Message content: '{response.choices[0].message.content}'")
                print(f"Message content type: {type(response.choices[0].message.content)}")
            
            if response.choices and response.choices[0].message and response.choices[0].message.content:
                text = response.choices[0].message.content
                print(f"AI food analysis response: {text}")
                
                # Parse the nutrition response using OpenAI
                analysis = await self._parse_nutrition_response(text, is_clarification=bool(clarification_text))
                if analysis:
                    # Return both the analysis and the transcribed text
                    return (analysis, transcribed_text)
                else:
                    print("Failed to parse nutrition response.")
                    return None
            elif response.choices and response.choices[0].message and response.choices[0].message.content == '':
                print("Empty response content from OpenAI - likely due to token limit. Retrying with simpler prompt...")
                
                # Retry with a simpler, more direct prompt
                simple_prompt = (
                    "Analyze this food description and provide a simple nutritional breakdown. "
                    "List each food item with estimated calories, protein, carbs, and fat. "
                    "Be concise and direct."
                )
                
                retry_response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model="gpt-4o-mini",  # Use a simpler model for retry
                    messages=[
                        {"role": "system", "content": simple_prompt},
                        {"role": "user", "content": f"Analyze this food: {transcribed_text}"}
                    ],
                    max_completion_tokens=1024
                )
                
                if retry_response.choices and retry_response.choices[0].message and retry_response.choices[0].message.content:
                    text = retry_response.choices[0].message.content
                    print(f"Retry AI food analysis response: {text}")
                    
                    # Parse the nutrition response using OpenAI
                    analysis = await self._parse_nutrition_response(text, is_clarification=bool(clarification_text))
                    if analysis:
                        return (analysis, transcribed_text)
                    else:
                        print("Failed to parse retry nutrition response.")
                        return None
                else:
                    print("Retry also failed to produce valid content.")
                    return None
            else:
                print("No valid response from OpenAI for food analysis.")
                return None
                
        except Exception as e:
            print(f"Error analyzing food audio: {e}")
            return None

    async def _parse_nutrition_response(self, text: str, is_clarification: bool = False) -> Optional[FoodAnalysisResponse]:
        """Convert unstructured nutrition text to structured data using OpenAI"""
        from models.nutrition_models import FoodItem, NutritionInfo
        
        try:
            import asyncio
            
            # Adjust system prompt based on whether this is a clarification
            if is_clarification:
                system_prompt = """Extract nutritional information from the food analysis text.

Rules:
- Identify all food items mentioned and their nutritional information
- If nutritional values are not specified, estimate reasonable values based on typical food content
- Quantities should be descriptive (e.g., "1 medium apple", "2 slices", "1 cup")  
- Calculate total_nutrition as the sum of all food items' nutrition
- If no food is identified, return empty food_items array with zero totals
- Since this is a clarification response, set has_uncertainty to false and confidence_score to 0.9 or higher"""
            else:
                system_prompt = """Extract nutritional information from the food analysis text and assess uncertainty.

Rules:
- Identify all food items mentioned and their nutritional information
- If nutritional values are not specified, estimate reasonable values based on typical food content
- Quantities should be descriptive (e.g., "1 medium apple", "2 slices", "1 cup")  
- Calculate total_nutrition as the sum of all food items' nutrition
- If no food is identified, return empty food_items array with zero totals

Uncertainty Assessment - IMPORTANT:
- ONLY set has_uncertainty to true for MAJOR unclear situations:
  * Completely unidentifiable food items (cannot guess what it is at all)
  * Extremely vague quantities that cannot be reasonably estimated
  * Multiple conflicting interpretations where you genuinely cannot choose
  * Severely poor image/audio quality making identification impossible

- DO NOT set has_uncertainty for these common situations:
  * Brand variations (use generic/average values)
  * Recipe variations (use typical/standard recipes)
  * Preparation method variations (choose most common)
  * Minor ingredient variations (estimate based on standard versions)
  * Typical food quality variations (use average nutritional values)

- When in doubt, make your best reasonable estimate and set has_uncertainty to FALSE
- Use generic product nutritional values when brand is unknown
- Only ask for clarification when you genuinely cannot make any reasonable guess
- List specific uncertain_items (only truly unclear food names)
- Provide uncertainty_reasons (only for major unclear situations)
- Set confidence_score between 0.0-1.0 (be generous with confidence for reasonable estimates)
- For most situations with identifiable food, set has_uncertainty to false, empty arrays, confidence_score 0.8+"""

            print("Requesting structured nutrition data from OpenAI...")
            print(f"Input text for parsing: {text[:200]}...")
            
            response = await asyncio.to_thread(
                self.client.beta.chat.completions.parse,
                model="gpt-5",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Parse this nutrition analysis:\n\n{text}"}
                ],
                response_format=NutritionParseResponse
            )
            
            print(f"OpenAI structured parsing response: {response}")
            
            if not response.choices or not response.choices[0].message:
                print("No valid response from structured parsing")
                return None
                
            parsed_data = response.choices[0].message.parsed
            if not parsed_data:
                print("No parsed data from structured response")
                return None
                
            print(f"Successfully parsed {len(parsed_data.food_items)} food items")
            print(f"Uncertainty detected: {parsed_data.uncertainty.has_uncertainty}")
            
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
            
            # Create uncertainty info
            uncertainty = UncertaintyInfo(
                has_uncertainty=parsed_data.uncertainty.has_uncertainty,
                uncertain_items=parsed_data.uncertainty.uncertain_items,
                uncertainty_reasons=parsed_data.uncertainty.uncertainty_reasons,
                confidence_score=parsed_data.uncertainty.confidence_score
            )
            
            # Create and return FoodAnalysisResponse
            analysis = FoodAnalysisResponse(
                food_items=food_items,
                total_nutrition=total_nutrition,
                analysis_timestamp=datetime.now(),
                uncertainty=uncertainty
            )
            
            return analysis
                
        except Exception as e:
            print(f"Error parsing nutrition response: {e}")
            print(f"Exception type: {type(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return None

    async def analyze_with_clarification(self, 
                                       original_analysis_text: str,
                                       clarification_data: bytes,
                                       clarification_type: str,
                                       filename: str = None) -> Optional[FoodAnalysisResponse]:
        """
        Combine original analysis with clarification to create final analysis
        
        Args:
            original_analysis_text: The original AI analysis text
            clarification_data: Image or audio bytes for clarification
            clarification_type: 'photo' or 'audio'
            filename: Optional filename for audio files
        """
        try:
            clarification_text = ""
            
            if clarification_type == 'photo':
                # Analyze clarification image
                encoded_image = self.encode_image(clarification_data)
                system_prompt = (
                    "You are helping to clarify a previous food analysis. "
                    "Analyze this clarification image and describe what you see. "
                    "Focus on identifying specific foods and quantities that might help clarify the original analysis."
                )
                
                import asyncio
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model="gpt-5-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Please describe this clarification image in detail:"
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{encoded_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_completion_tokens=512
                )
                
                if response.choices and response.choices[0].message:
                    clarification_text = response.choices[0].message.content
                
            elif clarification_type == 'audio':
                # Transcribe clarification audio
                import asyncio
                import io
                
                audio_bytes_io = io.BytesIO(clarification_data)
                audio_bytes_io.name = filename or "clarification.ogg"
                
                transcription = await asyncio.to_thread(
                    self.client.audio.transcriptions.create,
                    model="gpt-4o-mini-transcribe",
                    file=audio_bytes_io,
                    language="en"
                )
                
                clarification_text = transcription.text
            
            if not clarification_text.strip():
                print("No clarification text obtained")
                return None
            
            # Now combine original analysis with clarification
            system_prompt = (
                "You are a Nutritionist's assistant. "
                "You have an original food analysis and now received clarification from the user. "
                "Create a final, accurate nutritional analysis combining both pieces of information. "
                "Use the clarification to resolve any uncertainties from the original analysis."
            )
            
            combined_prompt = f"""
Original Analysis:
{original_analysis_text}

User Clarification:
{clarification_text}

Please provide a final, accurate nutritional analysis that combines this information and resolves any uncertainties.
"""
            
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": combined_prompt}
                ],
                max_completion_tokens=1024
            )
            
            if response.choices and response.choices[0].message and response.choices[0].message.content:
                final_analysis_text = response.choices[0].message.content
                print(f"Final combined analysis: {final_analysis_text}")
                
                # Parse the final analysis (mark as clarification so uncertainty is low)
                return await self._parse_nutrition_response(final_analysis_text, is_clarification=True)
            else:
                print("No valid response for combined analysis")
                return None
                
        except Exception as e:
            print(f"Error in analyze_with_clarification: {e}")
            return None