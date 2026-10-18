FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

RUN addgroup --system op06 && adduser --system --ingroup op06 op06

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install .

USER op06
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('PORT', '8000')}/health/ready\", timeout=2)"

# Hosting platforms (Render, Railway, Fly, Cloud Run) inject PORT; exec keeps uvicorn as PID 1.
CMD ["sh", "-c", "exec uvicorn op06.api.app:app --host 0.0.0.0 --port \"$PORT\" --proxy-headers --forwarded-allow-ips='*'"]

