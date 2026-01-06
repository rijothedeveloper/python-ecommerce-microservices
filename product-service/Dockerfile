FROM python:3.11-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

# Copy to appuser's home, not root's
COPY --from=builder /root/.local /home/appuser/.local

COPY --chown=appuser:appuser . .

USER appuser

# Point to appuser's .local, not root's
ENV PATH=/home/appuser/.local/bin:$PATH

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]