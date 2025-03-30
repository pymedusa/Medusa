# Python, Alpine and Unrar versions
ARG PYTHON_VERSION=3.11
ARG ALPINE_VERSION=3.21
ARG UNRAR_VERSION=7.1.3
FROM python:${PYTHON_VERSION}-alpine${ALPINE_VERSION} AS builder

# Build arguments
ARG TARGETARCH
ARG CXXFLAGS
ARG JOBS=${JOBS:-$(nproc)}
ARG GIT_BRANCH
ARG GIT_COMMIT
ARG BUILD_DATE

# Metadata labels for maintainability
LABEL maintainer="pymedusa"
LABEL build_version="Branch: ${GIT_BRANCH} | Commit: ${GIT_COMMIT} | Build-Date: ${BUILD_DATE}"

# Build stage
WORKDIR /unrar
RUN \
  echo "**** install build dependencies ****" && \
  apk add --no-cache --virtual=build-dependencies \
    build-base \
    curl \
    tar \
    linux-headers && \
  echo "**** install unrar from source ****" && \
  mkdir -p /tmp/unrar && \
  curl -o \
    /tmp/unrar.tar.gz -L \
    "https://www.rarlab.com/rar/unrarsrc-${UNRAR_VERSION}.tar.gz" && \
  tar xf \
    /tmp/unrar.tar.gz -C \
    /unrar --strip-components=1 && \
  sed -i 's|LDFLAGS=-pthread|LDFLAGS=-pthread -static|' makefile && \
  if [ -z "$CXXFLAGS" ]; then \
    if [ "$TARGETARCH"x = "amd64"x ]; then \
      CXXFLAGS='-march=x86-64'; \
    elif [ "$TARGETARCH"x = "arm64"x ]; then \
      CXXFLAGS='-march=armv8-a+crypto+crc'; \
    elif [ "$TARGETARCH"x = "arm"x ]; then \
      CXXFLAGS='-march=armv7-a -mfloat-abi=hard -mfpu=neon'; \
    fi; \
  fi && \
  sed -i "s|CXXFLAGS=-march=native|CXXFLAGS=$CXXFLAGS|" makefile && \
  make -j ${JOBS} && \
  echo "**** cleanup ****" && \
  apk del --purge \
    build-dependencies && \
  rm -rf \
    /root/.cache \
    /tmp/*

# Final image
FROM python:${PYTHON_VERSION}-alpine${ALPINE_VERSION}

# Runtime environment
ENV MEDUSA_COMMIT_BRANCH=$GIT_BRANCH \
    MEDUSA_COMMIT_HASH=$GIT_COMMIT \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install runtime dependencies
RUN --mount=type=cache,target=/var/cache/apk \
    apk add --no-cache \
        mediainfo \
        p7zip \
        ffmpeg \
        libstdc++

# Application setup
COPY --from=builder /unrar/unrar /usr/local/bin/
COPY . /app/medusa/

# Security improvements
RUN adduser -D -u 1000 medusa && \
    chown -R medusa:medusa /app && \
    find /app -type d -exec chmod 755 {} \+ && \
    find /app -type f -exec chmod 644 {} \+

USER medusa
WORKDIR /app/medusa
EXPOSE 8081
VOLUME /config /downloads /tv /anime

ENTRYPOINT ["runscripts/init.docker"]
