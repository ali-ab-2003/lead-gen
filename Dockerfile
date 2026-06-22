# Pipeline image. Based on the Playwright image so the optional DIY fallback
# scraper has its browser deps available; the default Apify path doesn't need them.
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

# Install Python deps first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code.
COPY . .

# Default command runs the full daily pipeline.
ENTRYPOINT ["python", "main.py"]
