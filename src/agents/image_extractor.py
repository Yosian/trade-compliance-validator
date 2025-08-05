import json
import boto3
import base64
import uuid
import os
from datetime import datetime, timezone
import logging
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AWS clients
bedrock = boto3.client('bedrock-runtime')
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Environment variables (these would come from your .env.dev file)
DOCUMENTS_TABLE = 'tdv-dev-documents-864899848062-us-east-1'
AUDIT_TABLE = 'tdv-dev-audit-trail-864899848062-us-east-1'

# Model configuration for cost optimization
CLASSIFICATION_MODELS = {
    'cheap': 'anthropic.claude-3-haiku-20240307-v1:0',
    'expensive': 'anthropic.claude-3-sonnet-20240229-v1:0'
}
EXTRACTION_MODEL = 'anthropic.claude-3-sonnet-20240229-v1:0'

# Confidence threshold for classification escalation
CLASSIFICATION_CONFIDENCE_THRESHOLD = 0.8

# Prompt content - embedded for demo (in production, load from S3 or deployment package)
CLASSIFIER_PROMPT = """You are a trade finance document classifier. Analyze this document image and classify it into one of the following trade finance document categories.

## DOCUMENT TYPES:

**LETTER_OF_CREDIT**: Letters of credit, documentary credits, LC amendments, standby letters of credit
- Look for: LC number, issuing bank, beneficiary, applicant, credit amount, UCP600 references

**COMMERCIAL_INVOICE**: Commercial invoices, proforma invoices, tax invoices
- Look for: Invoice number, seller/buyer details, itemized goods, total amounts, payment terms

**BILL_OF_LADING**: Bills of lading, sea waybills, airway bills, shipping documents
- Look for: Vessel/flight details, consignee, shipper, cargo description, ports of loading/discharge

**PACKING_LIST**: Packing lists, shipping manifests, cargo manifests
- Look for: Detailed item descriptions, quantities, weights, packaging details, container information

**CERTIFICATE**: Certificates of origin, inspection certificates, quality certificates, insurance certificates
- Look for: Certification authority, certificate number, goods covered, validity dates

**OTHER**: Any document that doesn't clearly fit the above categories

Return your classification as valid JSON in this exact structure:

{
    "document_type": "DOCUMENT_TYPE_HERE",
    "confidence": 0.85,
    "complexity_score": 0.6,
    "reasoning": "Brief explanation of classification decision",
    "key_indicators": ["list", "of", "key", "terms", "found"],
    "alternative_types": ["possible", "alternative", "classifications"]
}

Focus on accuracy over speed. Better to be uncertain and trigger expert review than to misclassify."""

LETTER_OF_CREDIT_PROMPT = """You are an expert trade finance analyst specializing in Letters of Credit (LC) under UCP600 rules. Analyze this Letter of Credit document image and extract key information with precision.

Extract the following Letter of Credit fields and return as valid JSON. If a field cannot be determined with confidence, return null rather than guessing.

Return your analysis as valid JSON in this exact structure:

{
    "extracted_fields": {
        "lc_number": "extracted value or null",
        "issue_date": "YYYY-MM-DD or null",
        "expiry_date": "YYYY-MM-DD or null",
        "expiry_place": "extracted value or null",
        "applicant": "extracted value or null",
        "beneficiary": "extracted value or null",
        "issuing_bank": "extracted value or null",
        "advising_bank": "extracted value or null",
        "credit_amount": "extracted value or null",
        "currency": "extracted value or null",
        "available_with": "extracted value or null",
        "available_by": "extracted value or null",
        "shipment_from": "extracted value or null",
        "shipment_to": "extracted value or null",
        "partial_shipments": "extracted value or null",
        "transhipment": "extracted value or null",
        "latest_shipment_date": "YYYY-MM-DD or null",
        "required_documents": ["list of documents or empty array"],
        "payment_terms": "extracted value or null",
        "charges": "extracted value or null"
    },
    "confidence": 0.85,
    "extraction_notes": "Quality assessment and any extraction challenges encountered"
}

Focus on precision and flag any ambiguities for human expert review."""

