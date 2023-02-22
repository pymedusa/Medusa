# Need this image for the /bin/start-build script.
# Build unrar.  It has been moved to non-free since Alpine 3.15.
# https://wiki.alpinelinux.org/wiki/Release_Notes_for_Alpine_3.15.0#unrar_moved_to_non-free
FROM jlesage/alpine-abuild:3.15 AS unrar
WORKDIR /tmp
RUN \
    mkdir /tmp/aport && \
    cd /tmp/aport && \
    git init && \
    git remote add origin https://github.com/alpinelinux/aports && \
    git config core.sparsecheckout true && \
    echo "non-free/unrar/*" >> .git/info/sparse-checkout && \
    git pull origin 3.15-stable && \
    PKG_SRC_DIR=/tmp/aport/non-free/unrar && \
    PKG_DST_DIR=/tmp/unrar-pkg && \
    mkdir "$PKG_DST_DIR" && \
    /bin/start-build -r && \
    rm /tmp/unrar-pkg/*-doc-* && \
    mkdir /tmp/unrar-install && \
    tar xf /tmp/unrar-pkg/unrar-*.apk -C /tmp/unrar-install

FROM python:3.10.8-alpine3.15
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
		p7zip \
		ffmpeg \
	&& \
	# Cleanup
	rm -rf \
		/var/cache/apk/

# Install app
COPY . /app/medusa/

# Copy unrar bin
COPY --from=unrar /tmp/unrar-install/usr/bin/unrar /usr/bin/

# Ports and Volumes
EXPOSE 8081
VOLUME /config /downloads /tv /anime

WORKDIR /app/medusa
CMD [ "runscripts/init.docker" ]
