"""
Service for managing food analysis clarifications and user state
"""
import json
import os
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from models.nutrition_models import PendingClarification

class ClarificationService:
    """Manages pending clarifications and user states"""
    
    def __init__(self, storage_file: str = '/app/data/pending_clarifications.json'):
        self.storage_file = storage_file
        self._pending_clarifications: Dict[int, PendingClarification] = {}
        self._load_from_file()
    
    def _load_from_file(self):
        """Load pending clarifications from file"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    for user_id_str, clarification_dict in data.items():
                        user_id = int(user_id_str)
                        # Convert timestamp string back to datetime
                        clarification_dict['timestamp'] = datetime.fromisoformat(clarification_dict['timestamp'])
                        clarification = PendingClarification(**clarification_dict)
                        self._pending_clarifications[user_id] = clarification
        except Exception as e:
            print(f"Error loading clarifications from file: {e}")
            self._pending_clarifications = {}
    
    def _save_to_file(self):
        """Save pending clarifications to file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
            
            # Convert to serializable format
            data = {}
            for user_id, clarification in self._pending_clarifications.items():
                clarification_dict = clarification.model_dump()
                # Convert datetime to string for JSON serialization
                clarification_dict['timestamp'] = clarification.timestamp.isoformat()
                data[str(user_id)] = clarification_dict
            
            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving clarifications to file: {e}")
    
    def has_pending_clarification(self, user_id: int) -> bool:
        """Check if user has pending clarification"""
        return user_id in self._pending_clarifications
    
    def store_pending_clarification(self, 
                                    user_id: int,
                                    original_data: Dict[str, Any],
                                    analysis_text: str,
                                    uncertain_items: list,
                                    uncertainty_reasons: list,
                                    media_type: str) -> None:
        """Store a pending clarification request"""
        clarification = PendingClarification(
            user_id=user_id,
            original_data=original_data,
            analysis_text=analysis_text,
            uncertain_items=uncertain_items,
            uncertainty_reasons=uncertainty_reasons,
            timestamp=datetime.now(),
            media_type=media_type
        )
        
        self._pending_clarifications[user_id] = clarification
        self._save_to_file()
    
    def get_pending_clarification(self, user_id: int) -> Optional[PendingClarification]:
        """Get pending clarification for user"""
        return self._pending_clarifications.get(user_id)
    
    def clear_pending_clarification(self, user_id: int) -> None:
        """Clear pending clarification for user"""
        if user_id in self._pending_clarifications:
            del self._pending_clarifications[user_id]
            self._save_to_file()
    
    def cleanup_expired_clarifications(self, max_age_hours: int = 24) -> None:
        """Remove clarifications older than specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        expired_users = []
        
        for user_id, clarification in self._pending_clarifications.items():
            if clarification.timestamp < cutoff_time:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self._pending_clarifications[user_id]
        
        if expired_users:
            self._save_to_file()
            print(f"Cleaned up {len(expired_users)} expired clarifications")
