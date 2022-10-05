#!/bin/bash
set -x
echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
version=$(grep -Po "(?<=version=([\"']))([0-9]\.[0-9](.dev|b|a|rc|.)[0-9])" setup.py)
docker build --tag paulfariello/stormbot:$version docker/
docker push paulfariello/stormbot:$version
