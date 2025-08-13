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
        encoded_image = self.encode_image(image_bytes)
        
        # Single-step analysis with structured output
        if clarification_text:
            system_prompt = """You are a Nutritionist's assistant that analyzes food images and provides structured nutritional data.

You previously analyzed this image but had some uncertainties. The user has provided clarification.
Re-analyze the image using the clarification to provide accurate nutrition data.

Rules:
- Identify all food items in the image and their nutritional information
- Estimate reasonable quantities and nutritional values based on visual assessment
- Calculate total_nutrition as the sum of all food items' nutrition
- Since this is a clarification response, set has_uncertainty to false and confidence_score to 0.9 or higher
- Use the clarification to resolve any previous uncertainties"""
            
            user_message = f"Re-analyze this food image with clarification: {clarification_text}\n\nProvide structured nutritional analysis."
        else:
            system_prompt = """You are a Nutritionist's assistant that analyzes food images and provides structured nutritional data.

Analyze the food image and extract nutritional information directly into the structured format.

Rules:
- Identify all food items in the image and estimate their nutritional content
- Estimate quantities based on visual assessment (e.g., "1 medium apple", "2 slices", "1 cup")
- If nutritional values cannot be determined from the image, use typical values for those foods
- Calculate total_nutrition as the sum of all food items' nutrition

Uncertainty Assessment - IMPORTANT:
- ONLY set has_uncertainty to true for MAJOR unclear situations:
  * Completely unidentifiable food items in the image
  * Extremely unclear quantities that cannot be reasonably estimated from visual cues
  * Severely poor image quality making identification impossible
- DO NOT set uncertainty for typical estimation scenarios (use reasonable defaults)
- When in doubt, make your best reasonable estimate and set has_uncertainty to FALSE
- Set confidence_score between 0.0-1.0 (be generous with confidence for reasonable estimates)"""
            
            user_message = "Analyze this food image and provide structured nutritional information."
        
        try:
            import asyncio
            response = await asyncio.to_thread(
                self.client.beta.chat.completions.parse,
                model="gpt-5-mini",
                reasoning_effort="minimal",
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
                response_format=NutritionParseResponse,
                max_completion_tokens=2048
            )
            
            if not response.choices or not response.choices[0].message:
                print("No valid response from OpenAI.")
                return None
                
            parsed_data = response.choices[0].message.parsed
            if not parsed_data:
                print("No parsed data from structured response")
                return None
                
            print(f"Successfully analyzed image with {len(parsed_data.food_items)} food items")
            print(f"Uncertainty detected: {parsed_data.uncertainty.has_uncertainty}")
            
            # Convert to your existing models
            return self._convert_to_food_analysis_response(parsed_data)
            
        except Exception as e:
            print(f"Error analyzing food image: {e}")
            return None

    async def analyze_food_audio(self, audio_bytes: bytes, filename: str = "audio.ogg", clarification_text: str = None) -> Optional[Tuple[FoodAnalysisResponse, str]]:
        """Analyze food audio by transcribing and then analyzing the description in a single step"""
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
            
            # Step 2: Single-step analysis with structured output
            if clarification_text:
                system_prompt = """You are a Nutritionist's assistant that analyzes food descriptions and provides structured nutritional data.

You previously analyzed a food description but had some uncertainties. The user has provided clarification.
Re-analyze using both the original description and clarification to provide accurate nutrition data.

Rules:
- Identify all food items mentioned and their nutritional information
- Estimate reasonable quantities and nutritional values based on the description
- Calculate total_nutrition as the sum of all food items' nutrition
- Since this is a clarification response, set has_uncertainty to false and confidence_score to 0.9 or higher
- Use the clarification to resolve any previous uncertainties"""
                
                user_message = f"Original description: {transcribed_text}\n\nClarification: {clarification_text}\n\nProvide structured nutritional analysis."
            else:
                system_prompt = """You are a Nutritionist's assistant that analyzes food descriptions and provides structured nutritional data.

Analyze the food description and extract nutritional information directly into the structured format.

Rules:
- Identify all food items mentioned and estimate their nutritional content
- Estimate quantities based on the description (e.g., "1 medium apple", "2 slices", "1 cup")
- If specific nutritional values aren't mentioned, use typical values for those foods
- Calculate total_nutrition as the sum of all food items' nutrition

Uncertainty Assessment - IMPORTANT:
- ONLY set has_uncertainty to true for MAJOR unclear situations:
  * Completely unidentifiable food items (cannot guess what it is at all)
  * Extremely vague quantities that cannot be reasonably estimated
  * Multiple conflicting interpretations where you genuinely cannot choose
- DO NOT set uncertainty for typical estimation scenarios (use reasonable defaults)
- When in doubt, make your best reasonable estimate and set has_uncertainty to FALSE
- Set confidence_score between 0.0-1.0 (be generous with confidence for reasonable estimates)"""
                
                user_message = f"Analyze this food description and provide structured nutritional information: {transcribed_text}"
            
            print("Starting single-step food analysis from transcription...")
            
            response = await asyncio.to_thread(
                self.client.beta.chat.completions.parse,
                model="gpt-5-mini",
                reasoning_effort="minimal",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format=NutritionParseResponse,
                max_completion_tokens=2048
            )
            
            print(f"OpenAI structured response: {response}")
            
            if not response.choices or not response.choices[0].message:
                print("No valid response from OpenAI for food analysis.")
                return None
                
            parsed_data = response.choices[0].message.parsed
            if not parsed_data:
                print("No parsed data from structured response")
                return None
                
            print(f"Successfully analyzed audio with {len(parsed_data.food_items)} food items")
            print(f"Uncertainty detected: {parsed_data.uncertainty.has_uncertainty}")
            
            # Convert to your existing models and return with transcribed text
            analysis = self._convert_to_food_analysis_response(parsed_data)
            if analysis:
                return (analysis, transcribed_text)
            else:
                print("Failed to convert parsed data to analysis response.")
                return None
                
        except Exception as e:
            print(f"Error analyzing food audio: {e}")
            return None

    async def analyze_food_text(self, text_description: str, clarification_text: str = None) -> Optional[FoodAnalysisResponse]:
        """Analyze food from text description using single-step structured output"""
        try:
            import asyncio
            
            if clarification_text:
                system_prompt = """You are a Nutritionist's assistant that analyzes food descriptions and provides structured nutritional data.

You previously analyzed a food description but had some uncertainties. The user has provided clarification.
Re-analyze using both the original description and clarification to provide accurate nutrition data.

Rules:
- Identify all food items mentioned and their nutritional information
- Estimate reasonable quantities and nutritional values based on the description
- Calculate total_nutrition as the sum of all food items' nutrition
- Since this is a clarification response, set has_uncertainty to false and confidence_score to 0.9 or higher
- Use the clarification to resolve any previous uncertainties"""
                
                user_message = f"Original description: {text_description}\n\nClarification: {clarification_text}\n\nProvide structured nutritional analysis."
            else:
                system_prompt = """You are a Nutritionist's assistant that analyzes food descriptions and provides structured nutritional data.

Analyze the food description and extract nutritional information directly into the structured format.

Rules:
- Identify all food items mentioned and estimate their nutritional content
- Estimate quantities based on the description (e.g., "1 medium apple", "2 slices", "1 cup")
- If specific nutritional values aren't mentioned, use typical values for those foods
- Calculate total_nutrition as the sum of all food items' nutrition

Uncertainty Assessment - IMPORTANT:
- ONLY set has_uncertainty to true for MAJOR unclear situations:
  * Completely unidentifiable food items (cannot guess what it is at all)
  * Extremely vague quantities that cannot be reasonably estimated
  * Multiple conflicting interpretations where you genuinely cannot choose
- DO NOT set uncertainty for typical estimation scenarios (use reasonable defaults)
- When in doubt, make your best reasonable estimate and set has_uncertainty to FALSE
- Set confidence_score between 0.0-1.0 (be generous with confidence for reasonable estimates)"""
                
                user_message = f"Analyze this food description and provide structured nutritional information: {text_description}"
            
            print("Starting single-step food analysis from text description...")
            
            response = await asyncio.to_thread(
                self.client.beta.chat.completions.parse,
                model="gpt-5-mini",
                reasoning_effort="minimal",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format=NutritionParseResponse,
                max_completion_tokens=2048
            )
            
            if not response.choices or not response.choices[0].message:
                print("No valid response from OpenAI for text analysis.")
                return None
                
            parsed_data = response.choices[0].message.parsed
            if not parsed_data:
                print("No parsed data from structured response")
                return None
                
            print(f"Successfully analyzed text with {len(parsed_data.food_items)} food items")
            print(f"Uncertainty detected: {parsed_data.uncertainty.has_uncertainty}")
            
            # Convert to your existing models
            return self._convert_to_food_analysis_response(parsed_data)
            
        except Exception as e:
            print(f"Error analyzing food text: {e}")
            return None

    def _convert_to_food_analysis_response(self, parsed_data: NutritionParseResponse) -> FoodAnalysisResponse:
        """Convert parsed nutrition data to FoodAnalysisResponse"""
        from models.nutrition_models import FoodItem, NutritionInfo
        
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
        return FoodAnalysisResponse(
            food_items=food_items,
            total_nutrition=total_nutrition,
            analysis_timestamp=datetime.now(),
            uncertainty=uncertainty
        )

    async def analyze_with_clarification(self, 
                                       original_analysis_text: str,
                                       clarification_data: bytes,
                                       clarification_type: str,
                                       filename: str = None) -> Optional[FoodAnalysisResponse]:
        """
        Combine original analysis with clarification to create final analysis using single-step structured output
        
        Args:
            original_analysis_text: The original AI analysis text
            clarification_data: Image or audio bytes for clarification
            clarification_type: 'photo' or 'audio'
            filename: Optional filename for audio files
        """
        try:
            clarification_text = ""
            
            if clarification_type == 'photo':
                # Get clarification from image using structured approach
                encoded_image = self.encode_image(clarification_data)
                system_prompt = """You are helping to clarify a previous food analysis. 
                
Analyze this clarification image and provide structured nutritional data that resolves uncertainties from the original analysis.

Rules:
- Focus on identifying specific foods and quantities visible in the image
- Provide structured output with food items and nutrition data
- Set has_uncertainty to false since this is clarification
- Set confidence_score to 0.9 or higher"""
                
                import asyncio
                response = await asyncio.to_thread(
                    self.client.beta.chat.completions.parse,
                    model="gpt-5-mini",
                    reasoning_effort="minimal",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Original analysis: {original_analysis_text}\n\nPlease analyze this clarification image and provide structured nutritional data:"
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
                    response_format=NutritionParseResponse,
                    max_completion_tokens=1024
                )
                
                if response.choices and response.choices[0].message:
                    parsed_data = response.choices[0].message.parsed
                    if parsed_data:
                        return self._convert_to_food_analysis_response(parsed_data)
                
            elif clarification_type == 'audio':
                # Transcribe clarification audio then analyze with structured output
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
                
                if clarification_text.strip():
                    # Single-step structured analysis with clarification
                    system_prompt = """You are a Nutritionist's assistant that provides structured nutritional data.

You have an original food analysis and clarification from the user. Provide final structured nutritional analysis.

Rules:
- Combine original analysis with user clarification
- Resolve any uncertainties using the clarification
- Set has_uncertainty to false since this is clarification
- Set confidence_score to 0.9 or higher"""
                    
                    combined_prompt = f"""
Original Analysis:
{original_analysis_text}

User Clarification:
{clarification_text}

Provide final structured nutritional analysis combining this information.
"""
                    
                    response = await asyncio.to_thread(
                        self.client.beta.chat.completions.parse,
                        model="gpt-5-mini",
                        reasoning_effort="minimal",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": combined_prompt}
                        ],
                        response_format=NutritionParseResponse,
                        max_completion_tokens=1024
                    )
                    
                    if response.choices and response.choices[0].message:
                        parsed_data = response.choices[0].message.parsed
                        if parsed_data:
                            return self._convert_to_food_analysis_response(parsed_data)
            
            print("Failed to obtain valid clarification analysis")
            return None
                
        except Exception as e:
            print(f"Error in analyze_with_clarification: {e}")
            return None