FROM python:3.11-slim AS builder

WORKDIR /app

# Install only essential build dependencies
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libfreetype6-dev \
        libharfbuzz-dev \
        libjpeg-dev \
        libopenjp2-7-dev \
        pkg-config && \
    rm -rf /var/lib/apt/lists/*

# Create a virtual environment
RUN python -m venv /opt/venv

# Enable venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install PyMuPDF
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir PyMuPDF==1.23.*

# Final stage - minimal runtime image
FROM python:3.11-slim

WORKDIR /app

# Install only essential runtime dependencies
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        libfreetype6 \
        libharfbuzz0b \
        libjpeg62-turbo \
        libopenjp2-7 && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Copy the virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Enable venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy the Python script
COPY process_pdfs.py .

# Set Python to not write bytecode files and not buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "/app/process_pdfs.py"]
