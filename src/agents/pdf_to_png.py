import json
import boto3
import fitz  # PyMuPDF
import uuid
import logging
from datetime import datetime, timezone
from io import BytesIO
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AWS clients
s3 = boto3.client('s3')
sqs = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')

# Configuration (would come from environment variables in production)
VISION_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/864899848062/tdv-dev-vision-processing'
AUDIT_TABLE = 'tdv-dev-audit-trail-864899848062-us-east-1'


def convert_pdf_to_png(bucket, key, audit_id):
    """
    Convert PDF to PNG images using PyMuPDF
    
    Returns: List of S3 keys for generated PNG images
    """
    
    try:
        # Download PDF from S3
        log_audit_event(audit_id, key, 'S3_PDF_DOWNLOAD_STARTED', {'bucket': bucket, 'key': key})
        
        response = s3.get_object(Bucket=bucket, Key=key)
        pdf_data = response['Body'].read()
        
        log_audit_event(audit_id, key, 'S3_PDF_DOWNLOAD_COMPLETED', {
            'pdf_size_bytes': len(pdf_data)
        })
        
        # Open PDF with PyMuPDF
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        
        log_audit_event(audit_id, key, 'PDF_OPENED', {
            'page_count': len(doc),
            'pdf_title': doc.metadata.get('title', ''),
            'pdf_author': doc.metadata.get('author', '')
        })
        
        png_keys = []
        
        # Convert each page to PNG
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Render page to image (high DPI for better OCR results)
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for 144 DPI
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PNG bytes
            png_data = pix.tobytes("png")
            
            # Generate PNG key (preserve path structure, add page number)
            base_key = key.rsplit('.', 1)[0]  # Remove .pdf extension
            png_key = f"{base_key}_page_{page_num + 1:03d}.png"
            
            # Upload PNG to S3
            s3.put_object(
                Bucket=bucket,
                Key=png_key,
                Body=png_data,
                ContentType='image/png',
                Metadata={
                    'source_pdf': key,
                    'page_number': str(page_num + 1),
                    'total_pages': str(len(doc)),
                    'conversion_timestamp': datetime.now(timezone.utc).isoformat(),
                    'dpi': '144'
                }
            )
            
            png_keys.append(png_key)
            
            log_audit_event(audit_id, key, 'PAGE_CONVERTED', {
                'page_number': page_num + 1,
                'png_key': png_key,
                'png_size_bytes': len(png_data),
                'image_dimensions': f"{pix.width}x{pix.height}"
            })
            
            logger.info(f"Converted page {page_num + 1}/{len(doc)} to {png_key}")
        
        doc.close()
        
        log_audit_event(audit_id, key, 'PDF_PROCESSING_COMPLETED', {
            'total_pages_converted': len(png_keys),
            'generated_images': png_keys
        })
        
        return png_keys
        
    except Exception as e:
        error_msg = f"PDF conversion failed: {str(e)}"
        log_audit_event(audit_id, key, 'PDF_CONVERSION_ERROR', {'error': error_msg})
        raise Exception(error_msg)

def forward_to_vision_processing(bucket, png_key, original_pdf_key, audit_id):
    """
    Forward converted PNG image to vision processing queue
    """
    
    try:
        # Create message for vision processing
        message = {
            'bucket': bucket,
            'key': png_key,
            'file_extension': 'png',
            'routing_decision': 'vision',
            'source_document': {
                'type': 'pdf_conversion',
                'original_key': original_pdf_key,
                'conversion_audit_id': audit_id
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Send to vision processing queue
        response = sqs.send_message(
            QueueUrl=VISION_QUEUE_URL,
            MessageBody=json.dumps(message)
        )
        
        log_audit_event(audit_id, png_key, 'FORWARDED_TO_VISION', {
            'queue_url': VISION_QUEUE_URL,
            'message_id': response['MessageId'],
            'original_pdf': original_pdf_key
        })
        
        logger.info(f"Forwarded {png_key} to vision processing (MessageId: {response['MessageId']})")
        
    except Exception as e:
        error_msg = f"Failed to forward to vision processing: {str(e)}"
        log_audit_event(audit_id, png_key, 'VISION_FORWARD_FAILED', {'error': error_msg})
        raise Exception(error_msg)

def log_audit_event(audit_id, document_key, event_type, event_data):
    """
    Log audit events for compliance and debugging
    """
    
    try:
        audit_table = dynamodb.Table(AUDIT_TABLE)
        
        timestamp = datetime.now(timezone.utc).isoformat()
        
        audit_record = {
            'audit_id': f"{audit_id}#{timestamp}",
            'timestamp': timestamp,
            'document_id': document_key,
            'agent_name': 'pdf-to-png-converter',
            'event_type': event_type,
            'event_data': event_data,
            # TTL: 1 year retention for audit records
            'ttl': int((datetime.now(timezone.utc).timestamp()) + (365 * 24 * 60 * 60))
        }
        
        audit_table.put_item(Item=audit_record)
        logger.info(f"Audit logged: {event_type} for {document_key}")
        
    except Exception as e:
        # Don't fail the main process if audit logging fails
        logger.warning(f"Audit logging failed: {str(e)}")
        pass

def lambda_handler(event, context):
    """
    PDF to PNG Conversion Lambda
    
    Converts PDF documents to PNG images and forwards to vision processing
    Uses PyMuPDF layer for efficient PDF processing
    """
    
    audit_id = str(uuid.uuid4())
    
    try:
        # Process each SQS message
        for record in event['Records']:
            message_body = json.loads(record['body'])
            
            # Extract file information
            bucket = message_body['bucket']
            key = message_body['key']
            routing_decision = message_body.get('routing_decision', 'pdf_converter')
            
            logger.info(f"Processing PDF: {key} from bucket: {bucket}")
            
            # Log processing start
            log_audit_event(audit_id, key, 'PDF_CONVERSION_STARTED', {
                'bucket': bucket,
                'key': key,
                'lambda_request_id': context.aws_request_id
            })
            
            # Convert PDF to PNG images
            png_keys = convert_pdf_to_png(bucket, key, audit_id)
            
            # Forward each PNG to vision processing
            for png_key in png_keys:
                forward_to_vision_processing(bucket, png_key, key, audit_id)
            
            # Log successful completion
            log_audit_event(audit_id, key, 'PDF_CONVERSION_COMPLETED', {
                'pages_converted': len(png_keys),
                'generated_images': png_keys
            })
            
            logger.info(f"Successfully converted PDF {key} to {len(png_keys)} PNG images")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'PDF conversion completed successfully',
                'audit_id': audit_id
            })
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error converting PDF: {error_msg}")
        
        log_audit_event(audit_id, key if 'key' in locals() else 'unknown', 'PDF_CONVERSION_FAILED', {
            'error': error_msg,
            'error_type': type(e).__name__
        })
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': error_msg,
                'audit_id': audit_id
            })
        }
