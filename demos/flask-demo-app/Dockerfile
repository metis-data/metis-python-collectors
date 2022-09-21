FROM python:3.10.3-alpine3.15

RUN apk add build-base

RUN set -ex && \
    apk add --no-cache gcc musl-dev

RUN set -ex && \
    rm -f /usr/libexec/gcc/x86_64-alpine-linux-musl/6.4.0/cc1obj && \
    rm -f /usr/libexec/gcc/x86_64-alpine-linux-musl/6.4.0/lto1 && \
    rm -f /usr/libexec/gcc/x86_64-alpine-linux-musl/6.4.0/lto-wrapper && \
    rm -f /usr/bin/x86_64-alpine-linux-musl-gcj

RUN apk add --no-cache postgresql-dev
RUN apk add --no-cache mysql-dev


RUN pip install psycopg2

WORKDIR /app

COPY requirements.txt requirements.txt

COPY ./templates ./templates
COPY bookmanager.py bookmanager.py

RUN pip3 install -r requirements.txt

EXPOSE 5011

CMD [ "python3", "bookmanager.py" ]
