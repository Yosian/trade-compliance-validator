# Use Amazon Linux 2023 for Lambda compatibility
FROM amazonlinux:2023

# Install Python and build dependencies
RUN yum update -y && \
    yum install -y \
    python3 \
    python3-pip \
    gcc \
    gcc-c++ \
    make \
    zip

# Create the layer directory structure
RUN mkdir -p /opt/python

# Copy requirements file
COPY requirements.txt /tmp/

# Install Python packages to the layer directory
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt -t /opt/python/

# Create the zip file for the layer
WORKDIR /opt
RUN zip -r9 /tmp/pymupdf-layer.zip python/

# Simple command to keep container running for file extraction
CMD ["tail", "-f", "/dev/null"]