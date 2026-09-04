FROM python:3.12-slim

WORKDIR /app
COPY send_traffic.py .

RUN useradd --create-home --shell /usr/sbin/nologin appuser
USER appuser

ENTRYPOINT ["python3", "send_traffic.py"]
