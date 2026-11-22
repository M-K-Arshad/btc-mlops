# ---------- Stage 1: builder (installs dependencies) ----------
FROM python:3.10-slim AS builder
WORKDIR /build
COPY app/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- Stage 2: runtime (small final image) ----------
FROM python:3.10-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MODEL_DIR=/app/models \
    PORT=5000

# Create a non-root user
RUN useradd --create-home --uid 1001 appuser

WORKDIR /app
# Copy only the installed packages from the builder stage
COPY --from=builder /install /usr/local
COPY app/app.py .
# Starting model built into the image (used if /app/models is empty)
COPY models/ /app/bundled_models/
RUN mkdir -p /app/models && chown -R appuser:appuser /app

USER appuser
EXPOSE 5000

# Production WSGI server
CMD gunicorn --workers 2 --timeout 60 --bind 0.0.0.0:${PORT} app:app