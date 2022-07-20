FROM FROM python:3.9.10-bullseye

WORKDIR /iotabot

COPY . .

RUN apt-get update \
    && apt-get install -y \
       libpq-dev libxml2-dev libxslt-dev curl gcc

RUN pip install --upgrade pip

RUN pip install -r requirements.txt

CMD [ "python", "-u", "./launcher.py" ]
