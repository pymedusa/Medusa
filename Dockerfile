FROM lsiobase/alpine.python:3.9
MAINTAINER a10kiloham

# set version label
ARG BUILD_DATE
ARG VERSION
LABEL build_version="Version:- ${VERSION} Build-date:- ${BUILD_DATE}"

RUN apk add --no-cache python3 && \
    python3 -m ensurepip && \
    rm -r /usr/lib/python*/ensurepip && \
    pip3 install --upgrade pip setuptools && \
    if [ ! -e /usr/bin/pip ]; then ln -s pip3 /usr/bin/pip ; fi && \
    if [[ ! -e /usr/bin/python ]]; then rm /usr/bin/python; fi && \
    ln -sf /usr/bin/python3.6 /usr/bin/python && \
    rm -r /root/.cache

# install packages
RUN \
 apk add --no-cache \
        --repository http://nl.alpinelinux.org/alpine/edge/community \
        mediainfo

# install app
COPY . /app/medusa/

# copy local files
COPY .docker/root/ /

# ports and volumes
EXPOSE 8081
VOLUME /config /downloads /tv /anime
