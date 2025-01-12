FROM python:3.13.0-slim

WORKDIR /iotabot

COPY . .

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

RUN pip install -r req

CMD ["python", "-u", "main.py"]
