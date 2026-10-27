#!/usr/bin/env python3
"""Stages the V8 sources for the static musl CLI build.

V8's prebuilt musl archive carries Chromium's libc++ under the __Cr ABI
namespace. Expose that libc++ to the native inference engines so the static
binary uses a single C++ runtime, and provide the few libc++ runtime pieces the
archive does not carry (random_device and the thread-exit fallback).
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCKFILE = REPO_ROOT / "apps" / "cli" / "Cargo.lock"
ICU_DATA = Path("/opt/operit-v8/icudtl.dat")
LIBCXX_ROOT = Path("/opt/operit-v8/libcxx")
SUPPLEMENT = Path("/opt/operit-v8/lib/liboperit_cxx_supplement.a")
CLANG = Path("/usr/lib/llvm-21/bin/clang++")
SYSROOT = Path("/opt/musl-sysroot")
GCC_TOOLCHAIN = Path("/opt/x86_64-linux-musl-cross")
# Runtime pieces MNN and llama.cpp need that V8 itself never instantiates.
SUPPLEMENT_SOURCES = (
    "third_party/libc++/src/src/random.cpp",
    "third_party/libc++/src/src/system_error.cpp",
    "third_party/libc++abi/src/src/cxa_thread_atexit.cpp",
)


# Parses command-line options for the V8 source staging step.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage the v8 crate for a musl build.")
    parser.add_argument("--cargo-home", type=Path)
    return parser.parse_args()


# Reads the v8 version the CLI resolves from its lockfile.
def v8_version() -> str:
    lock = LOCKFILE.read_text(encoding="utf-8")
    match = re.search(r'\[\[package\]\]\nname = "v8"\nversion = "([^"]+)"', lock)
    if not match:
        raise RuntimeError(f"{LOCKFILE} does not pin a v8 package")
    return match.group(1)


# Extracts the v8 crate the way cargo would, so it can be patched in place.
def crate_source(cargo_home: Path, version: str) -> Path:
    registry = cargo_home / "registry"
    crate = next((registry / "cache").glob(f"*/v8-{version}.crate"))
    source_root = registry / "src" / crate.parent.name
    crate_dir = source_root / f"v8-{version}"
    if crate_dir.is_dir():
        return crate_dir
    source_root.mkdir(parents=True, exist_ok=True)
    with tarfile.open(crate) as archive:
        archive.extractall(source_root, filter="data")
    # Cargo unpacks the crate itself unless the completion marker is present.
    (crate_dir / ".cargo-ok").write_text(json.dumps({"v": 1}), encoding="utf-8")
    return crate_dir


# Builds the libc++ runtime objects the V8 archive leaves out.
def build_supplement(crate_dir: Path) -> None:
    include_flags = [
        f"-isystem{LIBCXX_ROOT / 'config'}",
        f"-isystem{LIBCXX_ROOT / 'include'}",
        f"-isystem{crate_dir / 'third_party/libc++abi/src/include'}",
        f"-I{crate_dir / 'third_party/libc++abi/src/src'}",
    ]
    flags = [
        "--target=x86_64-unknown-linux-musl",
        f"--sysroot={SYSROOT}",
        f"--gcc-toolchain={GCC_TOOLCHAIN}",
        "-std=c++23",
        "-nostdinc++",
        *include_flags,
        "-DANDROID_HOST_MUSL",
        "-D_LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_NONE",
        "-O2",
        "-fPIC",
    ]
    objects: list[str] = []
    build_dir = SUPPLEMENT.parent / "supplement"
    build_dir.mkdir(parents=True, exist_ok=True)
    sources = [crate_dir / source for source in SUPPLEMENT_SOURCES]
    # llama.cpp enumerates plugin directories through std::filesystem.
    sources.extend(sorted((crate_dir / "third_party/libc++/src/src/filesystem").glob("*.cpp")))
    for source_path in sources:
        output = build_dir / f"{source_path.stem}.o"
        subprocess.run(
            [str(CLANG), *flags, "-c", str(source_path), "-o", str(output)],
            check=True,
        )
        objects.append(str(output))
    SUPPLEMENT.parent.mkdir(parents=True, exist_ok=True)
    SUPPLEMENT.unlink(missing_ok=True)
    subprocess.run(["ar", "rcs", str(SUPPLEMENT), *objects], check=True)


def main() -> int:
    args = parse_args()
    cargo_home = args.cargo_home or Path.home() / ".cargo"
    version = v8_version()
    crate_dir = crate_source(cargo_home, version)
    if ICU_DATA.is_file():
        destination = crate_dir / "third_party" / "icu" / "common" / "icudtl.dat"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ICU_DATA, destination)
    # V8's prebuilt archive is built against the libc++ shipped in this crate.
    # Expose its headers under stable paths so the native engines can use the
    # same ABI (namespace and configuration) instead of libstdc++.
    LIBCXX_ROOT.mkdir(parents=True, exist_ok=True)
    for name, source in (
        ("config", crate_dir / "buildtools" / "third_party" / "libc++"),
        ("include", crate_dir / "third_party" / "libc++" / "src" / "include"),
    ):
        link = LIBCXX_ROOT / name
        link.unlink(missing_ok=True)
        link.symlink_to(source, target_is_directory=True)
    build_supplement(crate_dir)
    print(f"Staged libc++ headers and {SUPPLEMENT.name} for v8 {version}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
