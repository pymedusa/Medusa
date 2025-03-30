# Python, Alpine and Unrar versions
ARG PYTHON_VERSION=3.11.8
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
RUN --mount=type=cache,target=/var/cache/apk \
    apk add --no-cache --virtual .build-deps \
        build-base \
        curl \
        linux-headers && \
    curl -fsSL -o /tmp/unrar.tar.gz \
        "https://www.rarlab.com/rar/unrarsrc-${UNRAR_VERSION}.tar.gz" && \
    tar xzf /tmp/unrar.tar.gz --strip-components=1 && \
    case "${TARGETARCH}" in \
        "amd64") CXXFLAGS="-march=x86-64" ;; \
        "arm64") CXXFLAGS="-march=armv8-a+crypto+crc" ;; \
        "arm")   CXXFLAGS="-march=armv7-a -mfloat-abi=hard -mfpu=neon" ;; \
    esac && \
    sed -i "s/LDFLAGS=-pthread/LDFLAGS=-pthread -static/" makefile && \
    sed -i "s/CXXFLAGS=-march=native/CXXFLAGS=${CXXFLAGS}/" makefile && \
    make -j${JOBS} && \
    apk del --purge .build-deps

# Final image
FROM python:${PYTHON_VERSION}-alpine${ALPINE_VERSION}

# Metadata labels for runtime image
LABEL maintainer="pymedusa"
LABEL version="1.0"
LABEL description="Medusa application Docker container"
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
