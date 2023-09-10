from python:alpine
workdir /app
copy gelbooru_poster.py entrypoint.sh .
run pip install requests
cmd ["./entrypoint.sh"]
