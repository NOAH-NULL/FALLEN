FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all repository files into /app
COPY . .

# Set PYTHONPATH AFTER copying so Python sees the whole folder tree
ENV PYTHONPATH=/app:/app/*

CMD ["python", "-m", "bot"]
