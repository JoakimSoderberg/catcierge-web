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

#
# Debian packages:
#
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys C7917B12
RUN echo deb http://ppa.launchpad.net/chris-lea/node.js/ubuntu trusty main > /etc/apt/sources.list.d/nodejs.list
#RUN add-apt-repository ppa:chris-lea/node.js
RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get -y dist-upgrade
RUN	apt-get install -y \
		build-essential \
		python2.7 \
		python2.7-dev \
		python-pip \
		libzmq-dev \
		nodejs \
		git

#
# Pip packages (Python):
#
ADD ./requirements.txt /home/tornado/catcierge-web/requirements.txt
RUN pip install -r requirements.txt

#
# npm packages (javascript modules):
#
ADD ./package.json /home/tornado/catcierge-web/package.json
RUN npm install -g
RUN npm install -g bower

RUN chown -R tornado: /home/tornado/
USER tornado

#
# Bower packages (css/frontend):
#
RUN mkdir -p /home/tornado/catcierge-web/bower_components
ADD ./bower.json /home/tornado/catcierge-web/bower.json
RUN bower install

#
# Add the rest of the sources.
#
ADD . /home/tornado/catcierge-web

#
# Compile less files to css.
#
RUN $(npm bin)/gulp

ENTRYPOINT ["python", "catcierge-web.py", "--docker", "--image_path=/home/tornado/catcierge-images"]
