# Trade Document Validator - Storage Deployment Script
# Usage: .\deploy-storage.ps1 [environment] [-ForceRecreate]
# Example: .\deploy-storage.ps1 dev
# Example: .\deploy-storage.ps1 dev -ForceRecreate

param(
    [Parameter(Position=0)]
    [ValidateSet("dev", "staging", "prod")]
    [string]$Environment = "dev",
    
    [Parameter()]
    [switch]$ForceRecreate
)

# Configuration
$ProjectPrefix = "tdv"
$StackName = "$ProjectPrefix-$Environment-storage"
$Region = if ($env:AWS_DEFAULT_REGION) { $env:AWS_DEFAULT_REGION } else { "us-east-1" }

# Auto-detect project root directory
$ScriptPath = $PSScriptRoot
$ProjectRoot = $null

# Try to find project root by looking for key files
$CurrentDir = $ScriptPath
while ($CurrentDir -and (Split-Path $CurrentDir -Parent)) {
    if ((Test-Path (Join-Path $CurrentDir "requirements.txt")) -and 
        (Test-Path (Join-Path $CurrentDir "src")) -and
        (Test-Path (Join-Path $CurrentDir "infrastructure"))) {
        $ProjectRoot = $CurrentDir
        break
    }
    $CurrentDir = Split-Path $CurrentDir -Parent
}

if (-not $ProjectRoot) {
    Write-Error "Could not find project root directory. Please ensure you're running this script from within the trade-compliance-validator project."
    exit 1
}

Write-Info "Project root detected: $ProjectRoot"
Set-Location $ProjectRoot

$TemplateFile = "infrastructure\cloudformation\storage.yaml"

# Colors for output (PowerShell doesn't have built-in colors like bash)
function Write-Info($message) {
    Write-Host "[INFO] $message" -ForegroundColor Blue
}

function Write-Success($message) {
    Write-Host "[SUCCESS] $message" -ForegroundColor Green
}

function Write-Warning($message) {
    Write-Host "[WARNING] $message" -ForegroundColor Yellow
}

function Write-Error($message) {
    Write-Host "[ERROR] $message" -ForegroundColor Red
}

# Function to test AWS CLI availability and credentials
function Test-AWSSetup {
    try {
        $null = aws sts get-caller-identity --output json 2>$null
        return $true
    }
    catch {
        return $false
    }
}

# Function to check if CloudFormation stack exists
function Test-StackExists($stackName, $region) {
    try {
        $result = aws cloudformation describe-stacks --stack-name $stackName --region $region --output json 2>$null
        if ($LASTEXITCODE -eq 0) {
            return $true
        } else {
            return $false
        }
    }
    catch {
        return $false
    }
}

# Function to wait for stack operation to complete
function Wait-StackOperation($stackName, $region, $operation) {
    Write-Info "Waiting for stack $operation to complete..."
    
    $waitCommand = switch ($operation) {
        "create" { "stack-create-complete" }
        "update" { "stack-update-complete" }
        default { throw "Unknown operation: $operation" }
    }
    
    try {
        $waitResult = aws cloudformation wait $waitCommand --stack-name $stackName --region $region 2>&1
        if ($LASTEXITCODE -eq 0) {
            return $true
        } else {
            Write-Error "Stack $operation failed. Exit code: $LASTEXITCODE"
            Write-Error "Error details: $waitResult"
            
            # Get stack events to show what went wrong
            Write-Info "Retrieving stack events for troubleshooting..."
            try {
                $events = aws cloudformation describe-stack-events --stack-name $stackName --region $region --query "StackEvents[?ResourceStatus=='CREATE_FAILED' || ResourceStatus=='UPDATE_FAILED'].{Resource:LogicalResourceId,Status:ResourceStatus,Reason:ResourceStatusReason}" --output table 2>$null
                if ($events) {
                    Write-Host $events
                }
            } catch {
                Write-Warning "Could not retrieve stack events"
            }
            return $false
        }
    }
    catch {
        Write-Error "Stack $operation failed or timed out: $($_.Exception.Message)"
        return $false
    }
}

# Main script execution
Write-Info "Starting Trade Document Validator storage deployment..."
Write-Info "Environment: $Environment"
Write-Info "Region: $Region"
Write-Info "Stack Name: $StackName"

# Check if template file exists
if (-not (Test-Path $TemplateFile)) {
    Write-Error "CloudFormation template not found: $TemplateFile"
    Write-Info "Please ensure you're running this script from the project root directory"
    exit 1
}

