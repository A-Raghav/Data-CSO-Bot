FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy specific application files and directories
COPY app.py .
COPY chainlit.md .
COPY README.md .
COPY src/ ./src/
COPY public/ ./public/
COPY cache/ ./cache/
COPY .chainlit/ ./.chainlit/
COPY artifacts/ ./artifacts/

# Expose the port Chainlit will run on
EXPOSE 8000

# Start the application
CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8000"]
