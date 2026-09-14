FROM python:3.12-slim

WORKDIR /app
COPY trigger_incident.py .

RUN useradd --create-home --shell /usr/sbin/nologin appuser
USER appuser

ENTRYPOINT ["python3", "trigger_incident.py"]
