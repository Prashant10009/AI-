# Dockerfile for DocAI API
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# MongoDB URI
ENV MONGODB_URI= ""
COPY . /app

# Install system dependencies for OCR, image processing, and building Python wheels
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      libpoppler-cpp-dev poppler-utils \
      tesseract-ocr \
      imagemagick \
      libgl1 libsm6 libxrender1 libglib2.0-0 \
      libjpeg-dev zlib1g-dev \
      curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, install headless OpenCV, then install the rest with retries/timeouts
RUN pip install --upgrade pip && \
    pip install --no-cache-dir opencv-python-headless && \
    pip install --no-cache-dir \
      --default-timeout=120 \
      --retries=5 \
      -r requirements.txt

# Expose port and launch Uvicorn
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