# Check AWS CLI setup
if (-not (Test-AWSSetup)) {
    Write-Error "AWS CLI is not configured or credentials are invalid"
    Write-Info "Run 'aws configure' to set up your credentials"
    exit 1
}

# Get AWS Account ID for logging
try {
    $AccountId = (aws sts get-caller-identity --query Account --output text)
    Write-Info "Account ID: $AccountId"
}
catch {
    Write-Error "Failed to get AWS Account ID"
    exit 1
}

# Validate CloudFormation template
Write-Info "Validating CloudFormation template..."
try {
    $null = aws cloudformation validate-template --template-body "file://$TemplateFile" --region $Region --output json
    Write-Success "Template validation passed"
}
catch {
    Write-Error "Template validation failed"
    Write-Error $_.Exception.Message
    exit 1
}

# Check if stack exists
Write-Info "Checking if stack exists..."

# First, let's list all stacks to see what's there
Write-Info "Listing existing stacks with 'tdv' prefix..."
try {
    $existingStacks = aws cloudformation list-stacks --region $Region --query "StackSummaries[?contains(StackName, 'tdv') && StackStatus != 'DELETE_COMPLETE'].{Name:StackName,Status:StackStatus}" --output table 2>$null
    if ($existingStacks) {
        Write-Host $existingStacks
    } else {
        Write-Info "No existing stacks found with 'tdv' prefix"
    }
} catch {
    Write-Warning "Could not list existing stacks"
}

$StackExists = Test-StackExists -stackName $StackName -region $Region
Write-Info "Stack exists: $StackExists"

# Handle force recreate option
if ($ForceRecreate -and $StackExists) {
    Write-Warning "Force recreate requested - deleting existing stack..."
    try {
        aws cloudformation delete-stack --stack-name $StackName --region $Region
        Write-Info "Waiting for stack deletion to complete..."
        aws cloudformation wait stack-delete-complete --stack-name $StackName --region $Region
        Write-Success "Stack deleted successfully"
        $StackExists = $false
    }
    catch {
        Write-Error "Failed to delete existing stack: $($_.Exception.Message)"
        exit 1
    }
}

if ($StackExists) {
    Write-Info "Stack exists, performing update..."
    
    # Update existing stack
    try {
        $updateResult = aws cloudformation update-stack `
            --stack-name $StackName `
            --template-body "file://$TemplateFile" `
            --parameters `
                "ParameterKey=Environment,ParameterValue=$Environment" `
                "ParameterKey=ProjectPrefix,ParameterValue=$ProjectPrefix" `
            --region $Region `
            --output json 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            if (Wait-StackOperation -stackName $StackName -region $Region -operation "update") {
                Write-Success "Stack update completed"
            }
            else {
                Write-Error "Stack update failed"
                exit 1
            }
        } else {
            if ($updateResult -match "No updates are to be performed") {
                Write-Warning "No updates to be performed"
            } else {
                Write-Error "Stack update failed: $updateResult"
                exit 1
            }
        }
    }
    catch {
        Write-Error "Stack update failed: $($_.Exception.Message)"
        exit 1
    }
}
else {
    Write-Info "Stack does not exist, creating new stack..."
    
    # Create new stack
    try {
        $createResult = aws cloudformation create-stack `
            --stack-name $StackName `
            --template-body "file://$TemplateFile" `
            --parameters `
                "ParameterKey=Environment,ParameterValue=$Environment" `
                "ParameterKey=ProjectPrefix,ParameterValue=$ProjectPrefix" `
            --region $Region `
            --output json 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            if (Wait-StackOperation -stackName $StackName -region $Region -operation "create") {
                Write-Success "Stack creation completed"
            }
            else {
                Write-Error "Stack creation failed"
                exit 1
            }
        } else {
            Write-Error "Stack creation failed: $createResult"
            exit 1
        }
    }
    catch {
        Write-Error "Stack creation failed: $($_.Exception.Message)"
        exit 1
    }
}

# Get stack outputs
Write-Info "Retrieving stack outputs..."
try {
    $outputs = aws cloudformation describe-stacks `
        --stack-name $StackName `
        --region $Region `
        --query "Stacks[0].Outputs" `
        --output table
    
    Write-Host $outputs
}
catch {
    Write-Warning "Failed to retrieve stack outputs, but deployment was successful"
}

# Extract key values for environment file
Write-Info "Extracting resource information..."

