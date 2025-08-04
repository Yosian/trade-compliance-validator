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

### Run Locally
```bash
# Start the API server
python src/api/main.py

# Process a sample document
curl -X POST http://localhost:5000/api/v1/documents/process \
  -F "file=@sample_data/letter_of_credit.pdf"
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

## 🧪 Testing

### Run Tests
```bash
# Unit tests
python -m pytest tests/unit/

# Integration tests
python -m pytest tests/integration/

# End-to-end tests
python -m pytest tests/e2e/
```

### Sample Documents
The `sample_data/` folder contains:
- `letter_of_credit.pdf` - Standard LC document
- `commercial_invoice.pdf` - Export invoice
- `bill_of_lading.pdf` - Shipping document
- `expected_outputs.json` - Golden dataset for evaluation

## 📡 API Endpoints

### Document Processing
```bash
POST /api/v1/documents/process
GET  /api/v1/documents/{doc_id}/results
GET  /api/v1/documents/{doc_id}/audit-trail
```

### Evaluation & Monitoring
```bash
GET  /api/v1/evaluation/pipeline-health
GET  /api/v1/evaluation/agent-performance/{agent_name}
POST /api/v1/evaluation/ab-test
```

### Prompt Management
```bash
GET  /api/v1/prompts/{agent_type}/versions
POST /api/v1/prompts/{agent_type}/new-version
PUT  /api/v1/prompts/{agent_type}/rollback/{version}
```

## 🏗️ Development Roadmap

### ✅ Phase 1: MVP Core (Days 1-2) - **PARTIALLY COMPLETE**
- [x] Project setup and infrastructure planning
- [x] Modular CloudFormation architecture design  
- [x] Storage layer deployment (DynamoDB + S3)
- [x] PowerShell deployment scripts with error handling
- [x] Environment configuration auto-generation
- [ ] Basic agent pipeline implementation
- [ ] API layer with Flask endpoints
- [ ] Sample data testing and validation

### 📊 Phase 2: Evaluation Layer (Days 3-4) - **PLANNED**
- [ ] Communications infrastructure (SQS + Step Functions)
- [ ] Evaluation framework with metrics tracking
- [ ] Audit trail enhancement and compliance logging
- [ ] Performance dashboard and monitoring

### 🚀 Phase 3: Advanced AI (Days 5-6) - **PLANNED**
- [ ] Prompt versioning and management system
- [ ] Bedrock caching implementation for cost optimization
- [ ] RAG vector store with regulation knowledge base
- [ ] A/B testing framework for prompt optimization

### 🏗️ Phase 4: Production Polish (Days 7-8) - **PLANNED**
- [ ] API Gateway stack deployment
- [ ] Monitoring and alerting stack
- [ ] Security hardening and compliance features
- [ ] Complete documentation and deployment guides

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

## 🎯 Success Metrics

- **Document processing accuracy**: > 85%
- **Average processing time**: < 30 seconds
- **API response time**: < 2 seconds
- **System uptime**: > 99%

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

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is created for demonstration purposes and showcases AI-powered trade finance automation capabilities.

## 🙏 Acknowledgments

- Built to demonstrate capabilities aligned with Traydstream's vision
- Inspired by modern agentic AI frameworks and trade finance digitization
- Uses AWS Bedrock, Claude, and serverless architecture best practices