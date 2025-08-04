# Trade Document Compliance Validator

**AI-powered trade document compliance checking system demonstrating advanced ML evaluation capabilities**

## 🎯 Project Overview

This project demonstrates a mini-version of Traydstream's core platform capabilities:
- **Agentic AI document processing** pipeline using Claude via AWS Bedrock
- **Comprehensive evaluation framework** with metrics tracking and A/B testing
- **Audit trail and explainability** for regulatory compliance
- **Prompt versioning and caching** for production optimization
- **RAG-based regulation checking** using trade finance knowledge base

**Resource Naming Convention**: All AWS resources use the pattern `tdv-{environment}-{resource}-{accountId}-us-east-1` for clear identification and multi-account/region deployment support.

## 🏗️ Architecture

**Modular CloudFormation Infrastructure:**
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Document      │    │   AI Agents      │    │   Compliance    │
│   Upload        ├────►   Pipeline       ├────►   Validation    │
│   (S3)          │    │   (Lambda)       │    │   (Results)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                        │
         └───────────────────────┼────────────────────────┘
                                 ▼
                    ┌──────────────────┐
                    │   Audit &        │
                    │   Evaluation     │
                    │   (DynamoDB)     │
                    └──────────────────┘
```

**Infrastructure Stacks:**
- `tdv-dev-storage` ✅ **DEPLOYED** - DynamoDB tables + S3 buckets
- `tdv-dev-communications` 📋 - SQS queues + Step Functions  
- `tdv-dev-compute` 📋 - Lambda functions + IAM roles
- `tdv-dev-api` 📋 - API Gateway + authorizers
- `tdv-dev-monitoring` 📋 - CloudWatch dashboards + alarms

## 🚀 Quick Start

### Prerequisites
- AWS CLI configured with appropriate permissions
- Python 3.9+
- Docker (for local development)

### Installation
```bash
git clone <your-repo-url>
cd trade-compliance-validator
pip install -r requirements.txt
```

### Deploy Infrastructure
```bash
# Deploy core storage (DynamoDB, S3)
./infrastructure/scripts/deploy-storage.sh dev

# Verify deployment (stack will be named: tdv-dev-storage)
aws cloudformation describe-stacks --stack-name tdv-dev-storage
```

## 📊 Key Features

### 🤖 AI Agent Pipeline
- **Document Classifier**: Identifies document type (LC, Invoice, Bill of Lading)
- **Field Extractor**: Extracts key trade finance fields
- **Compliance Validator**: Checks against UCP600 and ISBP guidelines
- **Risk Scorer**: Assigns compliance confidence scores

### 📈 Evaluation & Monitoring
- **Real-time metrics**: Accuracy, processing time, confidence scores
- **A/B testing framework**: Compare prompt versions and model performance
- **Audit trail**: Full decision logging for regulatory compliance
- **Performance dashboard**: System health and trend analysis

### 🎛️ Advanced Features
- **Prompt versioning**: Manage and rollback prompt changes
- **Bedrock caching**: Optimize costs and response times
- **RAG integration**: Query regulation knowledge base
- **Vector embeddings**: Smart regulation retrieval

## 🎯 Current Status

### ✅ **COMPLETED** (Infrastructure Foundation):
- **✅ Modular Architecture**: Independent CloudFormation stacks with proper separation of concerns
- **✅ Storage Infrastructure**: All DynamoDB tables and S3 buckets deployed and tested
- **✅ Resource Naming**: Consistent `tdv-{env}-{resource}-{account}-{region}` pattern
- **✅ Deployment Pipeline**: Robust PowerShell scripts with error handling and auto-detection
- **✅ Environment Configuration**: Auto-generated `.env.dev` file with all resource references
- **✅ Sample Prompts**: Initial prompt templates uploaded to S3 for AI agents

### 🔄 **IMMEDIATE NEXT STEPS**:
1. **Implement Document Processor Agent** (`src/agents/document_processor.py`)
   - Claude integration via AWS Bedrock for document classification
   - PyPDF2 integration for text extraction
   - Structured field extraction with JSON output

2. **Create Sample Test Data** (`sample_data/`)
   - Letter of Credit PDF samples
   - Commercial Invoice samples
   - Expected compliance outputs (golden dataset)

3. **Build Basic API Layer** (`src/api/main.py`)
   - Flask endpoints for document upload and processing
   - Results retrieval with full audit trail

**Resource Names Created:**
```
Stack: tdv-dev-storage
Tables: tdv-dev-documents-{accountId}-{region}
        tdv-dev-audit-trail-{accountId}-{region}  
        tdv-dev-prompt-versions-{accountId}-{region}
Buckets: tdv-dev-docs-{accountId}-{region}
         tdv-dev-prompts-{accountId}-{region}
         tdv-dev-embeddings-{accountId}-{region}
         tdv-dev-model-artifacts-{accountId}-{region}
```

## 🔧 Configuration

### Environment Variables (Auto-generated)
The deployment script creates `src/config/.env.dev` with:
```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=864899848062

# Environment  
ENVIRONMENT=dev

# DynamoDB Tables (auto-generated names)
DOCUMENTS_TABLE=tdv-dev-documents-{accountId}-{region}
AUDIT_TABLE=tdv-dev-audit-trail-{accountId}-{region}
PROMPT_VERSIONS_TABLE=tdv-dev-prompt-versions-{accountId}-{region}

# S3 Buckets (auto-generated names)
DOCUMENTS_BUCKET=tdv-dev-docs-{accountId}-{region}
PROMPTS_BUCKET=tdv-dev-prompts-{accountId}-{region}
EMBEDDINGS_BUCKET=tdv-dev-embeddings-{accountId}-{region}
MODEL_ARTIFACTS_BUCKET=tdv-dev-model-artifacts-{accountId}-{region}

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Application Configuration
LOG_LEVEL=INFO
API_PORT=5000
```

### Development Environment
- **Scripting**: PowerShell (.ps1) for VS Code compatibility
- **Deployment**: Modular CloudFormation stacks
- **Region/Account Flexible**: Deploy to any AWS region and account

### AWS Permissions Required
- Bedrock model access (Claude)
- DynamoDB read/write
- S3 bucket operations
- CloudWatch metrics
- Lambda execution

## 📄 License

This project is created for demonstration purposes and showcases AI-powered trade finance automation capabilities.

## 🙏 Acknowledgments

- Built to demonstrate capabilities aligned with Traydstream's vision
- Inspired by modern agentic AI frameworks and trade finance digitization
- Uses AWS Bedrock, Claude, and serverless architecture best practices