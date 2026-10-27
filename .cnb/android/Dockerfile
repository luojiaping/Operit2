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
        cmake \
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

# Android has no prebuilt rusty_v8 artifact, so the bridge compiles V8 from
# source. prepare_android_v8.py needs libclang 21+ for bindgen and ld.lld for
# Chromium's host toolchain; Ubuntu 24.04 only ships LLVM 18.
RUN curl -fsSL https://apt.llvm.org/llvm-snapshot.gpg.key \
        -o /usr/share/keyrings/llvm-snapshot.gpg.key \
    && printf '%s\n' \
        "deb [signed-by=/usr/share/keyrings/llvm-snapshot.gpg.key] http://apt.llvm.org/noble/ llvm-toolchain-noble-21 main" \
        > /etc/apt/sources.list.d/llvm.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        clang-21 \
        libclang-21-dev \
        libclang-rt-21-dev \
        lld-21 \
    && rm -rf /var/lib/apt/lists/*

# prepare_android_v8.py matches libclang.so.<major>, while libclang-21-dev only
# ships libclang.so -> libclang-21.so.1.
RUN libclang="$(readlink -f /usr/lib/llvm-21/lib/libclang.so)" \
    && test -f "$libclang" \
    && ln -sf "$libclang" /usr/lib/llvm-21/lib/libclang.so.21

# cmake-rs runs CMake with LC_ALL=C, and CMake's archive reader cannot convert
# MNN's UTF-8 paths in that locale. Unpack the pinned source here and hand it to
# FetchContent through OPERIT_MNN_SOURCE instead. The source-dir override skips
# FetchContent's PATCH_COMMAND, so run PatchMnnBuild.cmake against the tree.
ARG MNN_VERSION=3.6.1
COPY core/crates/provider/local-model/native/PatchMnnBuild.cmake /opt/operit-native/PatchMnnBuild.cmake
RUN curl -fsSL "https://codeload.github.com/alibaba/MNN/zip/refs/tags/${MNN_VERSION}" \
        -o /tmp/mnn.zip \
    && echo "93d60848879e68be554c247afe376657630a30652a7d8ec713e9e7d1bbf69260  /tmp/mnn.zip" \
        | sha256sum -c - \
    && unzip -q /tmp/mnn.zip -d /tmp/mnn \
    && mv "/tmp/mnn/MNN-${MNN_VERSION}" /opt/operit-native/mnn \
    && rm -rf /tmp/mnn /tmp/mnn.zip \
    && cd /opt/operit-native/mnn \
    && cmake -P /opt/operit-native/PatchMnnBuild.cmake

ENV OPERIT_MNN_SOURCE=/opt/operit-native/mnn

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

# The Android terminal runtime is built from pinned third-party sources and
# does not depend on the app. Producing it here removes the six-minute runtime
# stage from every pipeline run; the stage only copies the finished assets.
COPY tools/android-runtime/fetch_sources.sh /opt/operit-android-runtime/tools/android-runtime/fetch_sources.sh
COPY tools/android-runtime/build_android_tools_wsl.sh /opt/operit-android-runtime/tools/android-runtime/build_android_tools_wsl.sh
COPY tools/android-runtime/build_alpine_rootfs_wsl.sh /opt/operit-android-runtime/tools/android-runtime/build_alpine_rootfs_wsl.sh
COPY tools/android-runtime/patches/termux-proot-operit-android.patch /opt/operit-android-runtime/tools/android-runtime/patches/termux-proot-operit-android.patch
COPY tools/runtime/verify_alpine_node24.py /opt/operit-android-runtime/tools/runtime/verify_alpine_node24.py
RUN cd /opt/operit-android-runtime \
    && bash tools/android-runtime/fetch_sources.sh \
    && bash tools/android-runtime/build_android_tools_wsl.sh \
    && bash tools/android-runtime/build_alpine_rootfs_wsl.sh \
    && rm -rf tools/android-runtime/downloads tools/android-runtime/sources \
        "$HOME/.cache/operit-android-runtime"

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

# Flutter's Gradle plugin is an included build that resolves its dependencies
# in its own settings script, so the project-level Aliyun mirrors never apply to
# it and it reaches Maven Central directly. An init script runs before every
# settings script, which puts the mirror ahead of the built-in repositories for
# both the app build and the Flutter tool build.
#
# `beforeSettings` is required: the Flutter tool build sets
# RepositoriesMode.FAIL_ON_PROJECT_REPOS, so project repositories are rejected.
# The file is stored outside /root/.gradle as well, because that path is a
# cache volume whose contents shadow the image.
RUN mkdir -p /opt/operit-gradle /root/.gradle/init.d \
    && printf '%s\n' \
        "def aliyunMirrors = [" \
        "    'https://maven.aliyun.com/repository/public'," \
        "    'https://maven.aliyun.com/repository/google'," \
        "    'https://maven.aliyun.com/repository/gradle-plugin'," \
        "]" \
        "" \
        "beforeSettings { settings ->" \
        "    settings.pluginManagement.repositories {" \
        "        aliyunMirrors.each { mirror -> maven { url mirror } }" \
        "    }" \
        "    settings.dependencyResolutionManagement.repositories {" \
        "        aliyunMirrors.each { mirror -> maven { url mirror } }" \
        "    }" \
        "}" \
        > /opt/operit-gradle/aliyun.gradle \
    && cp /opt/operit-gradle/aliyun.gradle /root/.gradle/init.d/aliyun.gradle

WORKDIR /workspace
