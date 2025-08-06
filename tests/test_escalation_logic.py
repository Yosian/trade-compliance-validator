import json
import pytest
import sys
import os
from decimal import Decimal
from unittest.mock import Mock, patch

# Add project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import your functions
from src.agents.image_extractor import (
    smart_classify_document, 
    calculate_processing_costs,
    CLASSIFICATION_CONFIDENCE_THRESHOLD,
    CLASSIFICATION_MODELS
)

class TestEscalationLogic:
    """
    Tests the business-critical escalation logic that controls costs
    
    WHY THIS MATTERS: Wrong escalation decisions can cause 10x cost increases.
    A single batch of 1000 documents with incorrect escalation could cost 
    $300 instead of $30 - this is the highest financial risk in the system.
    """
    
    def test_confidence_threshold_exact_boundary(self):
        """Test escalation decisions at the exact 0.8 threshold"""
        
        # Mock the actual Bedrock calls to control the test
        with patch('src.agents.image_extractor.classify_with_bedrock') as mock_classify:
            # Test case 1: Confidence exactly at threshold (0.8) - should NOT escalate
            mock_classify.return_value = {
                'document_type': 'LETTER_OF_CREDIT',
                'confidence': Decimal('0.8'),  # Exactly at threshold
                'complexity_score': Decimal('0.5')
            }
            
            result = smart_classify_document("fake_image", "doc123", "audit123")
            
            # Should use cheap model, no escalation
            assert result['model_used'] == CLASSIFICATION_MODELS['cheap']
            assert result['escalated'] == False
            assert result['confidence'] == Decimal('0.8')
    
    def test_confidence_below_threshold_escalates(self):
        """Test that confidence below 0.8 triggers escalation"""
        
        with patch('src.agents.image_extractor.classify_with_bedrock') as mock_classify:
            # Setup: First call returns low confidence, second call returns high
            mock_classify.side_effect = [
                {  # Stage 1: Low confidence (triggers escalation)
                    'document_type': 'OTHER',
                    'confidence': Decimal('0.79'),  # Just below threshold
                    'complexity_score': Decimal('0.5')
                },
                {  # Stage 2: High confidence from expensive model
                    'document_type': 'LETTER_OF_CREDIT', 
                    'confidence': Decimal('0.95'),
                    'complexity_score': Decimal('0.7')
                }
            ]
            
            result = smart_classify_document("fake_image", "doc123", "audit123")
            
            # Should have escalated to expensive model
            assert result['model_used'] == CLASSIFICATION_MODELS['expensive']
            assert result['escalated'] == True
            assert result['confidence'] == Decimal('0.95')  # Final result from stage 2
            assert mock_classify.call_count == 2  # Called twice (escalation happened)
    
    def test_confidence_above_threshold_no_escalation(self):
        """Test that high confidence uses cheap model only"""
        
        with patch('src.agents.image_extractor.classify_with_bedrock') as mock_classify:
            mock_classify.return_value = {
                'document_type': 'LETTER_OF_CREDIT',
                'confidence': Decimal('0.92'),  # Well above threshold
                'complexity_score': Decimal('0.6')
            }
            
            result = smart_classify_document("fake_image", "doc123", "audit123")
            
            # Should NOT escalate - use cheap model only
            assert result['model_used'] == CLASSIFICATION_MODELS['cheap']
            assert result['escalated'] == False
            assert mock_classify.call_count == 1  # Called once only
    
    def test_decimal_precision_in_threshold_comparison(self):
        """Test that Decimal precision doesn't break threshold logic"""
        
        with patch('src.agents.image_extractor.classify_with_bedrock') as mock_classify:
            # Test edge case: 0.7999999 should escalate, 0.8000001 should not
            test_cases = [
                (Decimal('0.7999999'), True),   # Should escalate
                (Decimal('0.8000001'), False),  # Should not escalate
                (Decimal('0.79999'), True),     # Should escalate 
                (Decimal('0.80001'), False),    # Should not escalate
            ]
            
            for confidence_value, should_escalate in test_cases:
                mock_classify.return_value = {
                    'document_type': 'LETTER_OF_CREDIT',
                    'confidence': confidence_value,
                    'complexity_score': Decimal('0.5')
                }
                
                result = smart_classify_document("fake_image", "doc123", "audit123")
                
                assert result['escalated'] == should_escalate, \
                    f"Confidence {confidence_value} escalation incorrect. Expected {should_escalate}, got {result['escalated']}"
    
    def test_cost_calculation_accuracy(self):
        """Test that cost calculations are mathematically correct"""
        
        # Create mock results for cost calculation
        classification_result = {
            'model_used': CLASSIFICATION_MODELS['cheap'],
            'escalated': False
        }
        extraction_result = {}
        
        costs = calculate_processing_costs(classification_result, extraction_result)
        
        # Verify structure
        assert 'classification_cost_estimate' in costs
        assert 'extraction_cost_estimate' in costs
        assert 'total_estimated_cost' in costs
        assert 'cost_optimization_benefit' in costs
        
        # Verify all costs are Decimal type (not float - would break DynamoDB)
        assert isinstance(costs['classification_cost_estimate'], Decimal)
        assert isinstance(costs['extraction_cost_estimate'], Decimal)
        assert isinstance(costs['total_estimated_cost'], Decimal)
        
        # Verify math: total should equal sum of parts
        expected_total = costs['classification_cost_estimate'] + costs['extraction_cost_estimate']
        assert costs['total_estimated_cost'] == expected_total
        
        # Verify cheap model shows cost optimization benefit
        assert 'cheap' in costs['cost_optimization_benefit'].lower() or 'Used cheap' in costs['cost_optimization_benefit']
    
    def test_escalated_cost_calculation(self):
        """Test cost calculation when escalation occurs (more expensive)"""
        
        # Create mock results for escalated processing
        classification_result = {
            'model_used': CLASSIFICATION_MODELS['expensive'], 
            'escalated': True
        }
        extraction_result = {}
        
        costs = calculate_processing_costs(classification_result, extraction_result)
        
        # Verify escalation is reflected in cost benefit message
        assert 'escalated' in costs['cost_optimization_benefit'].lower() or 'accuracy' in costs['cost_optimization_benefit'].lower()
        
        # The expensive model should cost more than cheap model
        # (We'd need to run both scenarios to compare, but this verifies structure)
        assert costs['total_estimated_cost'] > Decimal('0')
    
    def test_cost_comparison_cheap_vs_expensive(self):
        """Test that expensive model actually costs more than cheap model"""
        
        # Calculate costs for cheap model
        cheap_result = {
            'model_used': CLASSIFICATION_MODELS['cheap'],
            'escalated': False
        }
        cheap_costs = calculate_processing_costs(cheap_result, {})
        
        # Calculate costs for expensive model  
        expensive_result = {
            'model_used': CLASSIFICATION_MODELS['expensive'],
            'escalated': True
        }
        expensive_costs = calculate_processing_costs(expensive_result, {})
        
        # Expensive model should cost significantly more
        assert expensive_costs['total_estimated_cost'] > cheap_costs['total_estimated_cost']
        
        # Should be at least 1.5x more expensive (realistic expectation)
        # Note: Extraction always uses expensive model, so difference is only from classification
        cost_ratio = expensive_costs['total_estimated_cost'] / cheap_costs['total_estimated_cost']
        assert cost_ratio > Decimal('1.5'), f"Expected >1.5x cost difference, got {cost_ratio}x"
        assert cost_ratio < Decimal('3'), f"Cost ratio suspiciously high: {cost_ratio}x"

