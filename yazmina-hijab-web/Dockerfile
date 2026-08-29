# ── Stage 1: Build React frontend ──────────────────────────────────
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --legacy-peer-deps 2>/dev/null || npm install
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python backend + serve frontend ──────────────────────
FROM python:3.11-slim
WORKDIR /app

# Install system deps for psycopg2
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy built frontend into backend/frontend/dist (main.py serves from here)
COPY --from=frontend-builder /app/frontend/dist ./backend/frontend/dist

WORKDIR /app/backend

# Expose port (Koyeb sets PORT env var)
EXPOSE 8000

# Run with uvicorn — gunicorn needs eventlet/gevent for async, uvicorn is simpler
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
