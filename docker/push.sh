#!/bin/bash
echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
version=$(grep -Po "(?<=version=([\"']))(([0-9]\.){2}(dev)?[0-9])" setup.py)
docker build --tag paulfariello/stormbot:$version docker/
docker push paulfariello/stormbot:$version
