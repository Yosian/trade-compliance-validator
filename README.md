# Trade Document Compliance Validator

**AI-powered trade finance document processing system with production-grade testing and cost optimization**

A technical demonstration of enterprise ML engineering capabilities, showcasing agentic AI architecture, cost-optimized processing, and comprehensive testing strategies for high-stakes production environments.

---

## 🎯 **Problem Statement**

Trade finance document processing currently requires manual review of complex documents (Letters of Credit, Commercial Invoices, Bills of Lading) taking days to complete. This system demonstrates automated processing that reduces processing time from days to minutes while maintaining regulatory compliance and audit trails.

**Key Challenges Addressed:**
- **Document Variability:** Different formats, languages, and quality levels
- **Cost Optimization:** AI inference costs can be 10x higher with wrong model selection
- **Regulatory Compliance:** Complete audit trails required for financial services
- **Production Reliability:** System failures can cost thousands in runaway processing

---

## 🏗️ **System Architecture**

### **Agentic AI Pipeline**
```
📄 Document Upload → 🔀 File Router → 📊 AI Classifier → 🧠 Field Extractor → 💾 Results Storage
                           ↓              ↓               ↓              ↓
                    SQS Orchestration  Cost-Optimized   Retry Logic   Audit Trail
```

### **Two-Stage Cost Optimization**
- **Stage 1:** Fast classification using Claude Haiku ($0.0005 per document)
- **Stage 2:** Escalation to Claude Sonnet ($0.006 per document) only when confidence < 80%
- **Result:** 45% cost reduction through intelligent model selection

### **Production Safety Features**
- **Hard retry limits:** Maximum 2 attempts (prevents infinite loop incidents)
- **Decimal precision:** All financial calculations use Decimal type for DynamoDB compatibility
- **Circuit breakers:** Processing stops on consecutive failures
- **Complete audit trail:** Every decision logged for regulatory compliance

---

## 📁 **Repository Structure**

### **Core Processing Logic**
```
src/
├── agents/
│   ├── file_selector.py          # Intelligent document routing
│   ├── image_extractor.py        # Two-stage AI processing with retry logic
│   └── pdf_to_png.py            # Docker-based PDF conversion
├── prompts/                      # Version-controlled AI prompts
│   ├── classifier_prompt_arn_V1.txt
│   └── LETTER_OF_CREDIT_V1_prompt_arn.txt
└── config/
    └── .env.dev                  # Auto-generated environment configuration
```

### **Infrastructure as Code**
```
infrastructure/
├── cloudformation/
│   ├── storage.yaml              # DynamoDB tables + S3 buckets
│   └── communications.yaml       # SQS queues with dead letter queues
└── scripts/
    ├── deploy-storage.ps1        # Automated deployment with validation
    └── deploy-communications.ps1 # Multi-region deployment ready
```

### **Production Testing**
```
tests/
├── test_llm_parsing.py          # LLM response parsing & validation (Priority 1)
├── test_escalation_logic.py     # Cost optimization & retry logic (Priority 2)
└── conftest.py                  # Test fixtures and configuration
```

---

## 🚀 **Quick Start**

### **Prerequisites**
- AWS CLI configured with appropriate permissions
- Python 3.9+
- Docker (for Lambda layers)

### **1. Deploy Infrastructure**
```powershell
# Deploy DynamoDB tables and S3 buckets
.\infrastructure\scripts\deploy-storage.ps1 dev

# Deploy SQS queues and messaging infrastructure
.\infrastructure\scripts\deploy-communications.ps1 dev
```

### **2. Install Dependencies**
```bash
pip install -r requirements.txt
```

### **3. Run Tests**
```bash
# Run all tests
python -m pytest tests/ -v

# Run priority 1 tests (LLM parsing reliability)
python -m pytest tests/test_llm_parsing.py -v

# Run priority 2 tests (cost optimization & retry logic)  
python -m pytest tests/test_escalation_logic.py -v
```

### **4. Test End-to-End Processing**
```bash
# Upload test document
aws s3 cp sample-letter-of-credit.png s3://tdv-dev-docs-{accountId}-{region}/test/

# Trigger processing
aws sqs send-message \
  --queue-url "https://sqs.us-east-1.amazonaws.com/{accountId}/tdv-dev-vision-processing" \
  --message-body '{"bucket": "tdv-dev-docs-{accountId}-{region}", "key": "test/sample-letter-of-credit.png"}'

# Check results
aws dynamodb scan --table-name tdv-dev-documents-{accountId}-{region} --limit 5
```

---

## 🧪 **Testing Strategy**

### **Priority-Based Testing Approach**
Rather than comprehensive coverage, tests focus on the **highest-risk failure points** in production ML systems:

#### **Priority 1: LLM Response Parsing (6 tests)**
- **Malformed JSON handling** - Prevents pipeline failures from truncated AI responses
- **Missing field validation** - Safe defaults when AI omits required fields  
- **Data type conversion** - Decimal compatibility for DynamoDB financial data
- **Invalid response graceful handling** - System continues operating despite AI failures

