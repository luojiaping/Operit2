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
# statically linked x86_64 CLI target needs a musl toolchain, installed below.
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
        libayatana-appindicator3-dev \
        libclang-18-dev \
        libgstreamer-plugins-base1.0-dev \
        libgstreamer1.0-dev \
        libgtk-3-dev \
        liblzma-dev \
        libwebkit2gtk-4.1-dev \
        lld \
        llvm-18 \
        make \
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

# musl-tools ships only the C driver, and the GNU libstdc++ headers cannot be
# combined with musl, while the native inference engines are C++. Install a
# toolchain that is itself built against musl and carries its own libstdc++.
ARG MUSL_CROSS_SHA256=c5d410d9f82a4f24c549fe5d24f988f85b2679b452413a9f7e5f7b956f2fe7ea
RUN curl -fsSL --retry 6 --retry-delay 5 --retry-all-errors \
        "https://musl.cc/x86_64-linux-musl-cross.tgz" -o /tmp/musl-cross.tgz \
    && echo "${MUSL_CROSS_SHA256}  /tmp/musl-cross.tgz" | sha256sum -c - \
    && tar -xzf /tmp/musl-cross.tgz -C /opt \
    && rm /tmp/musl-cross.tgz \
    && printf '%s\n' \
        '#!/bin/sh' \
        'exec /opt/x86_64-linux-musl-cross/bin/x86_64-linux-musl-gcc "$@"' \
        > /usr/local/bin/musl-gcc \
    && printf '%s\n' \
        '#!/bin/sh' \
        'exec /opt/x86_64-linux-musl-cross/bin/x86_64-linux-musl-g++ "$@"' \
        > /usr/local/bin/musl-g++ \
    && chmod +x /usr/local/bin/musl-gcc /usr/local/bin/musl-g++ \
    && printf '#include <string>\n#include <vector>\nint main() { std::vector<std::string> values{"ok"}; return values.at(0).size() == 2 ? 0 : 1; }\n' \
        > /tmp/musl-cxx-smoke.cc \
    && musl-g++ -static -o /tmp/musl-cxx-smoke /tmp/musl-cxx-smoke.cc \
    && /tmp/musl-cxx-smoke \
    && rm -f /tmp/musl-cxx-smoke /tmp/musl-cxx-smoke.cc

# V8's GN toolchain consumes the musl tree as a sysroot, which it expects to
# contain usr/include and usr/lib rather than the prefix layout GCC uses.
RUN mkdir -p /opt/musl-sysroot/usr \
    && ln -s /opt/x86_64-linux-musl-cross/x86_64-linux-musl/include /opt/musl-sysroot/usr/include \
    && ln -s /opt/x86_64-linux-musl-cross/x86_64-linux-musl/lib /opt/musl-sysroot/usr/lib \
    && ln -s /opt/x86_64-linux-musl-cross/x86_64-linux-musl/lib /opt/musl-sysroot/lib

# cmake-rs runs CMake with LC_ALL=C, and CMake's archive reader cannot convert
# MNN's UTF-8 paths in that locale. Unpack the pinned source here and hand it to
# FetchContent through OPERIT_MNN_SOURCE instead. The source-dir override skips
# FetchContent's PATCH_COMMAND, so run PatchMnnBuild.cmake against the tree.
ARG MNN_VERSION=3.6.1
COPY hosts/common/operit-host-local-inference/native/PatchMnnBuild.cmake /opt/operit-native/PatchMnnBuild.cmake
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

# V8's source build embeds third_party/icu/common/icudtl.dat, which the v8
# crate does not ship. Take the data file from the ICU revision V8 pins.
ARG ICU_DATA_SHA256=9f48c7f9c7c94d516a14870707e910ab94d75ae640ff6842c4af53276cd26ebe
RUN curl -fsSL --retry 6 --retry-delay 5 --retry-all-errors \
        "https://chromium.googlesource.com/chromium/deps/icu/+/d578f2e8b7bd5938e21cfb6bf15c079e0aa5b738/common/icudtl.dat?format=TEXT" \
        -o /tmp/icudtl.dat.b64 \
    && mkdir -p /opt/operit-v8 \
    && base64 -d /tmp/icudtl.dat.b64 > /opt/operit-v8/icudtl.dat \
    && echo "${ICU_DATA_SHA256}  /opt/operit-v8/icudtl.dat" | sha256sum -c - \
    && rm -f /tmp/icudtl.dat.b64

# The static musl CLI compiles V8 from source. Its build needs Clang 21+ for
# the GN toolchain and for bindgen, which Ubuntu 24.04 does not ship.
RUN curl -fsSL https://apt.llvm.org/llvm-snapshot.gpg.key \
        -o /usr/share/keyrings/llvm-snapshot.gpg.key \
    && printf '%s\n' \
        "deb [signed-by=/usr/share/keyrings/llvm-snapshot.gpg.key] http://apt.llvm.org/noble/ llvm-toolchain-noble-21 main" \
        > /etc/apt/sources.list.d/llvm.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        clang-21 \
        libclang-21-dev \
        lld-21 \
    && rm -rf /var/lib/apt/lists/*

# bindgen resolves libclang through OPERIT_LIBCLANG_DIR on Linux hosts.
# V8's GN defaults to Chromium's pinned Clang layout, which the distribution
# compiler does not match, so the v8 crate downloads its own clang and only
# bindgen uses the system libclang.
ENV OPERIT_LIBCLANG_DIR=/usr/lib/llvm-18/lib \
    LIBCLANG_PATH=/usr/lib/llvm-21/lib

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
