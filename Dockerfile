FROM python:3.9-alpine

WORKDIR /iotabot

COPY . .

RUN apk update && apk add postgresql-dev gcc python3-dev musl-dev linux-headers libxml2-dev libxslt-dev curl

RUN pip install --upgrade pip

RUN pip install -r requirements.txt

CMD [ "python", "-u", "./launcher.py" ]
