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
	# Runtime packages
	apk add --no-cache \
		mediainfo \
		tzdata \
		unrar \
	&& \
	# Cleanup
	rm -rf \
		/var/cache/apk/

# Install app
COPY . /app/medusa/

# Ports and Volumes
EXPOSE 8081
VOLUME /config /downloads /tv /anime

WORKDIR /app/medusa
CMD [ "python", "start.py", "--nolaunch", "--datadir", "/config" ]
