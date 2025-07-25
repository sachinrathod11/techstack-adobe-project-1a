FROM python:3.9-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the solution
COPY persona_processor.py .

# Create input and output directories
RUN mkdir -p /app/input /app/output

# Run the solution
CMD ["python", "persona_processor.py"]