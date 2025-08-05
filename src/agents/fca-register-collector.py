import json
import boto3
import requests
import uuid
import os
from datetime import datetime, timezone
from decimal import Decimal
import logging
from urllib.parse import quote_plus
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

# Environment variables (would be set in Lambda configuration)
CACHE_TABLE_NAME = os.environ.get('CACHE_TABLE_NAME', 'tdv-dev-regulatory-api-cache-864899848062-us-east-1')
REGULATORY_BUCKET = os.environ.get('REGULATORY_BUCKET', 'tdv-dev-regulatory-data-864899848062-us-east-1')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')

# FCA API Configuration
FCA_BASE_URL = "https://register.fca.org.uk/services/V0.1"
CACHE_TTL_HOURS = 24  # Refresh daily for regulatory data

def lambda_handler(event, context):
    """
    FCA Register Collector Lambda
    
    Collects authorized financial services firms data from FCA Register API
    Stores results in DynamoDB cache table for trade finance bank validation
    
    Event types supported:
    - Scheduled (EventBridge/CloudWatch Events)
    - Manual invocation with bank search parameters
    - API Gateway trigger for real-time bank validation
    """
    
    try:
        # Parse event type and parameters
        event_type = event.get('source', 'manual')
        search_params = event.get('search_params', {})
        
        logger.info(f"FCA Register Collector started - Event type: {event_type}")
        
        # Initialize DynamoDB table
        cache_table = dynamodb.Table(CACHE_TABLE_NAME)
        
        if event_type == 'aws.events':
            # Scheduled execution - collect all trade finance related data
            results = collect_all_trade_finance_firms(cache_table)
        elif 'bank_name' in search_params:
            # Specific bank validation request
            results = validate_specific_bank(cache_table, search_params['bank_name'])
        else:
            # Default: collect key trade finance institutions
            results = collect_key_trade_finance_firms(cache_table)
        
        # Store aggregated results in S3 for knowledge base
        s3_key = store_aggregated_results_in_s3(results)
        
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'FCA data collection completed successfully',
                'results_summary': {
                    'firms_processed': results.get('total_firms', 0),
                    'cache_updates': results.get('cache_updates', 0),
                    'api_calls_made': results.get('api_calls', 0),
                    's3_location': s3_key
                },
                'collection_timestamp': datetime.now(timezone.utc).isoformat(),
                'lambda_request_id': context.aws_request_id
            })
        }
        
        logger.info(f"Collection completed successfully: {results}")
        return response
        
    except Exception as e:
        error_msg = f"FCA data collection failed: {str(e)}"
        logger.error(error_msg)
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': error_msg,
                'lambda_request_id': context.aws_request_id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        }

def collect_all_trade_finance_firms(cache_table):
    """
    Collect comprehensive trade finance related firms data
    Used for scheduled/batch collections
    """
    
    # Trade finance related search terms for FCA register
    trade_finance_searches = [
        'documentary credit',
        'letter of credit', 
        'international banking',
        'correspondent banking',
        'trade finance',
        'export finance',
        'import finance',
        'commercial banking'
    ]
    
    results = {
        'total_firms': 0,
        'cache_updates': 0,
        'api_calls': 0,
        'search_results': {}
    }
    
    for search_term in trade_finance_searches:
        try:
            logger.info(f"Searching FCA register for: {search_term}")
            
            # Check if we need to refresh this search
            if should_refresh_cache('FCA_SEARCH', search_term, cache_table):
                
                firms_data = search_fca_register(search_term)
                results['api_calls'] += 1
                
                if firms_data:
                    # Store in cache
                    cache_key = f"search_{search_term.replace(' ', '_')}"
                    store_in_cache(cache_table, 'FCA_SEARCH', cache_key, firms_data)
                    results['cache_updates'] += 1
                    
                    # Process individual firms
                    processed_firms = process_firms_for_trade_finance(firms_data, search_term)
                    results['search_results'][search_term] = processed_firms
                    results['total_firms'] += len(processed_firms)
                    
                    logger.info(f"Found {len(processed_firms)} firms for '{search_term}'")
                else:
                    logger.warning(f"No results found for '{search_term}'")
            else:
                logger.info(f"Using cached data for '{search_term}'")
                # Load from cache for aggregation
                cached_data = load_from_cache(cache_table, 'FCA_SEARCH', f"search_{search_term.replace(' ', '_')}")
                if cached_data:
                    processed_firms = process_firms_for_trade_finance(cached_data, search_term)
                    results['search_results'][search_term] = processed_firms
                    results['total_firms'] += len(processed_firms)
                    
        except Exception as e:
            logger.error(f"Failed to process search term '{search_term}': {str(e)}")
            continue
    
    return results

