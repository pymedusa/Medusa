FROM python:${PYTHON_VERSION}-alpine${ALPINE_VERSION} AS builder
# Python, Alpine and Unrar versions
ARG PYTHON_VERSION=3.11
ARG ALPINE_VERSION=3.21
ARG UNRAR_VERSION=7.1.6

# Build arguments
ARG TARGETARCH
ARG CXXFLAGS
ARG JOBS=${JOBS:-$(nproc)}

# Build stage - Part 1: Install dependencies and download source
WORKDIR /unrar
RUN \
  echo "**** install build dependencies ****" && \
  apk add --no-cache --virtual=build-dependencies \
    build-base \
    curl \
    linux-headers && \
  echo "**** download unrar source ****" && \
  mkdir -p /unrar && \
  wget "https://www.rarlab.com/rar/unrarsrc-${UNRAR_VERSION}.tar.gz" \
    -O /tmp/unrar.tar.gz

# Build stage - Part 2: Extract, build, and clean up
RUN \
  echo "**** extract and build unrar ****" && \
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
ARG GIT_BRANCH
ARG GIT_COMMIT
ARG BUILD_DATE

# Metadata labels for maintainability
LABEL maintainer="pymedusa"
LABEL build_version="Branch: ${GIT_BRANCH} | Commit: ${GIT_COMMIT} | Build-Date: ${BUILD_DATE}"

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
