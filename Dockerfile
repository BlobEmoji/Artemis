FROM python:3.11

WORKDIR /opt/artemis
ADD requirements.txt .

RUN python -m pip install -r requirements.txt
