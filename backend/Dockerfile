FROM python:3.12-slim

WORKDIR /app

# Install system dependencies needed for Playwright and chromium
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser binaries and system deps
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

# Run db seeding (optional) and launch FastAPI
EXPOSE 8000
CMD ["python", "app/main.py"]
