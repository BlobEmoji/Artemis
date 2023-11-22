FROM python:3.11-alpine

WORKDIR /opt/artemis
ADD requirements.txt .

RUN apk add git

RUN apk add font-dejavu
RUN python -m pip install -r requirements.txt

CMD python -m src
