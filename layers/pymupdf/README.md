# PyMuPDF Lambda Layer

This directory contains the Docker-based build system for creating a PyMuPDF Lambda layer compatible with AWS Lambda runtime.

## 🎯 Purpose

The PyMuPDF layer provides PDF processing capabilities for Lambda functions, specifically for converting PDF documents to high-quality PNG images for AI/ML processing pipelines.

## 📦 Layer Contents

- **PyMuPDF 1.24.13**: High-performance PDF processing library
- **boto3**: AWS SDK for Python
- **Pillow**: Python Imaging Library for additional image processing

## 🏗️ Building the Layer

### Prerequisites
- Docker installed and running
- PowerShell (Windows) or bash (Linux/Mac)
- AWS CLI configured for layer deployment

### Build Process

```powershell
# Navigate to the layer directory
cd layers/pymupdf

# Build the layer using Docker
.\build-layer.ps1

# The layer zip will be created at: output/pymupdf-layer.zip
```

### Deploy to AWS

```bash
# Upload layer to AWS Lambda
aws lambda publish-layer-version \
    --layer-name pymupdf-layer \
    --zip-file fileb://output/pymupdf-layer.zip \
    --compatible-runtimes python3.11 \
    --description "PyMuPDF layer for PDF processing"

# Note the LayerVersionArn from the response
```

## 🔧 Docker Build Details

The build process uses Amazon Linux 2023 to ensure Lambda compatibility:

1. **Base Image**: amazonlinux:2023 (matches Lambda runtime)
2. **Dependencies**: Installs gcc, make for compiling native extensions
3. **Layer Structure**: Creates proper `/opt/python` directory structure
4. **Compression**: Creates optimized zip file for Lambda deployment

## 📋 Usage in Lambda Functions

```python
import fitz  # PyMuPDF (available from layer)
import boto3  # Available from layer

def lambda_handler(event, context):
    # Open PDF document
    doc = fitz.open(stream=pdf_data, filetype="pdf")
    
    # Process pages...
    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
        png_data = pix.tobytes("png")
        # ... upload to S3, etc.
```

## 🎯 Benefits

- **Performance**: Native C libraries for fast PDF processing
- **Quality**: High-DPI rendering (144 DPI) for better OCR results
- **Consistency**: Docker ensures reproducible builds across environments
- **Efficiency**: Shared layer reduces individual Lambda function size

## 🔍 Troubleshooting

### Common Issues

1. **Docker build fails**: Ensure Docker is running and has internet access
2. **Layer too large**: The layer should be ~50MB - if larger, check dependencies
3. **Import errors**: Verify the layer is attached to your Lambda function

### Build Verification

```bash
# Extract and inspect layer contents
unzip -l output/pymupdf-layer.zip | head -20

# Check for PyMuPDF installation
unzip -q output/pymupdf-layer.zip -d temp/
ls temp/python/fitz/
```

## 📊 Performance Metrics

- **Layer Size**: ~45MB compressed
- **Cold Start Impact**: +200-300ms for first invocation
- **Processing Speed**: ~2-3 seconds per page at 144 DPI
- **Memory Usage**: ~512MB recommended minimum