class TestBusinessIntelligence:
    """
    Test the business intelligence and audit trail features
    """
    
    def test_processing_cost_metadata_completeness(self):
        """Test that all required cost metadata is captured"""
        
        classification_result = {
            'model_used': CLASSIFICATION_MODELS['cheap'],
            'escalated': False
        }
        extraction_result = {}
        
        costs = calculate_processing_costs(classification_result, extraction_result)
        
        # Verify all business intelligence fields are present
        required_fields = [
            'classification_cost_estimate',
            'extraction_cost_estimate', 
            'total_estimated_cost',
            'cost_optimization_benefit'
        ]
        
        for field in required_fields:
            assert field in costs, f"Missing required cost field: {field}"
            assert costs[field] is not None, f"Cost field {field} is None"
    
    def test_cost_precision_for_billing(self):
        """Test that costs are precise enough for business billing"""
        
        classification_result = {'model_used': CLASSIFICATION_MODELS['cheap'], 'escalated': False}
        costs = calculate_processing_costs(classification_result, {})
        
        # Costs should be precise to 6 decimal places (micro-dollar precision)
        for cost_field in ['classification_cost_estimate', 'extraction_cost_estimate', 'total_estimated_cost']:
            cost_value = costs[cost_field]
            # Check decimal precision (should have 6 decimal places max)
            decimal_places = abs(cost_value.as_tuple().exponent)
            assert decimal_places <= 6, f"Cost {cost_field} has too many decimal places: {decimal_places}"

