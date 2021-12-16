FROM python:3.9-slim

WORKDIR /iotabot

COPY . .

RUN pip install -r requirements.txt

CMD [ "python", "-u", "./launcher.py" ]
