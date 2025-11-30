# /backend/Dockerfile
FROM python:3.10-slim

WORKDIR /app

# 1. Install dependencies first (Caching layer)
# Ensure you have a requirements.txt with fastapi, uvicorn, etc.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Copy the actual code
COPY . .

# 3. Expose the port we plan to use
EXPOSE 8001

# 4. Start the server
# --host 0.0.0.0 is CRITICAL for Docker networking
# --port 8001 matches our Service/Ingress config
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
