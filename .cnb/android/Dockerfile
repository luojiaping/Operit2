# Android APK build environment for CNB.
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

RUN apt-get update && apt-get install -y --no-install-recommends \
        bison \
        build-essential \
        bzip2 \
        ca-certificates \
        curl \
        file \
        flex \
        gawk \
        git \
        gzip \
        libclang-18-dev \
        liblzma-dev \
        make \
        ninja-build \
        openjdk-17-jdk-headless \
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
    && rustup target add aarch64-linux-android \
    && cargo --version

ENV ANDROID_SDK_ROOT=/opt/android-sdk \
    ANDROID_HOME=/opt/android-sdk \
    ANDROID_NDK_HOME=/opt/android-ndk-r29-beta4
RUN mkdir -p "${ANDROID_SDK_ROOT}/cmdline-tools" \
    && curl -fsSL "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip" \
        -o /tmp/cmdline-tools.zip \
    && unzip -q /tmp/cmdline-tools.zip -d /tmp/cmdline-tools \
    && mv /tmp/cmdline-tools/cmdline-tools "${ANDROID_SDK_ROOT}/cmdline-tools/latest" \
    && rm -rf /tmp/cmdline-tools /tmp/cmdline-tools.zip \
    && yes | "${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin/sdkmanager" --licenses > /dev/null \
    && "${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin/sdkmanager" \
        "platform-tools" \
        "platforms;android-34" \
        "platforms;android-35" \
        "platforms;android-36" \
        "build-tools;35.0.0" \
        "build-tools;36.0.0" \
        "cmake;3.22.1" \
        "ndk;28.2.13676358" \
    && rm -rf "${ANDROID_SDK_ROOT}/.temp" "${ANDROID_SDK_ROOT}/.downloadIntermediates"

# The Android runtime scripts pin NDK r29-beta4 independently of the NDK
# version Flutter's Gradle plugin uses.
RUN curl -fsSL "https://dl.google.com/android/repository/android-ndk-r29-beta4-linux.zip" \
        -o /tmp/ndk.zip \
    && unzip -q /tmp/ndk.zip -d /opt \
    && rm /tmp/ndk.zip \
    && "${ANDROID_NDK_HOME}/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-ar" --version > /dev/null

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
    && fvm flutter config --android-sdk "${ANDROID_SDK_ROOT}" \
    && fvm flutter precache --web --ohos \
    && git config --global --add safe.directory '*'

WORKDIR /workspace