def lambda_handler(event, context):
    """
    Enhanced Claude Vision Lambda with two-stage processing
    
    Stage 1: Smart document classification (cost-optimized)
    Stage 2: Specialized extraction using document-specific prompts
    """
    
    # Initialize audit tracking
    audit_id = str(uuid.uuid4())
    document_id = None
    
    try:
        # Parse SQS message
        for record in event['Records']:
            message_body = json.loads(record['body'])
            
            # Extract file information
            bucket = message_body['bucket']
            key = message_body['key']
            file_extension = message_body.get('file_extension', 'unknown')
            
            # Generate document ID
            document_id = f"doc_{uuid.uuid4().hex[:12]}"
            
            print(f"Processing document: {key} (ID: {document_id})")
            
            # Log processing start
            log_audit_event(audit_id, document_id, 'PROCESSING_STARTED', {
                'bucket': bucket,
                'key': key,
                'file_extension': file_extension,
                'lambda_request_id': context.aws_request_id,
                'processing_strategy': 'two_stage_with_embedded_prompts'
            })
            
            # Download and process image
            result = process_document_enhanced(bucket, key, document_id, audit_id)
            
            # Store results with training metadata
            store_document_results_enhanced(document_id, bucket, key, result, audit_id)
            
            # Log successful completion
            log_audit_event(audit_id, document_id, 'PROCESSING_COMPLETED', {
                'document_type': result.get('document_type'),
                'classification_confidence': result.get('classification_confidence'),
                'extraction_confidence': result.get('extraction_confidence'),
                'total_cost_estimate': result.get('processing_costs', {}).get('total_estimated_cost')
            })
            
            print(f"Successfully processed document {document_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Documents processed successfully',
                'document_id': document_id,
                'audit_id': audit_id,
                'processing_strategy': 'enhanced_two_stage'
            })
        }
        
    except Exception as e:
        # Log error with full context
        error_msg = str(e)
        print(f"Error processing document: {error_msg}")
        
        if document_id and audit_id:
            log_audit_event(audit_id, document_id, 'PROCESSING_FAILED', {
                'error': error_msg,
                'error_type': type(e).__name__
            })
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': error_msg,
                'document_id': document_id,
                'audit_id': audit_id
            })
        }

def process_document_enhanced(bucket, key, document_id, audit_id):
    """
    Enhanced document processing with two-stage classification and extraction
    """
    
    try:
        # Download image from S3
        log_audit_event(audit_id, document_id, 'S3_DOWNLOAD_STARTED', {'bucket': bucket, 'key': key})
        
        response = s3.get_object(Bucket=bucket, Key=key)
        image_data = response['Body'].read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        log_audit_event(audit_id, document_id, 'S3_DOWNLOAD_COMPLETED', {
            'image_size_bytes': len(image_data),
            'image_size_base64': len(image_base64)
        })
        
        print(f"Downloaded image: {len(image_data)} bytes")
        
        # Stage 1: Smart document classification (cost-optimized)
        classification_result = smart_classify_document(image_base64, document_id, audit_id)
        
        # Stage 2: Specialized extraction based on document type
        extraction_result = extract_with_specialized_prompt(
            image_base64, 
            classification_result['document_type'], 
            document_id, 
            audit_id
        )
        
        # Combine results with metadata for training
        combined_result = {
            'document_type': classification_result['document_type'],
            'classification_confidence': classification_result['confidence'],
            'classification_model_used': classification_result['model_used'],
            'classification_escalated': classification_result.get('escalated', False),
            'extracted_fields': extraction_result.get('extracted_fields', {}),
            'extraction_confidence': extraction_result.get('confidence', 0.0),
            'extraction_notes': extraction_result.get('extraction_notes', ''),
            'processing_costs': calculate_processing_costs(classification_result, extraction_result),
            'training_metadata': {
                'image_quality_score': assess_image_quality(image_data),
                'document_complexity_score': classification_result.get('complexity_score', 0.5),
                'processing_timestamp': datetime.now(timezone.utc).isoformat(),
                'models_used': {
                    'classification': classification_result['model_used'],
                    'extraction': EXTRACTION_MODEL
                }
            }
        }
        
        return combined_result
        
    except ClientError as e:
        error_msg = f"S3 download failed: {e.response['Error']['Message']}"
        log_audit_event(audit_id, document_id, 'S3_DOWNLOAD_FAILED', {'error': error_msg})
        raise Exception(error_msg)

