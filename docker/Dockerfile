FROM python:3-stretch

WORKDIR /app

COPY . /app

RUN apt update
RUN apt install -y sox alsa-utils libsox-fmt-mp3
RUN pip3 install --trusted-host pypi.python.org -r requirements.txt


CMD stormbot --help

