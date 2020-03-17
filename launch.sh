#!/bin/sh

docker run --rm --memory=1g --cpus=0.5 --volume="$(pwd)/work:/home/jovyan/work:rw" stem-bot python bot.py $1