def smart_classify_document(image_base64, document_id, audit_id):
    """
    Two-stage document classification for cost optimization
    """
    
    # Stage 1: Fast & cheap classification with Haiku
    log_audit_event(audit_id, document_id, 'CLASSIFICATION_STAGE1_STARTED', {
        'model': CLASSIFICATION_MODELS['cheap'],
        'strategy': 'cost_optimized_classification'
    })
    
    stage1_result = classify_with_bedrock(
        image_base64, 
        CLASSIFIER_PROMPT,
        CLASSIFICATION_MODELS['cheap'],
        document_id,
        audit_id
    )
    
    # Check if we need to escalate to expensive model
    if stage1_result['confidence'] >= CLASSIFICATION_CONFIDENCE_THRESHOLD:
        log_audit_event(audit_id, document_id, 'CLASSIFICATION_COMPLETED', {
            'stage': 1,
            'model_used': CLASSIFICATION_MODELS['cheap'],
            'confidence': stage1_result['confidence'],
            'document_type': stage1_result['document_type'],
            'cost_optimization': 'used_cheap_model_successfully'
        })
        
        stage1_result['model_used'] = CLASSIFICATION_MODELS['cheap']
        stage1_result['escalated'] = False
        return stage1_result
    
    # Stage 2: Escalate to expensive model for uncertain cases
    log_audit_event(audit_id, document_id, 'CLASSIFICATION_ESCALATED', {
        'stage1_confidence': stage1_result['confidence'],
        'threshold': CLASSIFICATION_CONFIDENCE_THRESHOLD,
        'escalation_model': CLASSIFICATION_MODELS['expensive']
    })
    
    stage2_result = classify_with_bedrock(
        image_base64, 
        CLASSIFIER_PROMPT,
        CLASSIFICATION_MODELS['expensive'],
        document_id,
        audit_id
    )
    
    log_audit_event(audit_id, document_id, 'CLASSIFICATION_COMPLETED', {
        'stage': 2,
        'model_used': CLASSIFICATION_MODELS['expensive'],
        'final_confidence': stage2_result['confidence'],
        'document_type': stage2_result['document_type'],
        'cost_optimization': 'escalated_for_accuracy'
    })
    
    stage2_result['model_used'] = CLASSIFICATION_MODELS['expensive']
    stage2_result['escalated'] = True
    return stage2_result

def classify_with_bedrock(image_base64, prompt_content, model_id, document_id, audit_id):
    """
    Classify document using Bedrock
    """
    
    try:
        log_audit_event(audit_id, document_id, 'BEDROCK_CLASSIFICATION_STARTED', {
            'model_id': model_id,
            'prompt_length': len(prompt_content)
        })
        
        # Use Bedrock Converse API
        response = bedrock.converse(
            modelId=model_id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "image": {
                                "format": "png",  # Adjust based on your image format
                                "source": {"bytes": base64.b64decode(image_base64)}
                            }
                        },
                        {
                            "text": prompt_content
                        }
                    ]
                }
            ],
            inferenceConfig={
                "maxTokens": 1000,
                "temperature": 0.1  # Low temperature for consistent classification
            }
        )
        
        # Parse classification response
        response_text = response['output']['message']['content'][0]['text']
        
        log_audit_event(audit_id, document_id, 'BEDROCK_CLASSIFICATION_COMPLETED', {
            'response_length': len(response_text),
            'input_tokens': response['usage']['inputTokens'],
            'output_tokens': response['usage']['outputTokens']
        })
        
        print(f"Classification response: {response_text[:200]}...")
        
        # Parse JSON response
        try:
            classification_data = json.loads(response_text)
            return {
                'document_type': classification_data.get('document_type', 'OTHER'),
                'confidence': classification_data.get('confidence', 0.5),
                'complexity_score': classification_data.get('complexity_score', 0.5),
                'raw_response': response_text
            }
        except json.JSONDecodeError:
            print("Classification returned non-JSON response")
            return {
                'document_type': 'OTHER',
                'confidence': 0.3,
                'complexity_score': 0.5,
                'raw_response': response_text
            }
            
    except ClientError as e:
        error_msg = f"Bedrock classification failed: {e.response['Error']['Message']}"
        log_audit_event(audit_id, document_id, 'BEDROCK_CLASSIFICATION_FAILED', {'error': error_msg})
        raise Exception(error_msg)