try {
    $DocumentsTable = (aws cloudformation describe-stacks `
        --stack-name $StackName `
        --region $Region `
        --query "Stacks[0].Outputs[?OutputKey=='DocumentsTableName'].OutputValue" `
        --output text).Trim()

    $AuditTable = (aws cloudformation describe-stacks `
        --stack-name $StackName `
        --region $Region `
        --query "Stacks[0].Outputs[?OutputKey=='AuditTrailTableName'].OutputValue" `
        --output text).Trim()

    $PromptVersionsTable = (aws cloudformation describe-stacks `
        --stack-name $StackName `
        --region $Region `
        --query "Stacks[0].Outputs[?OutputKey=='PromptVersionsTableName'].OutputValue" `
        --output text).Trim()

    # Fixed the query to match the actual output key name
    $RegulatoryApiCacheTable = (aws cloudformation describe-stacks `
        --stack-name $StackName `
        --region $Region `
        --query "Stacks[0].Outputs[?OutputKey=='RegulatoryApiCacheTableName'].OutputValue" `
        --output text).Trim()

    $DocumentsBucket = (aws cloudformation describe-stacks `
        --stack-name $StackName `
        --region $Region `
        --query "Stacks[0].Outputs[?OutputKey=='DocumentsBucketName'].OutputValue" `
        --output text).Trim()

    $PromptsBucket = (aws cloudformation describe-stacks `
        --stack-name $StackName `
        --region $Region `
        --query "Stacks[0].Outputs[?OutputKey=='PromptsBucketName'].OutputValue" `
        --output text).Trim()

    $EmbeddingsBucket = (aws cloudformation describe-stacks `
        --stack-name $StackName `
        --region $Region `
        --query "Stacks[0].Outputs[?OutputKey=='EmbeddingsBucketName'].OutputValue" `
        --output text).Trim()

    $ModelArtifactsBucket = (aws cloudformation describe-stacks `
        --stack-name $StackName `
        --region $Region `
        --query "Stacks[0].Outputs[?OutputKey=='ModelArtifactsBucketName'].OutputValue" `
        --output text).Trim()

    # Verify we got the essential values
    if (-not $DocumentsTable -or -not $DocumentsBucket) {
        throw "Failed to extract required resource names from stack outputs"
    }
    
    # RegulatoryApiCacheTable is optional for backward compatibility
    if (-not $RegulatoryApiCacheTable) {
        Write-Warning "RegulatoryApiCacheTable not found - may be an older stack version"
        $RegulatoryApiCacheTable = "not-available"
    }
}
catch {
    Write-Error "Failed to extract resource information: $($_.Exception.Message)"
    Write-Error "This usually means the stack deployment failed or outputs are not available"
    exit 1
}

# Create .env file for the environment
$ConfigDir = "src\config"
$EnvFile = "$ConfigDir\.env.$Environment"

# Create config directory if it doesn't exist
if (-not (Test-Path $ConfigDir)) {
    New-Item -ItemType Directory -Path $ConfigDir -Force | Out-Null
}

# Generate environment file content
$EnvContent = @"
# Auto-generated environment configuration
# Generated on: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
# Stack: $StackName

# AWS Configuration
AWS_REGION=$Region
AWS_ACCOUNT_ID=$AccountId

# Environment
ENVIRONMENT=$Environment

# DynamoDB Tables
DOCUMENTS_TABLE=$DocumentsTable
AUDIT_TABLE=$AuditTable
PROMPT_VERSIONS_TABLE=$PromptVersionsTable
REGULATORY_API_CACHE_TABLE=$RegulatoryApiCacheTable

# S3 Buckets
DOCUMENTS_BUCKET=$DocumentsBucket
PROMPTS_BUCKET=$PromptsBucket
EMBEDDINGS_BUCKET=$EmbeddingsBucket
MODEL_ARTIFACTS_BUCKET=$ModelArtifactsBucket

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Application Configuration
LOG_LEVEL=INFO
API_PORT=5000
"@

# Write environment file
$EnvContent | Out-File -FilePath $EnvFile -Encoding UTF8
Write-Success "Environment file created: $EnvFile"

# Create sample prompts in S3
Write-Info "Uploading sample prompts..."

$TempDir = "$env:TEMP\trade-document-validator-prompts"
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

# Document classifier prompt
$ClassifierPrompt = @"
You are a trade document classifier. Analyze the provided document text and classify it into one of these categories:
- LETTER_OF_CREDIT: Letters of credit, documentary credits
- COMMERCIAL_INVOICE: Commercial invoices, proforma invoices
- BILL_OF_LADING: Bills of lading, shipping documents
- PACKING_LIST: Packing lists, shipping manifests
- OTHER: Any other trade document