def validate_specific_bank(cache_table, bank_name):
    """
    Validate a specific bank for Letter of Credit processing
    Used for real-time bank validation during LC processing
    """
    
    logger.info(f"Validating specific bank: {bank_name}")
    
    try:
        # Check cache first
        cache_key = f"bank_{bank_name.replace(' ', '_').lower()}"
        
        if should_refresh_cache('FCA_BANK_VALIDATION', cache_key, cache_table):
            
            # Search FCA register for this specific bank
            bank_data = search_fca_register_by_name(bank_name)
            
            if bank_data:
                # Store in cache
                store_in_cache(cache_table, 'FCA_BANK_VALIDATION', cache_key, bank_data)
                
                # Process for trade finance validation
                validation_result = process_bank_for_lc_validation(bank_data, bank_name)
                
                return {
                    'total_firms': 1 if validation_result['is_authorized'] else 0,
                    'cache_updates': 1,
                    'api_calls': 1,
                    'bank_validation': validation_result
                }
            else:
                # Bank not found in FCA register
                validation_result = {
                    'bank_name': bank_name,
                    'is_authorized': False,
                    'fca_status': 'NOT_FOUND',
                    'risk_level': 'HIGH',
                    'validation_timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                # Cache negative result too (with shorter TTL)
                store_in_cache(cache_table, 'FCA_BANK_VALIDATION', cache_key, validation_result, ttl_hours=6)
                
                return {
                    'total_firms': 0,
                    'cache_updates': 1,
                    'api_calls': 1,
                    'bank_validation': validation_result
                }
        else:
            # Use cached validation result
            cached_result = load_from_cache(cache_table, 'FCA_BANK_VALIDATION', cache_key)
            return {
                'total_firms': 1 if cached_result and cached_result.get('is_authorized') else 0,
                'cache_updates': 0,
                'api_calls': 0,
                'bank_validation': cached_result
            }
            
    except Exception as e:
        logger.error(f"Bank validation failed for '{bank_name}': {str(e)}")
        raise

def collect_key_trade_finance_firms(cache_table):
    """
    Collect data for key trade finance institutions
    Focused collection for most common LC issuing banks
    """
    
    # Major UK and international banks commonly involved in trade finance
    key_banks = [
        'HSBC Bank plc',
        'Barclays Bank PLC',
        'Lloyds Bank plc', 
        'NatWest Bank plc',
        'Standard Chartered Bank',
        'Santander UK plc',
        'Deutsche Bank AG',
        'BNP Paribas',
        'Citibank N.A.',
        'JPMorgan Chase Bank'
    ]
    
    results = {
        'total_firms': 0,
        'cache_updates': 0,
        'api_calls': 0,
        'key_banks': {}
    }
    
    for bank_name in key_banks:
        try:
            bank_result = validate_specific_bank(cache_table, bank_name)
            results['key_banks'][bank_name] = bank_result.get('bank_validation', {})
            results['total_firms'] += bank_result.get('total_firms', 0)
            results['cache_updates'] += bank_result.get('cache_updates', 0)
            results['api_calls'] += bank_result.get('api_calls', 0)
            
        except Exception as e:
            logger.error(f"Failed to validate key bank '{bank_name}': {str(e)}")
            continue
    
    return results

def search_fca_register(search_term):
    """
    Search FCA register using their API
    """
    
    try:
        # FCA Register search endpoint
        search_url = f"{FCA_BASE_URL}/search"
        
        params = {
            'query': search_term,
            'type': 'firm',
            'status': 'authorised',
            'limit': 100  # Adjust based on API limits
        }
        
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'TradeDocumentValidator/1.0'
        }
        
        response = requests.get(search_url, params=params, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"FCA API search successful for '{search_term}': {len(data.get('data', []))} results")
            return data
        elif response.status_code == 429:
            logger.warning(f"FCA API rate limit hit for '{search_term}'")
            return None
        else:
            logger.error(f"FCA API search failed for '{search_term}': {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"FCA API request failed for '{search_term}': {str(e)}")
        return None

def search_fca_register_by_name(bank_name):
    """
    Search for a specific bank by name in FCA register
    """
    
    try:
        # Try exact name first, then variations
        search_variations = [
            bank_name,
            bank_name.replace(' plc', '').replace(' PLC', ''),
            bank_name.replace(' Bank', '').replace(' bank', ''),
            bank_name.split()[0]  # First word only
        ]
        
        for search_name in search_variations:
            logger.info(f"Searching FCA register for bank variation: '{search_name}'")
            
            result = search_fca_register(search_name)
            if result and result.get('data'):
                # Filter results to find exact or close matches
                matching_firms = []
                for firm in result['data']:
                    firm_name = firm.get('Name', '').lower()
                    if any(name.lower() in firm_name for name in search_variations):
                        matching_firms.append(firm)
                
                if matching_firms:
                    logger.info(f"Found {len(matching_firms)} matching firms for '{bank_name}'")
                    return {'data': matching_firms, 'search_term': search_name}
        
        logger.warning(f"No matching firms found for '{bank_name}' in FCA register")
        return None
        
    except Exception as e:
        logger.error(f"Bank name search failed for '{bank_name}': {str(e)}")
        return None

def process_firms_for_trade_finance(firms_data, search_term):
    """
    Process FCA firms data to extract trade finance relevant information
    """
    
    processed_firms = []
    
    if not firms_data or 'data' not in firms_data:
        return processed_firms
    
    for firm in firms_data['data']:
        try:
            processed_firm = {
                'firm_reference_number': firm.get('FirmReferenceNumber', ''),
                'firm_name': firm.get('Name', ''),
                'status': firm.get('Status', ''),
                'authorization_date': firm.get('AuthorisationDate', ''),
                'permissions': extract_trade_finance_permissions(firm),
                'address': extract_firm_address(firm),
                'trade_finance_relevance': calculate_trade_finance_relevance(firm, search_term),
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'source_search': search_term
            }
            
            # Only include firms with trade finance relevance
            if processed_firm['trade_finance_relevance'] > 0:
                processed_firms.append(processed_firm)
                
        except Exception as e:
            logger.warning(f"Failed to process firm: {str(e)}")
            continue
    
    return processed_firms

def process_bank_for_lc_validation(bank_data, bank_name):
    """
    Process bank data specifically for Letter of Credit validation
    """
    
    if not bank_data or 'data' not in bank_data or not bank_data['data']:
        return {
            'bank_name': bank_name,
            'is_authorized': False,
            'fca_status': 'NOT_FOUND',
            'risk_level': 'HIGH',
            'validation_timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    # Take the best matching firm
    firm = bank_data['data'][0]
    
    try:
        permissions = extract_trade_finance_permissions(firm)
        
        # Check if bank has relevant permissions for trade finance
        has_banking_permissions = any(
            perm.lower() in ['banking', 'deposit taking', 'credit', 'payment services'] 
            for perm in permissions
        )
        
        trade_finance_score = calculate_trade_finance_relevance(firm, bank_name)
        
        # Determine risk level based on authorization and permissions
        if firm.get('Status', '').lower() == 'authorised' and has_banking_permissions:
            risk_level = 'LOW' if trade_finance_score > 5 else 'MEDIUM'
            is_authorized = True
        else:
            risk_level = 'HIGH'
            is_authorized = False
        
        return {
            'bank_name': bank_name,
            'fca_firm_name': firm.get('Name', ''),
            'firm_reference_number': firm.get('FirmReferenceNumber', ''),
            'is_authorized': is_authorized,
            'fca_status': firm.get('Status', ''),
            'authorization_date': firm.get('AuthorisationDate', ''),
            'permissions': permissions,
            'trade_finance_score': trade_finance_score,
            'risk_level': risk_level,
            'validation_timestamp': datetime.now(timezone.utc).isoformat(),
            'address': extract_firm_address(firm)
        }
        
    except Exception as e:
        logger.error(f"Failed to process bank data for '{bank_name}': {str(e)}")
        return {
            'bank_name': bank_name,
            'is_authorized': False,
            'fca_status': 'PROCESSING_ERROR',
            'risk_level': 'HIGH',
            'error': str(e),
            'validation_timestamp': datetime.now(timezone.utc).isoformat()
        }

def extract_trade_finance_permissions(firm):
    """
    Extract trade finance relevant permissions from FCA firm data
    """
    
    permissions = []
    
    # Look for permissions in various fields
    perm_fields = ['Permissions', 'Activities', 'BusinessTypes']
    
    for field in perm_fields:
        if field in firm and firm[field]:
            if isinstance(firm[field], list):
                permissions.extend([str(p) for p in firm[field]])
            else:
                permissions.append(str(firm[field]))
    
    return list(set(permissions))  # Remove duplicates

def extract_firm_address(firm):
    """
    Extract firm address information
    """
    
    address_info = {}
    
    address_fields = ['Address', 'RegisteredAddress', 'BusinessAddress']
    
    for field in address_fields:
        if field in firm and firm[field]:
            address_info = firm[field]
            break
    
    return address_info

def calculate_trade_finance_relevance(firm, search_context):
    """
    Calculate how relevant this firm is for trade finance operations
    Used for filtering and risk assessment
    """
    
    relevance_score = 0
    
    firm_name = firm.get('Name', '').lower()
    permissions = extract_trade_finance_permissions(firm)
    
    # Name-based scoring
    trade_finance_keywords = [
        'bank', 'banking', 'international', 'trade', 'export', 'import', 
        'commercial', 'correspondent', 'hsbc', 'barclays', 'lloyds', 
        'natwest', 'standard chartered', 'santander'
    ]
    
    for keyword in trade_finance_keywords:
        if keyword in firm_name:
            relevance_score += 2
    
    # Permission-based scoring
    trade_permissions = [
        'banking', 'deposit taking', 'credit', 'payment services',
        'correspondent banking', 'trade finance', 'documentary credit'
    ]
    
    for perm in permissions:
        perm_lower = perm.lower()
        for trade_perm in trade_permissions:
            if trade_perm in perm_lower:
                relevance_score += 3
                break
    
    # Search context relevance
    if search_context and any(word in firm_name for word in search_context.lower().split()):
        relevance_score += 1
    
    return relevance_score

def should_refresh_cache(api_source, cache_key, cache_table):
    """
    Check if cached data needs refreshing based on TTL and data source
    """
    
    try:
        response = cache_table.get_item(
            Key={
                'api_source': api_source,
                'cache_key': cache_key
            }
        )
        
        if 'Item' not in response:
            return True  # No cache, need fresh data
        
        item = response['Item']
        last_updated_str = item.get('last_updated', '')
        
        if not last_updated_str:
            return True  # Invalid cache entry
        
        last_updated = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
        age_hours = (datetime.now(timezone.utc) - last_updated).total_seconds() / 3600
        
        # Different refresh rates for different data types
        ttl_hours = {
            'FCA_SEARCH': 24,           # Daily refresh for general searches
            'FCA_BANK_VALIDATION': 12,  # Twice daily for specific bank validations
            'FCA_KEY_BANKS': 6          # Every 6 hours for key banking institutions
        }.get(api_source, CACHE_TTL_HOURS)
        
        return age_hours > ttl_hours
        
    except Exception as e:
        logger.warning(f"Cache check failed for {api_source}:{cache_key}: {str(e)}")
        return True  # Default to refresh on error

def load_from_cache(cache_table, api_source, cache_key):
    """
    Load data from DynamoDB cache
    """
    
    try:
        response = cache_table.get_item(
            Key={
                'api_source': api_source,
                'cache_key': cache_key
            }
        )
        
        if 'Item' in response:
            cached_data = response['Item'].get('data')
            if isinstance(cached_data, str):
                return json.loads(cached_data)
            return cached_data
        
        return None
        
    except Exception as e:
        logger.error(f"Failed to load from cache {api_source}:{cache_key}: {str(e)}")
        return None

def store_in_cache(cache_table, api_source, cache_key, data, ttl_hours=CACHE_TTL_HOURS):
    """
    Store data in DynamoDB cache with TTL
    """
    
    try:
        cache_record = {
            'api_source': api_source,
            'cache_key': cache_key,
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'data': json.dumps(data, default=str) if not isinstance(data, str) else data,
            'data_size': len(str(data)),
            'ttl': int((datetime.now(timezone.utc).timestamp()) + (ttl_hours * 3600))
        }
        
        # Convert floats to Decimal for DynamoDB compatibility
        cache_record = convert_floats_to_decimal(cache_record)
        
        cache_table.put_item(Item=cache_record)
        logger.info(f"Stored in cache: {api_source}:{cache_key} ({cache_record['data_size']} bytes)")
        
    except Exception as e:
        logger.error(f"Failed to store in cache {api_source}:{cache_key}: {str(e)}")
        raise

def store_aggregated_results_in_s3(results):
    """
    Store aggregated results in S3 for knowledge base consumption
    """
    
    try:
        # Create comprehensive dataset for RAG knowledge base
        knowledge_base_data = {
            'collection_metadata': {
                'collection_timestamp': datetime.now(timezone.utc).isoformat(),
                'source': 'FCA_Register_API',
                'purpose': 'trade_finance_bank_validation',
                'total_firms': results.get('total_firms', 0)
            },
            'authorized_banks': [],
            'search_summaries': []
        }
        
        # Process search results into knowledge base format
        if 'search_results' in results:
            for search_term, firms in results['search_results'].items():
                search_summary = {
                    'search_term': search_term,
                    'firms_found': len(firms),
                    'high_relevance_firms': [f for f in firms if f.get('trade_finance_relevance', 0) > 5]
                }
                knowledge_base_data['search_summaries'].append(search_summary)
                knowledge_base_data['authorized_banks'].extend(firms)
        
        # Process key bank validations
        if 'key_banks' in results:
            for bank_name, validation in results['key_banks'].items():
                if validation.get('is_authorized'):
                    bank_record = {
                        'bank_name': bank_name,
                        'fca_firm_name': validation.get('fca_firm_name', ''),
                        'firm_reference_number': validation.get('firm_reference_number', ''),
                        'fca_status': validation.get('fca_status', ''),
                        'trade_finance_score': validation.get('trade_finance_score', 0),
                        'risk_level': validation.get('risk_level', 'UNKNOWN'),
                        'permissions': validation.get('permissions', []),
                        'validation_timestamp': validation.get('validation_timestamp', ''),
                        'source_type': 'key_bank_validation'
                    }
                    knowledge_base_data['authorized_banks'].append(bank_record)
        
        # Store in S3
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        s3_key = f'regulatory-knowledge-base/fca-authorized-banks-{timestamp}.json'
        
        s3.put_object(
            Bucket=REGULATORY_BUCKET,
            Key=s3_key,
            Body=json.dumps(knowledge_base_data, indent=2, default=str),
            ContentType='application/json',
            Metadata={
                'collection_timestamp': datetime.now(timezone.utc).isoformat(),
                'source': 'fca_register_collector_lambda',
                'purpose': 'trade_finance_rag_knowledge_base',
                'total_firms': str(results.get('total_firms', 0))
            }
        )
        
        logger.info(f"Stored aggregated results in S3: {s3_key}")
        return s3_key
        
    except Exception as e:
        logger.error(f"Failed to store results in S3: {str(e)}")
        return None

def convert_floats_to_decimal(obj):
    """
    Convert float values to Decimal for DynamoDB compatibility
    """
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {key: convert_floats_to_decimal(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    else:
        return obj