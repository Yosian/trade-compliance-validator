import json
import boto3
from urllib.parse import unquote_plus

# Initialize AWS clients
sqs = boto3.client('sqs')

# Hardcoded queue URLs for demo (replace account/region as needed)
VISION_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/864899848062/tdv-dev-vision-processing'
DOC_READER_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/864899848062/tdv-dev-doc-reader'
PDF_CONVERTER_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/864899848062/tdv-dev-pdf-converter'

def lambda_handler(event, context):
    """
    File Selector Lambda - Routes documents to appropriate processors
    
    Input: S3 event or direct invocation with file details
    Output: Routes to Vision, Doc Reader, or PDF Converter
    """
    
    try:
        # Parse input - handle both S3 events and direct invocations
        if 'Records' in event:
            # S3 event trigger
            record = event['Records'][0]
            bucket = record['s3']['bucket']['name']
            key = unquote_plus(record['s3']['object']['key'])
        else:
            # Direct invocation
            bucket = event['bucket']
            key = event['key']
        
        # Extract file extension and determine routing
        file_extension = key.lower().split('.')[-1]
        routing_decision = determine_routing(file_extension, key)
        
        # Create message payload
        message = {
            'bucket': bucket,
            'key': key,
            'file_extension': file_extension,
            'routing_decision': routing_decision,
            'timestamp': context.aws_request_id
        }
        
        # Route to appropriate queue
        queue_url = get_target_queue(routing_decision)
        
        if queue_url:
            response = sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message)
            )
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': f'File routed to {routing_decision}',
                    'bucket': bucket,
                    'key': key,
                    'messageId': response['MessageId']
                })
            }
        else:
            raise ValueError(f"No queue configured for routing: {routing_decision}")
            
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to route file'
            })
        }

def determine_routing(file_extension, key):
    """
    Determine which processor should handle this file
    
    Returns: 'vision', 'doc_reader', 'pdf_converter', or 'unsupported'
    """
    
    # Image files go directly to vision
    if file_extension in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff']:
        return 'vision'
    
    # PDF files need conversion to images first
    elif file_extension == 'pdf':
        return 'pdf_converter'
    
    # Text-based documents go to doc reader
    elif file_extension in ['txt', 'doc', 'docx', 'rtf']:
        return 'doc_reader'
    
    # Everything else is unsupported for now
    else:
        return 'unsupported'

def get_target_queue(routing_decision):
    """
    Map routing decision to SQS queue URL
    """
    
    queue_mapping = {
        'vision': VISION_QUEUE_URL,
        'doc_reader': DOC_READER_QUEUE_URL,
        'pdf_converter': PDF_CONVERTER_QUEUE_URL
    }
    
    return queue_mapping.get(routing_decision)