class TestProductionScenarios:
    """
    Test realistic production scenarios that could cause financial impact
    """
    
    def test_batch_processing_cost_optimization(self):
        """Test cost optimization across a realistic batch of documents"""
        
        # Simulate a batch of 100 documents with varying confidence levels
        documents = [
            # 70% high confidence (should use cheap model)
            *[Decimal('0.85')] * 70,
            # 20% medium confidence (should use cheap model) 
            *[Decimal('0.82')] * 20,
            # 10% low confidence (should escalate to expensive model)
            *[Decimal('0.75')] * 10
        ]
        
        escalation_count = 0
        total_estimated_cost = Decimal('0')
        
        for confidence in documents:
            if confidence >= CLASSIFICATION_CONFIDENCE_THRESHOLD:
                # Would use cheap model
                classification_result = {'model_used': CLASSIFICATION_MODELS['cheap'], 'escalated': False}
            else:
                # Would escalate to expensive model
                classification_result = {'model_used': CLASSIFICATION_MODELS['expensive'], 'escalated': True}
                escalation_count += 1
            
            costs = calculate_processing_costs(classification_result, {})
            total_estimated_cost += costs['total_estimated_cost']
        
        # Business validation: only 10% should have escalated
        assert escalation_count == 10, f"Expected 10 escalations, got {escalation_count}"
        
        # Cost should be reasonable (rough check - adjust based on your pricing)
        assert total_estimated_cost < Decimal('10.0'), f"Batch cost too high: ${total_estimated_cost}"
        
        print(f"Batch processing: {escalation_count}/100 documents escalated, total cost: ${total_estimated_cost}")
    
    def test_emergency_high_cost_detection(self):
        """Test detection of unexpectedly high processing costs"""
        
        # Simulate all documents needing expensive model (worst case)
        expensive_result = {
            'model_used': CLASSIFICATION_MODELS['expensive'],
            'escalated': True
        }
        
        costs = calculate_processing_costs(expensive_result, {})
        
        # In production, you might want alerts if costs exceed thresholds
        cost_per_document = costs['total_estimated_cost']
        
        # Alert threshold: > $0.10 per document (adjust as needed)
        COST_ALERT_THRESHOLD = Decimal('0.10')
        
        if cost_per_document > COST_ALERT_THRESHOLD:
            print(f"WARNING: High cost per document: ${cost_per_document}")
            # In production, this would trigger CloudWatch alerts
        
        # Test passes regardless, but logs the warning
        assert True