Respond with only the category name.

Document text:
{document_text}
"@

# Field extractor prompt
$ExtractorPrompt = @"
Extract the following key fields from this trade document. Return as JSON:

Required fields:
- beneficiary: Name of the beneficiary
- applicant: Name of the applicant/buyer
- amount: Document amount with currency
- description: Description of goods/services
- date: Document date
- reference: Document reference number

Document text:
{document_text}

Return only valid JSON with the extracted fields.
"@

# Compliance validator prompt
$ValidatorPrompt = @"
Analyze this trade document for compliance issues. Check for:
1. Completeness of required fields
2. Consistency between different sections
3. Format compliance with trade finance standards
4. Any obvious discrepancies or red flags

Document type: {document_type}
Extracted fields: {fields}

Return JSON with:
- compliance_score: 0-100 score
- issues: List of identified issues
- recommendations: List of recommendations
- risk_level: LOW, MEDIUM, HIGH
"@

# Write prompt files
$ClassifierPrompt | Out-File -FilePath "$TempDir\classifier_prompt.txt" -Encoding UTF8
$ExtractorPrompt | Out-File -FilePath "$TempDir\extractor_prompt.txt" -Encoding UTF8
$ValidatorPrompt | Out-File -FilePath "$TempDir\validator_prompt.txt" -Encoding UTF8

# Upload prompts to S3
if ($PromptsBucket) {
    try {
        aws s3 cp "$TempDir\classifier_prompt.txt" "s3://$PromptsBucket/classifier/current/prompt.txt"
        aws s3 cp "$TempDir\extractor_prompt.txt" "s3://$PromptsBucket/extractor/current/prompt.txt"
        aws s3 cp "$TempDir\validator_prompt.txt" "s3://$PromptsBucket/validator/current/prompt.txt"
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Sample prompts uploaded to S3"
        } else {
            Write-Warning "Some prompts failed to upload to S3"
        }
    }
    catch {
        Write-Warning "Failed to upload sample prompts: $($_.Exception.Message)"
    }
} else {
    Write-Warning "Skipping prompt upload - prompts bucket name not available"
}

# Clean up temp files
Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue

# Test connectivity
Write-Info "Testing AWS connectivity..."

# Test DynamoDB
if ($DocumentsTable) {
    try {
        $null = aws dynamodb describe-table --table-name $DocumentsTable --region $Region --output json
        if ($LASTEXITCODE -eq 0) {
            Write-Success "DynamoDB connectivity confirmed"
        } else {
            Write-Error "DynamoDB connectivity failed"
        }
    }
    catch {
        Write-Error "DynamoDB connectivity failed: $($_.Exception.Message)"
    }
} else {
    Write-Warning "Skipping DynamoDB test - table name not available"
}

# Test S3
if ($DocumentsBucket) {
    try {
        $null = aws s3 ls "s3://$DocumentsBucket" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "S3 connectivity confirmed"
        } else {
            Write-Error "S3 connectivity failed"
        }
    }
    catch {
        Write-Error "S3 connectivity failed: $($_.Exception.Message)"
    }
} else {
    Write-Warning "Skipping S3 test - bucket name not available"
}

Write-Success "Storage deployment completed successfully!"
Write-Info ""
Write-Info "Next steps:"
Write-Info "1. Load the environment file variables (manual process in PowerShell)"
Write-Info "2. Install dependencies: pip install -r requirements.txt"
Write-Info "3. Start implementing the document processor: src\agents\document_processor.py"
Write-Info ""
Write-Info "If you encounter issues, you can force recreate the stack with:"
Write-Info "  .\infrastructure\scripts\deploy-storage.ps1 dev -ForceRecreate"
Write-Info ""
Write-Info "Stack resources:"
Write-Info "  Documents Table: $DocumentsTable"
Write-Info "  Audit Table: $AuditTable"
Write-Info "  Prompt Versions Table: $PromptVersionsTable"
Write-Info "  Regulatory API Cache Table: $RegulatoryApiCacheTable"
Write-Info "  Documents Bucket: $DocumentsBucket"
Write-Info "  Prompts Bucket: $PromptsBucket"
Write-Info "  Embeddings Bucket: $EmbeddingsBucket"
Write-Info "  Model Artifacts Bucket: $ModelArtifactsBucket"