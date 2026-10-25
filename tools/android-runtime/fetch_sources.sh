#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
downloads_dir="$script_dir/downloads"
sources_dir="$script_dir/sources"

mkdir -p "$downloads_dir" "$sources_dir"

# Fixed upstream archives shared with the Windows script; keep both lists in sync.
items=(
    "busybox-1.38.0|https://busybox.net/downloads/busybox-1.38.0.tar.bz2|busybox-1.38.0.tar.bz2|34F9EA6FF8636F2C9241153B9114EEFA9E65674A45318AE1EF95BB5F31C53BB2|busybox-1.38.0"
    "termux-proot-v5.1.107.78|https://github.com/termux/proot/archive/refs/tags/v5.1.107.78.tar.gz|termux-proot-v5.1.107.78.tar.gz|F3377BA49DCD833370420C34C5081B4C243ECBB85B2A9881A4F4586012599AFA|proot-5.1.107.78"
    "talloc-2.4.3|https://www.samba.org/ftp/talloc/talloc-2.4.3.tar.gz|talloc-2.4.3.tar.gz|DC46C40B9F46BB34DD97FE41F548B0E8B247B77A918576733C528E83ABD854DD|talloc-2.4.3"
    "bash-5.2.37|https://ftp.gnu.org/gnu/bash/bash-5.2.37.tar.gz|bash-5.2.37.tar.gz|9599B22ECD1D5787AD7D3B7BF0C59F312B3396D1E281175DD1F8A4014DA621FF|bash-5.2.37"
)

for item in "${items[@]}"; do
    IFS='|' read -r name url archive expected_sha256 extracted <<< "$item"
    archive_path="$downloads_dir/$archive"

    echo "Downloading $name"
    curl -fL --retry 5 --retry-delay 2 --retry-connrefused \
        --connect-timeout 30 -o "$archive_path" "$url"

    actual_sha256="$(sha256sum "$archive_path" | awk '{ print toupper($1) }')"
    if [ "$actual_sha256" != "$expected_sha256" ]; then
        echo "$archive SHA256 mismatch: $actual_sha256" >&2
        exit 1
    fi

    extract_path="$sources_dir/$extracted"
    rm -rf "$extract_path"
    tar -xf "$archive_path" -C "$sources_dir"
done
