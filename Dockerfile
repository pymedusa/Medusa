FROM lsiobase/alpine.python:3.7
MAINTAINER bobbysteel

# set version label
ARG BUILD_DATE
ARG VERSION
LABEL build_version="Version:- ${VERSION} Build-date:- ${BUILD_DATE}"

# install packages
RUN \
 apk add --no-cache \
	--repository http://nl.alpinelinux.org/alpine/edge/community \
	mediainfo gdbm py-gdbm

# install app
COPY . /app/medusa/

# copy local files
COPY .docker/root/ /

# ports and volumes
EXPOSE 8081
VOLUME /config /downloads /tv /anime
