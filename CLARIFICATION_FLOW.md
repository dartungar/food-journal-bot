# Food Analysis Clarification Flow

This document describes the new clarification flow implemented in the Food Journal Bot to handle uncertain AI analyses.

## Overview

The bot now includes an intelligent clarification system that:
1. Detects when the AI is uncertain about food identification or quantities
2. Asks users for clarification before storing data
3. Combines original analysis with clarification to create accurate results
4. Maintains conversation state across multiple messages

## Flow Description

### 1. Initial Analysis
User sends food photo or voice message → Bot analyzes with OpenAI → AI determines confidence level

### 2. Uncertainty Detection
The AI now explicitly assesses uncertainty and returns:
- `has_uncertainty`: Boolean indicating if clarification is needed
- `uncertain_items`: List of food items that are unclear
- `uncertainty_reasons`: Specific reasons for uncertainty
- `confidence_score`: Overall confidence (0.0-1.0)

### 3. Clarification Request
If uncertainty is detected:
- Bot stores pending clarification state
- Asks user for clarification with specific details about uncertainties
- User's next photo/voice message is treated as clarification

### 4. Combined Analysis
- Bot combines original analysis with clarification
- Creates final analysis with higher confidence
- Stores result in database

## New Commands

- `/status` - Check if you have pending clarification requests
- `/cancel` - Cancel pending clarification and start over

## Implementation Details

### Key Components

1. **UncertaintyInfo Model** (`models/nutrition_models.py`)
   - Stores uncertainty information from AI analysis

2. **PendingClarification Model** (`models/nutrition_models.py`)
   - Stores user state for pending clarifications

3. **ClarificationService** (`services/clarification_service.py`)
   - Manages pending clarification states
   - Handles persistence to JSON file
   - Automatic cleanup of expired clarifications

4. **Enhanced AI Service** (`services/ai_service.py`)
   - Updated analysis methods to detect uncertainty
   - New `analyze_with_clarification()` method
   - Improved prompts for better uncertainty detection

5. **Updated Handlers** (`handlers/food_handler.py`)
   - State-aware message handling
   - Separate handlers for clarification messages
   - Helper functions for consistent responses

### State Management

- Clarifications are stored in `/app/data/pending_clarifications.json`
- Each user can have at most one pending clarification
- Clarifications expire after 24 hours (configurable)
- State persists across bot restarts

### AI Prompt Engineering

The AI now receives different prompts based on context:
- **Initial Analysis**: Instructed to identify uncertainties
- **Clarification**: Instructed to be more confident with additional context
- **Combined Analysis**: Uses both original and clarification data

## Usage Examples

### Scenario 1: Uncertain Food Identification
1. User sends blurry photo
2. AI responds: "⚠️ I have some uncertainties about your food: **Uncertain items:** some kind of pasta dish **Reasons:** Poor image quality makes specific identification difficult"
3. User sends clearer photo
4. Bot combines both analyses and provides confident result

### Scenario 2: Unclear Quantities
1. User says "I had some chicken and rice"
2. AI responds: "⚠️ I have some uncertainties: **Uncertain items:** chicken portion, rice portion **Reasons:** Vague quantities mentioned"
3. User clarifies: "About 150g chicken breast and 1 cup of rice"
4. Bot creates accurate nutritional analysis

## Benefits

1. **Higher Accuracy**: Prevents guesswork by asking for clarification
2. **User Engagement**: Users provide better data when prompted
3. **Transparency**: Users understand what the AI is uncertain about
4. **Flexibility**: Supports both photo and voice clarifications
5. **State Management**: Maintains context across messages

## Configuration

- Uncertainty threshold: Configurable in AI prompts
- Clarification expiry: 24 hours (configurable in ClarificationService)
- Storage location: `/app/data/pending_clarifications.json`

## Error Handling

- Graceful handling of expired clarifications
- Fallback to regular analysis if clarification fails
- User-friendly error messages
- Logging for debugging

## Future Enhancements

- Multiple clarification rounds
- Learning from user corrections
- Confidence score display to users
- Analytics on uncertainty patterns