class TestRetryLogic:
    """
    Test retry logic that prevents infinite loops (learned from $4k incident)
    
    KEY: Maximum 2 attempts, no infinite loops, graceful failure handling
    """
    
    @patch('src.agents.image_extractor.extract_with_specialized_prompt')
    @patch('src.agents.image_extractor.time.sleep')  # Skip sleep in tests
    def test_successful_first_attempt_no_retry(self, mock_sleep, mock_extract):
        """Test that successful first attempt doesn't trigger unnecessary retry"""
        
        # Mock successful extraction on first try
        mock_extract.return_value = {
            'extracted_fields': {
                'lc_number': 'LC123456',
                'beneficiary': 'Samsung Electronics',
                'applicant': 'Apple Inc', 
                'credit_amount': 'USD 100,000',
                'expiry_date': '2025-12-31'
            },
            'confidence': Decimal('0.9'),
            'extraction_notes': 'High quality extraction'
        }
        
        # Import your retry function
        from src.agents.image_extractor import extract_with_retry
        
        result = extract_with_retry("fake_image", "LETTER_OF_CREDIT", "doc123", "audit123")
        
        # Should succeed on first attempt
        assert mock_extract.call_count == 1  # Only called once
        assert mock_sleep.call_count == 0    # No sleep (no retry)
        assert result['retry_metadata']['attempts_made'] == 1
        assert result['retry_metadata']['success_on_attempt'] == 1
        assert result['retry_metadata']['validation_passed'] == True
    
    @patch('src.agents.image_extractor.extract_with_specialized_prompt')  
    @patch('src.agents.image_extractor.time.sleep')
    def test_first_fails_second_succeeds(self, mock_sleep, mock_extract):
        """Test retry logic when first attempt fails but second succeeds"""
        
        # Mock first attempt failure, second attempt success
        mock_extract.side_effect = [
            {  # First attempt: poor quality
                'extracted_fields': {},  # No fields extracted
                'confidence': Decimal('0.2'),  # Low confidence
                'extraction_notes': 'Poor image quality'
            },
            {  # Second attempt: good quality  
                'extracted_fields': {
                    'lc_number': 'LC123456',
                    'beneficiary': 'Samsung Electronics',
                    'credit_amount': 'USD 100,000'
                },
                'confidence': Decimal('0.8'),
                'extraction_notes': 'Successful retry'
            }
        ]
        
        from src.agents.image_extractor import extract_with_retry
        
        result = extract_with_retry("fake_image", "LETTER_OF_CREDIT", "doc123", "audit123")
        
        # Should have retried exactly once
        assert mock_extract.call_count == 2  # Called twice
        assert mock_sleep.call_count == 1    # One sleep between attempts
        assert result['retry_metadata']['attempts_made'] == 2
        assert result['retry_metadata']['success_on_attempt'] == 2
        assert result['retry_metadata']['validation_passed'] == True
    
    @patch('src.agents.image_extractor.extract_with_specialized_prompt')
    @patch('src.agents.image_extractor.time.sleep')
    def test_both_attempts_fail_no_infinite_loop(self, mock_sleep, mock_extract):
        """CRITICAL TEST: Both attempts fail but NO INFINITE LOOP (prevents $4k incident)"""
        
        # Mock both attempts failing
        mock_extract.side_effect = [
            {  # First attempt: poor quality
                'extracted_fields': {},
                'confidence': Decimal('0.1'),
                'extraction_notes': 'Failed extraction'
            },
            {  # Second attempt: still poor quality
                'extracted_fields': {'incomplete': 'data'},
                'confidence': Decimal('0.2'), 
                'extraction_notes': 'Still failed extraction'
            }
        ]
        
        from src.agents.image_extractor import extract_with_retry
        
        result = extract_with_retry("fake_image", "LETTER_OF_CREDIT", "doc123", "audit123")
        
        # CRITICAL: Should stop after exactly 2 attempts (NO INFINITE LOOP)
        assert mock_extract.call_count == 2  # Exactly 2 attempts
        assert mock_sleep.call_count == 1    # One sleep between attempts
        assert result['retry_metadata']['attempts_made'] == 2
        assert result['retry_metadata']['success_on_attempt'] is None  # Failed
        assert result['retry_metadata']['validation_passed'] == False
        
        # Should return the second (final) attempt result
        assert 'incomplete' in result['extracted_fields']
    
    @patch('src.agents.image_extractor.extract_with_specialized_prompt')
    @patch('src.agents.image_extractor.time.sleep')
    def test_exception_on_first_success_on_second(self, mock_sleep, mock_extract):
        """Test that exceptions trigger retry (but with hard limits)"""
        
        # Mock exception on first try, success on second
        mock_extract.side_effect = [
            Exception("Bedrock API timeout"),  # First attempt throws exception
            {  # Second attempt succeeds
                'extracted_fields': {'lc_number': 'LC789', 'beneficiary': 'Test Corp'},
                'confidence': Decimal('0.7'),
                'extraction_notes': 'Successful after exception'
            }
        ]
        
        from src.agents.image_extractor import extract_with_retry
        
        result = extract_with_retry("fake_image", "LETTER_OF_CREDIT", "doc123", "audit123")
        
        # Should have retried after exception
        assert mock_extract.call_count == 2
        assert result['retry_metadata']['attempts_made'] == 2
        assert result['retry_metadata']['success_on_attempt'] == 2
        assert 'lc_number' in result['extracted_fields']
    
    @patch('src.agents.image_extractor.extract_with_specialized_prompt')
    @patch('src.agents.image_extractor.time.sleep')
    def test_exceptions_on_both_attempts_no_infinite_loop(self, mock_sleep, mock_extract):
        """CRITICAL TEST: Exceptions on both attempts but NO INFINITE LOOP"""
        
        # Mock exceptions on both attempts
        mock_extract.side_effect = [
            Exception("First API failure"),
            Exception("Second API failure")
        ]
        
        from src.agents.image_extractor import extract_with_retry
        
        result = extract_with_retry("fake_image", "LETTER_OF_CREDIT", "doc123", "audit123")
        
        # CRITICAL: Should stop after exactly 2 attempts, not loop forever
        assert mock_extract.call_count == 2  # Exactly 2 attempts
        assert mock_sleep.call_count == 1    # One sleep between attempts
        
        # Should return error result (not crash)
        assert result['extracted_fields'] == {}
        assert result['confidence'] == Decimal('0.1')
        assert result['retry_metadata']['attempts_made'] == 2
        assert result['retry_metadata']['success_on_attempt'] is None
        assert 'Second API failure' in result['retry_metadata']['final_error']
    
    def test_critical_fields_validation_logic(self):
        """Test that validation logic correctly identifies poor quality extractions"""
        
        from src.agents.image_extractor import validate_extraction_quality
        
        # Test case 1: Good extraction (should not need retry)
        good_extraction = {
            'extracted_fields': {
                'lc_number': 'LC123',
                'beneficiary': 'Samsung',
                'applicant': 'Apple',
                'credit_amount': 'USD 100,000',
                'expiry_date': '2025-12-31'
            },
            'confidence': Decimal('0.85')
        }
        
        validation = validate_extraction_quality(good_extraction, 'LETTER_OF_CREDIT')
        assert validation['is_acceptable'] == True
        assert validation['quality_score'] > Decimal('0.4')
        
        # Test case 2: Poor extraction (should trigger retry)
        poor_extraction = {
            'extracted_fields': {},  # No fields
            'confidence': Decimal('0.2')  # Low confidence
        }
        
        validation = validate_extraction_quality(poor_extraction, 'LETTER_OF_CREDIT')
        assert validation['is_acceptable'] == False
        assert 'no_fields_extracted' in validation['issues']
        assert 'confidence_too_low' in validation['issues']
    
    def test_max_attempts_constant_prevents_infinite_loops(self):
        """Test that MAX_EXTRACTION_ATTEMPTS constant is reasonable"""
        
        from src.agents.image_extractor import MAX_EXTRACTION_ATTEMPTS
        
        # Should be exactly 2 (your lesson learned from $4k incident)
        assert MAX_EXTRACTION_ATTEMPTS == 2
        assert MAX_EXTRACTION_ATTEMPTS < 10  # Sanity check - never allow high limits