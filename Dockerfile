# Multi-stage build: build the React frontend, then run the FastAPI backend
# which serves both the API and the built frontend from a single service.

# --- Stage 1: build the frontend ---
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# --- Stage 2: backend + built frontend ---
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# bring in the compiled frontend from stage 1
COPY --from=frontend /app/frontend/dist ./frontend/dist
# Railway provides $PORT; default to 8000 locally
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]