#### **Priority 2: Cost Optimization Logic (17 tests)**
- **Escalation decision accuracy** - Validates 0.8 confidence threshold
- **Financial calculation correctness** - 45% cost savings through smart model selection
- **Retry logic safety** - Maximum 2 attempts (prevents $4k infinite loop incidents)
- **Batch processing validation** - Cost optimization at scale

**Test Results:** 23/23 tests passing (100% success rate)

### **Key Test Validations**
```bash
# Confidence threshold testing
assert result['escalated'] == (confidence < Decimal('0.8'))

# Infinite loop prevention  
assert mock_extract.call_count == 2  # Maximum 2 attempts
assert result['retry_metadata']['attempts_made'] <= 2

# Cost calculation accuracy
assert expensive_cost > cheap_cost * Decimal('1.5')  # Realistic cost difference
```

---

## 💰 **Cost Optimization**

### **Business Intelligence**
- **Classification cost:** $0.0005 (cheap) vs $0.006 (expensive) per document
- **Extraction cost:** $0.006 per document (always uses accuracy-optimized model)
- **Total savings:** 45% reduction through intelligent model selection
- **Batch processing:** 1000 documents cost $6.50 vs $12.00 without optimization

### **Production Safeguards**
- **Hard retry limits:** Mathematically impossible for infinite loops
- **Quality validation:** Retry only when extraction quality is poor
- **Audit trail:** Complete cost tracking for business intelligence
- **Circuit breakers:** Automatic processing halt on consecutive failures

---

## 🔧 **Key Technical Decisions**

### **Why Agentic Architecture?**
- **Modularity:** Each Lambda has single responsibility (file routing, classification, extraction)
- **Scalability:** Independent scaling of different processing stages
- **Maintainability:** Clean separation of concerns with clear interfaces
- **Cost optimization:** Fine-grained control over expensive AI model usage

### **Why Two-Stage Processing?**
- **Claude Haiku** for classification: Fast, cheap, sufficient accuracy for routing decisions
- **Claude Sonnet** for extraction: High accuracy required for financial data extraction
- **Escalation logic:** Use expensive model only when cheap model is uncertain

### **Why Hard Retry Limits?**
- **Production lesson learned:** Infinite retry loops can cause $4k+ incidents
- **Maximum 2 attempts:** Handles transient failures without runaway costs
- **Quality validation:** Only retry when extraction is genuinely poor
- **Graceful degradation:** Return best-effort results when both attempts fail

---

## 📊 **Production Readiness Features**

### **Infrastructure**
- ✅ **Multi-environment support** (dev/staging/prod)
- ✅ **Multi-region deployment** ready
- ✅ **Resource naming conventions** prevent conflicts
- ✅ **Encryption and security** built-in from day one

### **Error Handling**
- ✅ **Dead letter queues** for poison message handling
- ✅ **Comprehensive logging** with structured audit trails
- ✅ **Graceful degradation** on AI service failures
- ✅ **Circuit breaker patterns** prevent cascading failures

### **Monitoring & Observability**
- ✅ **Cost tracking** with business intelligence metadata
- ✅ **Processing metrics** for performance monitoring
- ✅ **Confidence scoring** for human review triggers
- ✅ **Retry attempt auditing** for production debugging

### **Regulatory Compliance**
- ✅ **Complete audit trail** for financial services compliance
- ✅ **Document processing history** with timestamps and reasoning
- ✅ **Model decision explanations** for regulatory review
- ✅ **Data retention policies** with TTL configurations


---

## 🚀 **Future Enhancements**

### **Immediate Next Steps**
- Deploy Lambda functions with CloudFormation compute stack
- Add API Gateway for external system integration
- Implement real-time cost monitoring with CloudWatch alarms

### **Advanced Features**
- RAG system with UCP600 regulation knowledge base
- A/B testing framework for prompt optimization
- Multi-language document support
- Additional document types (Certificates of Origin, Insurance Certificates)

---

## 📝 **Development Notes**

### **Lessons Learned**
- **DynamoDB requires Decimal types** for financial data (not float)
- **Claude responses are non-deterministic** - robust parsing essential
- **Infinite retry loops** can cause massive costs - hard limits mandatory
- **Testing strategy** should focus on highest-risk failure points

### **Production Considerations**
- All financial calculations use 6-decimal precision for micro-dollar accuracy
- SQS message processing includes loop detection to prevent infinite cycles
- Prompt management separated from code for version control and A/B testing
- Complete audit trail stored for regulatory compliance and debugging

---

## 🏆 **Technical Highlights**

This system demonstrates several advanced production ML engineering concepts:

- **Agentic AI Architecture:** Modular, orchestrated processing pipeline
- **Cost Engineering:** 45% cost reduction through intelligent model selection  
- **Production Safety:** Hard limits prevent infinite loop incidents
- **Financial Precision:** Decimal-based calculations for banking compliance
- **Strategic Testing:** Focus on highest-risk business logic rather than comprehensive coverage
- **Regulatory Awareness:** Complete audit trails and explainable AI decisions

**Built for enterprise trade finance automation with production-grade reliability and cost optimization.**