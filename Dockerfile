FROM python:3.11

RUN mkdir /app
WORKDIR /app
COPY ./pong .

RUN pip install -r ./requirements.txt

WORKDIR /app/pong
RUN mkdir logs
RUN touch logs/debug.log

cat << EOF > /tmp/yourfilehere
These contents will be written to the file.
        This line is indented.
EOF

RUN cat << EOF > start.sh
#!/bin/bash

python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn --bind 0.0.0.0:8000 --workers 3 --worker-class uvicorn.workers.UvicornWorker pong.asgi:application
EOF

RUN chmod +x start.sh

EXPOSE 8000

CMD ["/bin/sh", "-c", "/app/pong/start.sh"]

