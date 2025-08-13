#!/usr/bin/env python3
"""
Test to verify ClarificationService method names
"""

import sys
import os

# Add the bot directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))

def test_clarification_service_methods():
    """Test that we're calling the correct method names"""
    try:
        from services.clarification_service import ClarificationService
        
        # Create service instance
        service = ClarificationService()
        
        # Check available methods
        available_methods = [method for method in dir(service) if not method.startswith('_')]
        
        print("Available ClarificationService methods:")
        for method in available_methods:
            print(f"  - {method}")
        
        # Verify the methods we need exist
        required_methods = ['has_pending_clarification', 'clear_pending_clarification']
        
        print(f"\nChecking required methods:")
        for method in required_methods:
            if hasattr(service, method):
                print(f"  ✅ {method} - EXISTS")
            else:
                print(f"  ❌ {method} - MISSING")
        
        # Check if the wrong method exists
        if hasattr(service, 'cancel_clarification'):
            print(f"  ⚠️  cancel_clarification - EXISTS (should use clear_pending_clarification instead)")
        else:
            print(f"  ✅ cancel_clarification - DOES NOT EXIST (good, we should use clear_pending_clarification)")
            
    except ImportError as e:
        print(f"Could not import ClarificationService: {e}")

if __name__ == "__main__":
    test_clarification_service_methods()
