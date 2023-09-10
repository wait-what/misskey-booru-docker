#!/bin/sh

echo Running the bot
python gelbooru_poster.py

echo Waiting for $INTERVAL_SECONDS seconds
sleep $INTERVAL_SECONDS

echo Starting over
exec ./entrypoint.sh
