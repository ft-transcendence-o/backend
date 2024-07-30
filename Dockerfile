FROM python:3.11

RUN mkdir /app
WORKDIR /app
COPY . .

RUN pip install -r ./requirements.txt

WORKDIR /app/pong
RUN mkdir logs
RUN touch logs/debug.log

RUN echo '#!/bin/bash\n\n\
python manage.py makemigrations authentication\n\
python manage.py makemigrations game\n\
python manage.py migrate\n\
python manage.py collectstatic --noinput\n\
gunicorn --bind 0.0.0.0:8000 --workers 3 --worker-class uvicorn.workers.UvicornWorker pong.asgi:application' > start.sh

RUN chmod +x start.sh

EXPOSE 8000

CMD ["/bin/sh", "-c", "/app/pong/start.sh"]

