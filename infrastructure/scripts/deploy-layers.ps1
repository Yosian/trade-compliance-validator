# Trade Document Validator - Lambda Layers Deployment Script
# Usage: .\deploy-layers.ps1 [environment] [-Rebuild]
# Example: .\deploy-layers.ps1 dev
# Example: .\deploy-layers.ps1 dev -Rebuild

param(
    [Parameter(Position=0)]
    [ValidateSet("dev", "staging", "prod")]
    [string]$Environment = "dev",
    
    [Parameter()]
    [switch]$Rebuild
)

# Configuration
$ProjectPrefix = "tdv"
$Region = if ($env:AWS_DEFAULT_REGION) { $env:AWS_DEFAULT_REGION } else { "us-east-1" }
$LayerName = "$ProjectPrefix-$Environment-pymupdf-layer"

# Colors for output
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

# Get script directory and navigate to project root
$ScriptPath = $PSScriptRoot
$ProjectRoot = Split-Path (Split-Path $ScriptPath -Parent) -Parent
Set-Location $ProjectRoot

Write-Info "Deploying Lambda layers for Trade Document Validator..."
Write-Info "Environment: $Environment"
Write-Info "Region: $Region"
Write-Info "Layer Name: $LayerName"

# Check if Docker is running
try {
    $null = docker info 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker is not running"
    }
    Write-Success "Docker is running"
}
catch {
    Write-Error "Docker is not available or not running"
    Write-Info "Please start Docker Desktop and try again"
    exit 1
}

# Navigate to PyMuPDF layer directory
$LayerDir = "layers\pymupdf"
if (-not (Test-Path $LayerDir)) {
    Write-Error "Layer directory not found: $LayerDir"
    exit 1
}

Set-Location $LayerDir

# Check if layer needs to be built
$LayerZip = "output\pymupdf-layer.zip"
$ShouldBuild = $Rebuild -or (-not (Test-Path $LayerZip))

if ($ShouldBuild) {
    Write-Info "Building PyMuPDF layer with Docker..."
    
    # Run layer build script
    try {
        .\build-layer.ps1
        if ($LASTEXITCODE -ne 0) {
            throw "Layer build failed"
        }
        Write-Success "Layer built successfully"
    }
    catch {
        Write-Error "Failed to build layer: $($_.Exception.Message)"
        exit 1
    }
}
else {
    Write-Info "Using existing layer zip: $LayerZip"
}

# Check if layer zip exists
if (-not (Test-Path $LayerZip)) {
    Write-Error "Layer zip not found: $LayerZip"
    exit 1
}

# Get layer zip size for logging
$LayerSize = (Get-Item $LayerZip).Length
$LayerSizeMB = [math]::Round($LayerSize / 1MB, 2)
Write-Info "Layer size: ${LayerSizeMB} MB"

# Check AWS CLI and credentials
try {
    $AccountId = (aws sts get-caller-identity --query Account --output text 2>$null)
    if ($LASTEXITCODE -ne 0) {
        throw "AWS credentials not configured"
    }
    Write-Info "AWS Account ID: $AccountId"
}
catch {
    Write-Error "AWS CLI is not configured or credentials are invalid"
    Write-Info "Run 'aws configure' to set up your credentials"
    exit 1
}

# Deploy layer to AWS
Write-Info "Deploying layer to AWS Lambda..."

try {
    $result = aws lambda publish-layer-version `
        --layer-name $LayerName `
        --zip-file "fileb://$LayerZip" `
        --compatible-runtimes python3.11 `
        --description "PyMuPDF layer for PDF processing - $Environment environment" `
        --region $Region `
        --output json
    
    if ($LASTEXITCODE -eq 0) {
        $layerInfo = $result | ConvertFrom-Json
        $LayerVersionArn = $layerInfo.LayerVersionArn
        $Version = $layerInfo.Version
        
        Write-Success "Layer deployed successfully"
        Write-Info "Layer Version: $Version"
        Write-Info "Layer ARN: $LayerVersionArn"
        
        # Store layer ARN in environment file for easy reference
        $ConfigDir = "..\..\src\config"
        $EnvFile = "$ConfigDir\.env.$Environment"
        
        if (Test-Path $EnvFile) {
            # Add or update layer ARN in environment file
            $envContent = Get-Content $EnvFile
            $layerArnLine = "PYMUPDF_LAYER_ARN=$LayerVersionArn"
            
            # Remove existing layer ARN line if present
            $envContent = $envContent | Where-Object { $_ -notmatch "^PYMUPDF_LAYER_ARN=" }
            
            # Add new layer ARN line
            $envContent += $layerArnLine
            
            # Write back to file
            $envContent | Out-File -FilePath $EnvFile -Encoding UTF8
            
            Write-Success "Layer ARN added to environment file: $EnvFile"
        }
        else {
            Write-Warning "Environment file not found: $EnvFile"
            Write-Info "Please manually add this to your Lambda configuration:"
            Write-Info "PYMUPDF_LAYER_ARN=$LayerVersionArn"
        }
        
        # List recent layer versions for reference
        Write-Info "Recent layer versions:"
        try {
            $versions = aws lambda list-layer-versions `
                --layer-name $LayerName `
                --region $Region `
                --max-items 5 `
                --query "LayerVersions[].{Version:Version,CreatedDate:CreatedDate}" `
                --output table
            
            Write-Host $versions
        }
        catch {
            Write-Warning "Could not list layer versions"
        }
    }
    else {
        throw "Layer deployment failed"
    }
}
catch {
    Write-Error "Failed to deploy layer: $($_.Exception.Message)"
    exit 1
}

# Return to project root
Set-Location $ProjectRoot

Write-Success "Layer deployment completed successfully!"
Write-Info ""
Write-Info "Next steps:"
Write-Info "1. Use the layer ARN in your Lambda functions:"
Write-Info "   $LayerVersionArn"
Write-Info ""
Write-Info "2. In your Lambda function code, import PyMuPDF:"
Write-Info "   import fitz  # PyMuPDF"
Write-Info ""
Write-Info "3. Deploy compute stack with layer integration:"
Write-Info "   .\infrastructure\scripts\deploy-compute.ps1 $Environment"