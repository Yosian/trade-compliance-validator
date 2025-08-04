# Trade Document Validator - Communications Deployment Script
# Usage: .\deploy-communications.ps1 [environment]
# Example: .\deploy-communications.ps1 dev

param(
    [Parameter(Position=0)]
    [ValidateSet("dev", "staging", "prod")]
    [string]$Environment = "dev"
)

# Configuration
$ProjectPrefix = "tdv"
$StackName = "$ProjectPrefix-$Environment-communications"
$Region = if ($env:AWS_DEFAULT_REGION) { $env:AWS_DEFAULT_REGION } else { "us-east-1" }
$TemplateFile = "infrastructure\cloudformation\communications.yaml"

Write-Host "[INFO] Deploying SQS queues for Trade Document Validator..." -ForegroundColor Blue
Write-Host "[INFO] Environment: $Environment" -ForegroundColor Blue
Write-Host "[INFO] Stack Name: $StackName" -ForegroundColor Blue

# Validate template
Write-Host "[INFO] Validating CloudFormation template..." -ForegroundColor Blue
aws cloudformation validate-template --template-body "file://$TemplateFile" --region $Region

if ($LASTEXITCODE -eq 0) {
    Write-Host "[SUCCESS] Template validation passed" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Template validation failed" -ForegroundColor Red
    exit 1
}

# Deploy stack
Write-Host "[INFO] Deploying communications stack..." -ForegroundColor Blue

try {
    $result = aws cloudformation deploy `
        --template-file $TemplateFile `
        --stack-name $StackName `
        --parameter-overrides `
            "Environment=$Environment" `
            "ProjectPrefix=$ProjectPrefix" `
        --region $Region `
        --no-fail-on-empty-changeset

    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SUCCESS] Communications stack deployed successfully" -ForegroundColor Green
        
        # Get queue URLs
        Write-Host "[INFO] Retrieving queue URLs..." -ForegroundColor Blue
        $outputs = aws cloudformation describe-stacks `
            --stack-name $StackName `
            --region $Region `
            --query "Stacks[0].Outputs" `
            --output table
        
        Write-Host $outputs
    } else {
        Write-Host "[ERROR] Stack deployment failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[ERROR] Deployment failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "[SUCCESS] Communications deployment completed!" -ForegroundColor Green