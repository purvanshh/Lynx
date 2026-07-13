FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir build wheel && \
    pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim

RUN addgroup --system lynx && adduser --system --group lynx

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY lynx/ lynx/
COPY simulator/ simulator/
COPY scripts/ scripts/

RUN chown -R lynx:lynx /app
USER lynx

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "lynx.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
