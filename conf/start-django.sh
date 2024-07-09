#!/bin/bash

python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn --bind 0.0.0.0:8000 --workers 3 --worker-class uvicorn.workers.UvicornWorker pong.asgi:application
