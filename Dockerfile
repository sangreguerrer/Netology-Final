FROM python:3.12-alpine

RUN apk update && apk add python3-dev gcc libc-dev
# set work directory
WORKDIR /djangoProjectFinalWork


# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# install dependencies
COPY ./requirements.txt /djangoProjectFinalWork
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
# copy project
COPY . /djangoProjectFinalWork/




