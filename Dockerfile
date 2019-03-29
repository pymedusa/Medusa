FROM python:3.7-alpine3.9
LABEL maintainer="pymedusa"

ARG GIT_BRANCH
ARG GIT_COMMIT
ENV MEDUSA_COMMIT_BRANCH $GIT_BRANCH
ENV MEDUSA_COMMIT_HASH $GIT_COMMIT

ARG BUILD_DATE
LABEL build_version="Branch: $GIT_BRANCH | Commit: $GIT_COMMIT | Build-Date: $BUILD_DATE"

# Install packages
RUN \
	# Update
	apk update \
	&& \
	# Install build dependencies
	apk add --no-cache --virtual=build-dependencies \
		gcc \
		libc-dev \
		linux-headers \
	&& \
	# Runtime packages
	apk add --no-cache \
		mediainfo \
		unrar \
	&& \
	# Install Python dependencies
	pip install --upgrade \
		psutil \
	&& \
	# Cleanup
	apk del --purge \
		build-dependencies \
	&& \
	rm -rf \
		/var/cache/apk/ \
		~/.cache

# Install app
COPY . /app/medusa/

# Ports and Volumes
EXPOSE 8081
VOLUME /config /downloads /tv /anime

WORKDIR /app/medusa
CMD [ "python", "start.py", "--nolaunch", "--datadir", "/config" ]