def extract_with_specialized_prompt(image_base64, document_type, document_id, audit_id):
    """
    Extract document fields using specialized prompts based on document type
    """
    
    # Get the appropriate extraction prompt
    extraction_prompt = get_extraction_prompt(document_type)
    
    try:
        log_audit_event(audit_id, document_id, 'BEDROCK_EXTRACTION_STARTED', {
            'document_type': document_type,
            'model_id': EXTRACTION_MODEL,
            'prompt_length': len(extraction_prompt)
        })
        
        # Use Bedrock for extraction
        response = bedrock.converse(
            modelId=EXTRACTION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "image": {
                                "format": "png",  # Adjust based on your image format
                                "source": {"bytes": base64.b64decode(image_base64)}
                            }
                        },
                        {
                            "text": extraction_prompt
                        }
                    ]
                }
            ],
            inferenceConfig={
                "maxTokens": 2000,
                "temperature": 0.0  # Deterministic extraction
            }
        )
        
        response_text = response['output']['message']['content'][0]['text']
        
        log_audit_event(audit_id, document_id, 'BEDROCK_EXTRACTION_COMPLETED', {
            'response_length': len(response_text),
            'input_tokens': response['usage']['inputTokens'],
            'output_tokens': response['usage']['outputTokens']
        })
        
        print(f"Extraction response: {response_text[:200]}...")
        
        # Parse extraction response
        try:
            extraction_data = json.loads(response_text)
            return {
                'extracted_fields': extraction_data.get('extracted_fields', {}),
                'confidence': extraction_data.get('confidence', 0.5),
                'extraction_notes': extraction_data.get('extraction_notes', ''),
                'raw_response': response_text
            }
        except json.JSONDecodeError:
            print("Extraction returned non-JSON response")
            return {
                'extracted_fields': {},
                'confidence': 0.3,
                'extraction_notes': 'Response was not valid JSON',
                'raw_response': response_text
            }
            
    except ClientError as e:
        error_msg = f"Bedrock extraction failed: {e.response['Error']['Message']}"
        log_audit_event(audit_id, document_id, 'BEDROCK_EXTRACTION_FAILED', {'error': error_msg})
        raise Exception(error_msg)

def get_extraction_prompt(document_type):
    """
    Get the appropriate extraction prompt based on document type
    """
    
    # Map document types to their specialized prompts
    prompt_mapping = {
        'LETTER_OF_CREDIT': LETTER_OF_CREDIT_PROMPT,
        # Add more document types as needed
        # 'COMMERCIAL_INVOICE': COMMERCIAL_INVOICE_PROMPT,
        # 'BILL_OF_LADING': BILL_OF_LADING_PROMPT,
    }
    
    # Return specialized prompt or generic fallback
    return prompt_mapping.get(document_type, LETTER_OF_CREDIT_PROMPT)  # Default to LC for demo

