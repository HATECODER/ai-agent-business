FROM python:3.13.2-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.lock.txt ./
RUN python -m pip install --no-cache-dir --requirement requirements.lock.txt

COPY . .
RUN chmod +x scripts/start_render.sh

EXPOSE 10000
CMD ["./scripts/start_render.sh"]
