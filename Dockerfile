FROM python:3.9-alpine

WORKDIR /iotabot

COPY . .

RUN apk update && apk add postgresql-dev gcc python3-dev musl-dev

RUN pip install -r requirements.txt

CMD [ "python", "-u", "./launcher.py" ]
