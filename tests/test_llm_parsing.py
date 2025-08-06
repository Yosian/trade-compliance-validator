import json
import pytest
import sys
import os
from decimal import Decimal

# Add project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import your functions
from src.agents.image_extractor import parse_claude_classification_response, convert_floats_to_decimal

class TestLLMResponseParsing:
    """
    Tests the most critical failure point: parsing Claude's responses
    
    WHY THIS MATTERS: Claude responses are unpredictable and can break
    our processing pipeline if not handled properly.
    
    We test the parsing logic directly without AWS dependencies.
    """
    
    def test_valid_response_parsing(self):
        """Test that we correctly parse a perfect Claude response"""
        valid_response = {
            "document_type": "LETTER_OF_CREDIT",
            "confidence": 0.92,
            "complexity_score": 0.7,
            "reasoning": "Clear LC structure with issuing bank details"
        }
        
        response_text = json.dumps(valid_response)
        result = parse_claude_classification_response(response_text)
        
        assert result['document_type'] == 'LETTER_OF_CREDIT'
        assert result['confidence'] == Decimal('0.92')
        assert result['complexity_score'] == Decimal('0.7')
        assert 'raw_response' in result
            
    def test_malformed_json_handling(self):
        """Test that we don't crash when Claude returns broken JSON"""
        # This happens in production when token limits cut off responses
        malformed_json = '{"document_type": "LETTER_OF_CREDIT", "confidence": 0.8'  # Missing closing brace
        
        result = parse_claude_classification_response(malformed_json)
        
        # Should not crash, should return safe defaults
        assert result['document_type'] == 'OTHER'  # Safe fallback
        assert result['confidence'] == Decimal('0.3')  # Low confidence for safety
        assert result['raw_response'] == malformed_json
        
    def test_missing_confidence_field(self):
        """Test when Claude forgets to include confidence score"""
        missing_confidence = {
            "document_type": "LETTER_OF_CREDIT"
            # confidence field missing!
        }
        
        response_text = json.dumps(missing_confidence)
        result = parse_claude_classification_response(response_text)
        
        assert result['document_type'] == 'LETTER_OF_CREDIT'  # Should keep what's valid
        assert result['confidence'] == Decimal('0.5')  # Safe default for missing confidence
        
    def test_invalid_confidence_type(self):
        """Test when Claude returns confidence as string instead of number"""
        invalid_confidence = {
            "document_type": "LETTER_OF_CREDIT", 
            "confidence": "very high"  # String instead of number
        }

        response_text = json.dumps(invalid_confidence)
        result = parse_claude_classification_response(response_text)

        # Keep valid document_type, but downgrade confidence
        assert result['document_type'] == 'LETTER_OF_CREDIT'
        assert result['confidence'] == Decimal('0.3')  # Low confidence fallback

        
    def test_completely_invalid_response(self):
        """Test completely non-JSON response"""
        invalid_response = "I cannot process this document due to quality issues."
        
        result = parse_claude_classification_response(invalid_response)
        
        # Should not crash, should return safe defaults
        assert result['document_type'] == 'OTHER'
        assert result['confidence'] == Decimal('0.3')
        assert result['raw_response'] == invalid_response
        
    def test_decimal_conversion_safety(self):
        """Test that float-to-Decimal conversion doesn't break DynamoDB"""
        # This is critical - DynamoDB fails if we send floats instead of Decimals
        test_data = {
            'confidence': 0.85,  # Float that must become Decimal
            'nested': {
                'score': 0.92,
                'values': [0.1, 0.2, 0.3]
            }
        }
        
        result = convert_floats_to_decimal(test_data)
        
        # All floats should be Decimals now
        assert isinstance(result['confidence'], Decimal)
        assert isinstance(result['nested']['score'], Decimal)
        assert all(isinstance(v, Decimal) for v in result['nested']['values'])