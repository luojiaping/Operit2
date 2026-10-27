#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path

from common import (
    DIST_DIR,
    release_asset_name,
    FLUTTER_APP_DIR,
    compress_tar_gz,
    flutter_command,
    flutter_pub_get,
    generate_dart_proxy_artifacts,
    host_arch,
    run,
)


# Parses command-line options for the Linux Flutter build.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Operit2 Linux Flutter app.")
    parser.add_argument("--build-name")
    parser.add_argument("--build-number")
    parser.add_argument("--archive-path", type=Path)
    parser.add_argument("--enforce-lockfile", action="store_true")
    return parser.parse_args()


# Verifies that the bundle ships the bridge and the engine it links against.
def verify_bundle_libraries(bundle: Path) -> None:
    bridge = bundle / "lib" / "liboperit_flutter_bridge.so"
    engine = bundle / "lib" / "liboperit_local_llm.so"
    for library in (bridge, engine):
        if not library.is_file():
            raise RuntimeError(f"Linux bundle is missing {library.name}")
    result = subprocess.run(["ldd", str(bridge)], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"ldd failed for {bridge.name}: {result.stderr.strip()}")
    unresolved = [line.strip() for line in result.stdout.splitlines() if "not found" in line]
    if unresolved:
        raise RuntimeError("Linux bundle has unresolved libraries: " + "; ".join(unresolved))


# Builds the Linux Flutter app and writes a release archive.
def main() -> int:
    args = parse_args()
    generate_dart_proxy_artifacts()
    flutter_pub_get(enforce_lockfile=args.enforce_lockfile)
    command = [flutter_command(), "build", "linux", "--release", "--no-pub"]
    if args.build_name:
        command.extend(["--build-name", args.build_name])
    if args.build_number:
        command.extend(["--build-number", args.build_number])
    run(command, cwd=FLUTTER_APP_DIR)
    bundle = FLUTTER_APP_DIR / "build" / "linux" / "x64" / "release" / "bundle"
    verify_bundle_libraries(bundle)
    archive_path = args.archive_path or DIST_DIR / release_asset_name("app", "linux", host_arch(), "tar.gz")
    compress_tar_gz(bundle, archive_path)
    print(f"Linux archive: {archive_path}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
