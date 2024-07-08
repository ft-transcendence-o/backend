FROM python:3.11

RUN mkdir /app
WORKDIR /app
COPY ./pong .

RUN pip install -r ./requirements.txt
RUN pip install uvicorn gunicorn

WORKDIR /app/pong
RUN echo "gunicorn --bind 0.0.0.0:8000 --workers 3 --worker-class uvicorn.workers.UvicornWorker pong.asgi:application" > start.sh
RUN chmod +x start.sh

EXPOSE 8000
CMD /app/pong/start.sh
