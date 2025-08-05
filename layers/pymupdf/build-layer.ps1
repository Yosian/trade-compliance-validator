# PyMuPDF Lambda Layer Build Script
# build-layer.ps1

Write-Host "Building PyMuPDF Lambda Layer..." -ForegroundColor Green

# Get the script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "Script directory: $scriptDir" -ForegroundColor Cyan

Set-Location $scriptDir

# Create output directory
if (!(Test-Path "output")) {
    New-Item -ItemType Directory -Name "output"
}

# Build the Docker image
Write-Host "Building Docker image..." -ForegroundColor Yellow
docker build -t pymupdf-layer .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker build failed!" -ForegroundColor Red
    exit 1
}

# Run container in detached mode and copy the layer zip
Write-Host "Extracting layer zip..." -ForegroundColor Yellow
$containerId = docker run -d pymupdf-layer
Start-Sleep -Seconds 2  # Give container time to start

# Copy the zip file from container to host
docker cp "${containerId}:/tmp/pymupdf-layer.zip" "./output/pymupdf-layer.zip"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to extract layer zip!" -ForegroundColor Red
    docker stop $containerId | Out-Null
    docker rm $containerId | Out-Null
    exit 1
}

# Clean up container
docker stop $containerId | Out-Null
docker rm $containerId | Out-Null

Write-Host "Layer built successfully!" -ForegroundColor Green
Write-Host "Layer file: output/pymupdf-layer.zip" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Upload the layer to AWS:" -ForegroundColor White
Write-Host "   aws lambda publish-layer-version --layer-name pymupdf-layer --zip-file fileb://output/pymupdf-layer.zip --compatible-runtimes python3.11" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Note the LayerVersionArn from the response to use in your Lambda function" -ForegroundColor White