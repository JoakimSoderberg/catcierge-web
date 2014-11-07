#
# Docker for the Catcierge Web App.
#
# 
#

FROM phusion/baseimage:0.9.15

MAINTAINER Joakim Soderberg <joakim.soderberg@gmail.com>


RUN useradd -m tornado
ENV HOME /home/tornado

RUN mkdir -p /home/tornado/catcierge-images
RUN mkdir -p /home/tornado/catcierge-web

VOLUME /home/tornado/catcierge-images
WORKDIR /home/tornado/catcierge-web

RUN apt-get update
RUN	apt-get install -y \
		nodejs \
		python2.7 \
		python2.7-dev \
		python-pip \
		libzmq-dev

ADD ./requirements.txt /home/tornado/catcierge-web/requirements.txt

RUN pip install -r requirements.txt

ADD . /home/tornado/catcierge-web

USER tornado

# TODO: 
# * How to set ZMQ-host/port?
# * How to connect to Rethinkdb using the link vars?
# * Make the entrypoint a script.
#   http://mike-clarke.com/2013/11/docker-links-and-runtime-env-vars/
# * Add --zmq_uri as cmdline switch in catcierge-web.py
# * Maybe use this https://www.npmjs.org/package/docker-links

ENTRYPOINT ["python", "catcierge-web.py", "--docker", "--image_path=/home/tornado/catcierge-images"]
