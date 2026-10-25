# Linux App and CLI build environment for CNB.
#
# The image carries the whole toolchain so pipeline stages only run project
# scripts. It is rebuilt by CNB whenever this file or the pinned Flutter
# version changes.
FROM ubuntu:24.04

# CNB builds images inside a user namespace, where tar cannot chown to the
# archive's original uid. Flutter unpacks SDK archives with tar.
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TAR_OPTIONS=--no-same-owner

# The Flutter Linux desktop build needs GTK 3, WebKitGTK, and GStreamer; the
# statically linked x86_64 CLI target needs the musl toolchain.
RUN apt-get update && apt-get install -y --no-install-recommends \
        bison \
        build-essential \
        bzip2 \
        ca-certificates \
        clang \
        cmake \
        curl \
        file \
        flex \
        gawk \
        git \
        gzip \
        libclang-18-dev \
        libgstreamer-plugins-base1.0-dev \
        libgstreamer1.0-dev \
        libgtk-3-dev \
        liblzma-dev \
        libwebkit2gtk-4.1-dev \
        lld \
        llvm-18 \
        make \
        musl-tools \
        ninja-build \
        patch \
        pkg-config \
        python3 \
        python3-venv \
        tar \
        unzip \
        xz-utils \
        zip \
    && rm -rf /var/lib/apt/lists/*

# bindgen resolves libclang through OPERIT_LIBCLANG_DIR on Linux hosts.
ENV OPERIT_LIBCLANG_DIR=/usr/lib/llvm-18/lib

ARG NODE_VERSION=22.23.2
RUN curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" \
        -o /tmp/node.tar.xz \
    && tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 \
    && rm /tmp/node.tar.xz \
    && node --version \
    && npm --version \
    && npm install --global pnpm@10.7.0 typescript@5.9.3 \
    && pnpm --version \
    && tsc --version

ARG RUST_VERSION=1.95.0
ENV RUSTUP_HOME=/usr/local/rustup \
    CARGO_HOME=/usr/local/cargo \
    PATH=/usr/local/cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
        | sh -s -- -y --no-modify-path --profile minimal --default-toolchain "${RUST_VERSION}" \
    && rustup target add x86_64-unknown-linux-musl \
    && cargo --version

RUN curl -fsSL "https://storage.googleapis.com/dart-archive/channels/stable/release/latest/sdk/dartsdk-linux-x64-release.zip" \
        -o /tmp/dart.zip \
    && unzip -q /tmp/dart.zip -d /opt \
    && rm /tmp/dart.zip \
    && ln -s /opt/dart-sdk/bin/dart /usr/local/bin/dart \
    && dart --version

ARG FVM_VERSION=4.3.0
ENV FVM_CACHE_PATH=/opt/fvm \
    PUB_CACHE=/opt/pub-cache
RUN dart pub global activate fvm "${FVM_VERSION}" \
    && ln -s /opt/pub-cache/bin/fvm /usr/local/bin/fvm \
    && fvm --version

# Warm the FVM cache with the Flutter fork pinned by the project.
WORKDIR /opt/operit-app
COPY apps/flutter/app/.fvmrc /opt/operit-app/.fvmrc
RUN fvm install --skip-pub-get \
    && fvm flutter precache --web --ohos \
    && git config --global --add safe.directory '*'

WORKDIR /workspace
