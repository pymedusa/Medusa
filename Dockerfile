FROM python:3.10.16-alpine3.21 AS builder

ARG TARGETARCH
ARG CXXFLAGS
ARG UNRAR_VERSION=7.0.9
# Build unrar
WORKDIR /unrar
RUN \
  echo "**** install build dependencies ****" && \
  apk add --no-cache --virtual=build-dependencies \
    build-base \
    curl \
    linux-headers && \
  echo "**** install unrar from source ****" && \
  mkdir /tmp/unrar && \
  curl -o \
    /tmp/unrar.tar.gz -L \
    "https://www.rarlab.com/rar/unrarsrc-${UNRAR_VERSION}.tar.gz" && \
  tar xf \
    /tmp/unrar.tar.gz -C \
    /unrar --strip-components=1 && \
  sed -i 's|LDFLAGS=-pthread|LDFLAGS=-pthread -static|' makefile && \
  if [ -z $CXXFLAGS ]; then \
    if [ "$TARGETARCH"x == "amd64"x ]; then \
      CXXFLAGS='-march=x86-64'; \
    elif [ "$TARGETARCH"x == "arm64"x ]; then \
      CXXFLAGS='-march=armv8-a+crypto+crc'; \
    elif [ "$TARGETARCH"x == "arm"x ]; then \
      CXXFLAGS='-march=armv7-a -mfloat-abi=hard -mfpu=neon'; \
    fi \
  fi && \
  sed -i "s|CXXFLAGS=-march=native|CXXFLAGS=$CXXFLAGS|" makefile && \
  make && \
  echo "**** cleanup ****" && \
  apk del --purge \
    build-dependencies && \
  rm -rf \
    /root/.cache \
    /tmp/*

FROM python:3.10.16-alpine3.21
LABEL maintainer="pymedusa"

ARG GIT_BRANCH
ARG GIT_COMMIT
ENV MEDUSA_COMMIT_BRANCH $GIT_BRANCH
ENV MEDUSA_COMMIT_HASH $GIT_COMMIT

ARG BUILD_DATE
LABEL build_version="Branch: $GIT_BRANCH | Commit: $GIT_COMMIT | Build-Date: $BUILD_DATE"

COPY --from=builder /unrar/unrar /usr/bin
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

# Ports and Volumes
EXPOSE 8081
VOLUME /config /downloads /tv /anime

WORKDIR /app/medusa
CMD [ "runscripts/init.docker" ]
