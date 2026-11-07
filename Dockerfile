FROM python:3.12-slim-trixie

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sql/ sql/
COPY ridehail/ ridehail/

ENTRYPOINT ["python", "-m", "ridehail"]
CMD ["close"]
