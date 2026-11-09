#!/usr/bin/env python3
r"""Remove compiler working state and old Flutter caches in Operit2.

Keep compiled Cargo dependencies, build-script outputs, fingerprints and app
binaries together. Cargo can need several hashes of the same crate in one build.
Flutter's .last_build_id identifies the build cache to retain.

Usage:
    .\.venv\Scripts\python.exe tools/prune_build_caches.py [--dry-run]
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CARGO_TARGET_DIRS = [
    REPO_ROOT / 'apps/flutter/native/operit-flutter-bridge/target',
    REPO_ROOT / 'core/target',
    REPO_ROOT / 'apps/cli/target',
]
FLUTTER_APP_DIRS = [
    REPO_ROOT / 'apps/flutter/app',
    REPO_ROOT / 'apps/flutter/theme_preview',
]
TEST_CACHE_DIRS = [
    REPO_ROOT / 'apps/flutter/app/build/test_cache',
    REPO_ROOT / 'apps/flutter/packages/operit_theme/build/test_cache',
]
THEME_PREVIEW_DIR = REPO_ROOT / 'build/theme-preview'
ALLOWED_CACHE_DIRS = (
    [target / 'debug/incremental' for target in CARGO_TARGET_DIRS]
    + [app / '.dart_tool/flutter_build' for app in FLUTTER_APP_DIRS]
    + [app / 'build' for app in FLUTTER_APP_DIRS]
    + TEST_CACHE_DIRS
    + [THEME_PREVIEW_DIR]
)


@dataclass(frozen=True)
class CacheEntry:
    category: str
    path: Path
    size: int


def assert_safe_path(path: Path) -> Path:
    resolved = path.resolve()
    if resolved != path.absolute():
        raise ValueError(f'Linked cache path rejected: {path}')
    if not resolved.is_relative_to(REPO_ROOT) or resolved == REPO_ROOT:
        raise ValueError(f'Path outside workspace rejected: {resolved}')
    if not any(resolved == cache or resolved.is_relative_to(cache)
               for cache in ALLOWED_CACHE_DIRS):
        raise ValueError(f'Path outside allowed cache directories: {resolved}')
    return resolved


def compute_size_bytes(path: Path) -> int:
    assert_safe_path(path)
    if not path.is_dir():
        return path.stat().st_size

    def report_error(error):
        raise error

    total = 0
    for root, dirs, files in os.walk(path, followlinks=False, onerror=report_error):
        for name in dirs + files:
            entry = Path(root) / name
            if entry.is_symlink() or entry.resolve() != entry.absolute():
                raise ValueError(f'Linked cache entry rejected: {entry}')
        for name in files:
            total += (Path(root) / name).stat().st_size
    return total


def ensure_no_active_builds():
    if sys.platform != 'win32':
        return
    query = (
        'Get-CimInstance Win32_Process | Where-Object { '
        "$_.Name -match '^(cargo|rustc|MSBuild|cmake|link|flutter)\\.exe$' -or "
        "($_.Name -eq 'dart.exe' -and $_.CommandLine -match "
        "'flutter_tools\\.snapshot.*\\s(build|run)(\\s|$)') "
        '} | Select-Object ProcessId,Name | ConvertTo-Json -Compress'
    )
    result = subprocess.run(
        ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', query],
        check=True, capture_output=True, text=True,
    )
    if result.stdout.strip():
        processes = json.loads(result.stdout)
        raise RuntimeError(f'Build processes are active; cleanup stopped: {processes}')


def collect_cleanup_plan() -> list[CacheEntry]:
    plan = []

    def add(category: str, path: Path):
        if path.exists():
            plan.append(CacheEntry(category, assert_safe_path(path), compute_size_bytes(path)))

    # Incremental state is optional; the compiled deps and their metadata stay intact.
    for target in CARGO_TARGET_DIRS:
        add('Cargo incremental', target / 'debug/incremental')

    for app in FLUTTER_APP_DIRS:
        cache_dir = app / '.dart_tool/flutter_build'
        if cache_dir.is_dir():
            hashes = [p for p in cache_dir.iterdir()
                      if p.is_dir() and re.fullmatch(r'[0-9a-f]{32}', p.name)]
            if len(hashes) > 1:
                build_id = (app / 'build/.last_build_id').read_text().strip()
                if not re.fullmatch(r'[0-9a-f]{32}', build_id) or not (cache_dir / build_id).is_dir():
                    raise ValueError(f'Invalid current Flutter build ID for {app}: {build_id!r}')
                print(f'Keeping Flutter build: {cache_dir.relative_to(REPO_ROOT)} / {build_id}')
                for old in hashes:
                    if old.name != build_id:
                        add('Flutter build hashes', old)

        build_dir = app / 'build'
        if build_dir.is_dir():
            tracked = sorted(
                [p for p in build_dir.iterdir()
                 if p.is_file() and re.fullmatch(r'[0-9a-f]{32}\.cache\.dill\.track\.dill', p.name)],
                key=lambda p: (p.stat().st_mtime_ns, p.name), reverse=True,
            )
            for old in tracked[1:]:
                add('Flutter tracked kernels', old)

    if THEME_PREVIEW_DIR.is_dir():
        previews = sorted(
            [p for p in THEME_PREVIEW_DIR.iterdir()
             if p.is_dir() and p.name.startswith('development')],
            key=lambda p: (p.stat().st_mtime_ns, p.name), reverse=True,
        )
        for old in previews[1:]:
            add('Theme previews', old)

    for path in TEST_CACHE_DIRS:
        add('Test caches', path)
    return plan


def apply_cleanup(plan: list[CacheEntry]) -> int:
    ensure_no_active_builds()
    removed_bytes = 0
    for entry in plan:
        path = assert_safe_path(entry.path)
        size = compute_size_bytes(path)
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        if path.exists():
            raise OSError(f'Cache path still exists after deletion: {path}')
        removed_bytes += size
        print(f'Removed: {path.relative_to(REPO_ROOT)} ({size / 1024**2:.2f} MiB)', flush=True)
    return removed_bytes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='Preview cleanup without deleting.')
    args = parser.parse_args()
    ensure_no_active_builds()
    plan = collect_cleanup_plan()
    categories = {}
    for entry in plan:
        categories[entry.category] = categories.get(entry.category, 0) + entry.size
        print(f'Candidate: {entry.path.relative_to(REPO_ROOT)} ({entry.size / 1024**2:.2f} MiB)')
    for category, size in categories.items():
        print(f'[{category}] {size / 1024**3:.3f} GiB')

    if args.dry_run:
        size = sum(entry.size for entry in plan)
        print(f'Done. Would free {size / 1024**2:.2f} MiB ({size / 1024**3:.3f} GiB).')
    else:
        free_before = shutil.disk_usage(REPO_ROOT).free
        size = apply_cleanup(plan)
        free_after = shutil.disk_usage(REPO_ROOT).free
        print(f'Done. Removed {size / 1024**2:.2f} MiB ({size / 1024**3:.3f} GiB) of cache files.')
        print(f'Drive free: {free_before / 1024**3:.3f} -> {free_after / 1024**3:.3f} GiB '
              f'(change {(free_after - free_before) / 1024**3:.3f} GiB).')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f'Cleanup failed: {error}', file=sys.stderr)
        sys.exit(1)