def calculate_processing_costs(classification_result, extraction_result):
    """
    Estimate processing costs for business intelligence
    """
    
    # Rough cost estimates (actual costs vary by region and time)
    model_costs = {
        'anthropic.claude-3-haiku-20240307-v1:0': {'input': 0.00025, 'output': 0.00125},
        'anthropic.claude-3-sonnet-20240229-v1:0': {'input': 0.003, 'output': 0.015}
    }
    
    classification_model = classification_result.get('model_used', CLASSIFICATION_MODELS['cheap'])
    
    # Estimate tokens (rough approximation for business intelligence)
    estimated_input_tokens = 1000  # Typical image + prompt
    estimated_output_tokens = 200   # Typical classification + extraction response
    
    classification_cost = (
        estimated_input_tokens / 1000 * model_costs[classification_model]['input'] +
        estimated_output_tokens / 1000 * model_costs[classification_model]['output']
    )
    
    extraction_cost = (
        estimated_input_tokens / 1000 * model_costs[EXTRACTION_MODEL]['input'] +
        estimated_output_tokens / 1000 * model_costs[EXTRACTION_MODEL]['output']
    )
    
    return {
        'classification_cost_estimate': round(classification_cost, 6),
        'extraction_cost_estimate': round(extraction_cost, 6),
        'total_estimated_cost': round(classification_cost + extraction_cost, 6),
        'cost_optimization_benefit': 'Used cheap classification model' if not classification_result.get('escalated', False) else 'Escalated for accuracy'
    }

def assess_image_quality(image_data):
    """
    Simple image quality assessment for training metadata
    """
    
    # Simple heuristics for image quality (can be enhanced with CV libraries)
    file_size = len(image_data)
    
    if file_size < 50000:  # < 50KB
        return 0.3  # Likely low quality
    elif file_size > 500000:  # > 500KB
        return 0.9  # Likely high quality
    else:
        return 0.6  # Medium quality
    
def store_document_results_enhanced(document_id, bucket, key, result, audit_id):
    """
    Store enhanced results with training metadata
    """
    
    try:
        documents_table = dynamodb.Table(DOCUMENTS_TABLE)
        
        timestamp = datetime.now(timezone.utc).isoformat()
        
        document_record = {
            'document_id': document_id,
            'created_at': timestamp,
            'updated_at': timestamp,
            'status': 'PROCESSED',
            'document_type': result.get('document_type', 'OTHER'),
            'source_bucket': bucket,
            'source_key': key,
            'classification_confidence': result.get('classification_confidence', 0.0),
            'classification_model_used': result.get('classification_model_used'),
            'classification_escalated': result.get('classification_escalated', False),
            'extraction_confidence': result.get('extraction_confidence', 0.0),
            'extracted_fields': result.get('extracted_fields', {}),
            'extraction_notes': result.get('extraction_notes', ''),
            'processing_costs': result.get('processing_costs', {}),
            'training_metadata': result.get('training_metadata', {}),
            'processing_metadata': {
                'processor': 'enhanced-claude-vision-lambda',
                'processing_strategy': 'two_stage_with_embedded_prompts',
                'audit_id': audit_id
            },
            # TTL: 90 days from now
            'ttl': int((datetime.now(timezone.utc).timestamp()) + (90 * 24 * 60 * 60))
        }
        
        documents_table.put_item(Item=document_record)
        
        log_audit_event(audit_id, document_id, 'ENHANCED_RESULTS_STORED', {
            'table': DOCUMENTS_TABLE,
            'record_size': len(json.dumps(document_record, default=str)),
            'training_metadata_included': True
        })
        
        print(f"Stored enhanced results for document {document_id}")
        
    except ClientError as e:
        error_msg = f"DynamoDB storage failed: {e.response['Error']['Message']}"
        log_audit_event(audit_id, document_id, 'STORAGE_FAILED', {'error': error_msg})
        raise Exception(error_msg)

def log_audit_event(audit_id, document_id, event_type, event_data):
    """
    Enhanced audit logging with cost and performance metadata
    """
    
    try:
        audit_table = dynamodb.Table(AUDIT_TABLE)
        
        timestamp = datetime.now(timezone.utc).isoformat()
        
        audit_record = {
            'audit_id': f"{audit_id}#{timestamp}",
            'timestamp': timestamp,
            'document_id': document_id,
            'agent_name': 'enhanced-claude-vision-lambda',
            'event_type': event_type,
            'event_data': event_data,
            # TTL: 1 year retention for audit records
            'ttl': int((datetime.now(timezone.utc).timestamp()) + (365 * 24 * 60 * 60))
        }
        
        audit_table.put_item(Item=audit_record)
        print(f"Audit logged: {event_type} for {document_id}")
        
    except Exception as e:
        # Don't fail the main process if audit logging fails
        print(f"Audit logging failed: {str(e)}")
        pass