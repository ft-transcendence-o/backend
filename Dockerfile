FROM python:3.11

RUN mkdir /app
WORKDIR /app
COPY ./pong .

COPY ./conf/requirements.txt /tmp
COPY ./conf/start-django.sh /tmp

RUN chmod +x /tmp/start-django.sh
RUN chmod +x /tmp/requirements.txt

RUN pip install -r /tmp/requirements.txt

EXPOSE 8000

# WORKDIR /app/pong
CMD ["/bin/sh", "-c", "/tmp/start-django.sh"]
