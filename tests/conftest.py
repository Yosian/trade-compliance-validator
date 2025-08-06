import pytest
import json
import os

@pytest.fixture
def claude_responses():
    """Load test responses that simulate Claude's actual outputs"""
    return {
        # What Claude SHOULD return
        'valid_response': {
            "document_type": "LETTER_OF_CREDIT",
            "confidence": 0.92,
            "complexity_score": 0.7,
            "reasoning": "Clear LC structure with issuing bank details"
        },
        
        # What can go WRONG in production
        'malformed_json': '{"document_type": "LETTER_OF_CREDIT", "confidence": 0.8',  # Missing }
        'missing_confidence': {
            "document_type": "LETTER_OF_CREDIT"
            # confidence field missing!
        },
        'invalid_confidence': {
            "document_type": "LETTER_OF_CREDIT", 
            "confidence": "very high"  # String instead of number
        },
        'truncated_response': '{"document_type": "LET'  # Token limit truncation
    }