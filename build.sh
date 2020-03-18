#!/bin/sh

docker build -t stem-bot:python -f Dockerfile.python .
docker build -t stem-bot:octave -f Dockerfile.octave .
docker build -t stem-bot:R -f Dockerfile.R .
