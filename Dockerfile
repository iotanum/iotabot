FROM python:3.9-slim

WORKDIR /iotabot

COPY . .

RUN apt-get update

RUN pip install --upgrade pip

RUN pip install -r requirements.txt

CMD [ "python", "-u", "./launcher.py" ]
