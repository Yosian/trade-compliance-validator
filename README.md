# Trade Document Compliance Validator

**AI-powered trade document compliance checking system demonstrating advanced ML evaluation capabilities**

## 🎯 Project Overview

This project demonstrates a mini-version of Traydstream's core platform capabilities:
- **Agentic AI document processing** pipeline using Claude via AWS Bedrock
- **Comprehensive evaluation framework** with metrics tracking and A/B testing
- **Audit trail and explainability** for regulatory compliance
- **Prompt versioning and caching** for production optimization
- **RAG-based regulation checking** using trade finance knowledge base

## 🏗️ Architecture

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

# Verify deployment
aws cloudformation describe-stacks --stack-name trade-compliance-dev
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

### ✅ Phase 1: MVP Core (Days 1-2)
- [x] Project setup and infrastructure
- [ ] Basic agent pipeline
- [ ] API layer
- [ ] Sample data testing

### 📊 Phase 2: Evaluation Layer (Days 3-4)
- [ ] Evaluation framework
- [ ] Audit trail enhancement
- [ ] Performance dashboard

### 🚀 Phase 3: Advanced AI (Days 5-6)
- [ ] Prompt versioning
- [ ] Caching implementation
- [ ] RAG vector store
- [ ] A/B testing framework

### 🏗️ Phase 4: Production Polish (Days 7-8)
- [ ] Infrastructure as Code
- [ ] Error handling & resilience
- [ ] Security & compliance
- [ ] Complete documentation

## 🎯 Success Metrics

- **Document processing accuracy**: > 85%
- **Average processing time**: < 30 seconds
- **API response time**: < 2 seconds
- **System uptime**: > 99%

## 🔧 Configuration

### Environment Variables
```bash
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
DYNAMODB_TABLE_PREFIX=trade-compliance
S3_BUCKET_PREFIX=trade-docs
LOG_LEVEL=INFO
```

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