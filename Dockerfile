FROM python:3.9-slim

WORKDIR /iotabot

COPY . .

RUN apt-get update \
    && apt-get install postgresql-dev gcc \
       python3-dev musl-dev linux-headers \
       libxml2-dev libxslt-dev curl

RUN pip install --upgrade pip

RUN pip install -r requirements.txt

CMD [ "python", "-u", "./launcher.py" ]
