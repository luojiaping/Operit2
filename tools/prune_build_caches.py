#!/usr/bin/env python3
r"""Prune old Flutter and Cargo build caches in Operit2, keeping only the single newest build.

Usage:
    .\.venv\Scripts\python.exe tools/prune_build_caches.py [--dry-run]
"""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

ALLOWED_CACHE_PREFIXES = [
    str(REPO_ROOT / 'apps' / 'flutter' / 'native' / 'operit-flutter-bridge' / 'target') + os.sep,
    str(REPO_ROOT / 'core' / 'target') + os.sep,
    str(REPO_ROOT / 'apps' / 'cli' / 'target') + os.sep,
    str(REPO_ROOT / 'build' / 'theme-preview') + os.sep,
    str(REPO_ROOT / 'apps' / 'flutter' / 'theme_preview' / '.dart_tool' / 'flutter_build') + os.sep,
    str(REPO_ROOT / 'apps' / 'flutter' / 'theme_preview' / 'build'),
    str(REPO_ROOT / 'apps' / 'flutter' / 'app' / '.dart_tool' / 'flutter_build') + os.sep,
    str(REPO_ROOT / 'apps' / 'flutter' / 'app' / 'build' / 'test_cache'),
    str(REPO_ROOT / 'apps' / 'flutter' / 'packages' / 'operit_theme' / 'build' / 'test_cache'),
    str(REPO_ROOT / 'target'),
    str(REPO_ROOT / 'rust-learning' / 'target'),
    str(REPO_ROOT / 'apps' / 'web_access' / 'build'),
    str(REPO_ROOT / '_investigation' / 'Operit-iOS' / 'apps' / 'flutter' / 'app' / 'build'),
]


def assert_safe_path(target_path: Path) -> Path:
    resolved = target_path.resolve()
    resolved_str = os.path.normcase(str(resolved))
    root_str = os.path.normcase(str(REPO_ROOT))
    if not resolved_str.startswith(root_str):
        raise ValueError(f'Path outside workspace rejected: {resolved}')

    matched = False
    for pref in ALLOWED_CACHE_PREFIXES:
        p_norm = os.path.normcase(pref)
        if p_norm.endswith(os.sep):
            if resolved_str.startswith(p_norm) and len(resolved_str) > len(p_norm):
                matched = True
                break
        else:
            if resolved_str == p_norm or resolved_str.startswith(p_norm + os.sep):
                matched = True
                break
    if not matched:
        raise ValueError(f'Path outside allowed cache directories: {resolved}')
    return resolved


def compute_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    if not path.is_dir():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def remove_path(path: Path, dry_run: bool = False) -> int:
    safe = assert_safe_path(path)
    if not safe.exists():
        return 0
    sz = compute_size_bytes(safe)
    if not dry_run:
        if safe.is_dir():
            shutil.rmtree(safe, ignore_errors=True)
        else:
            try:
                safe.unlink()
            except OSError:
                pass
    return sz


def prune_flutter_build_dirs(parent_dir: Path, dry_run: bool) -> int:
    if not parent_dir.is_dir():
        return 0
    subdirs = []
    for entry in parent_dir.iterdir():
        if entry.is_dir() and re.match(r'^[0-9a-f]{32}$', entry.name):
            try:
                subdirs.append((entry.stat().st_mtime, entry))
            except OSError:
                pass
    subdirs.sort(key=lambda x: x[0], reverse=True)
    freed = 0
    if len(subdirs) > 1:
        latest = subdirs[0][1]
        print(f'  [Flutter] {parent_dir.relative_to(REPO_ROOT)}: keeping newest {latest.name}')
        for _, old_dir in subdirs[1:]:
            b = remove_path(old_dir, dry_run)
            freed += b
    return freed


def prune_theme_preview_dirs(tp_root: Path, dry_run: bool) -> int:
    if not tp_root.is_dir():
        return 0
    subdirs = []
    for entry in tp_root.iterdir():
        if entry.is_dir() and entry.name.startswith('development'):
            try:
                subdirs.append((entry.stat().st_mtime, entry))
            except OSError:
                pass
    subdirs.sort(key=lambda x: x[0], reverse=True)
    freed = 0
    if len(subdirs) > 1:
        latest = subdirs[0][1]
        print(f'  [ThemePreview] keeping newest {latest.name}')
        for _, old_dir in subdirs[1:]:
            b = remove_path(old_dir, dry_run)
            freed += b
    return freed


def prune_cargo_incremental(target_dir: Path, dry_run: bool) -> int:
    inc_dir = target_dir / 'debug' / 'incremental'
    if not inc_dir.is_dir():
        return 0

    groups = {}
    for entry in inc_dir.iterdir():
        if entry.is_dir():
            crate = re.sub(r'-[0-9a-z]+$', '', entry.name)
            try:
                groups.setdefault(crate, []).append((entry.stat().st_mtime, entry))
            except OSError:
                pass

    freed = 0
    for crate, items in groups.items():
        items.sort(key=lambda x: x[0], reverse=True)
        # Keep only the newest hash folder per crate
        for _, old_dir in items[1:]:
            b = remove_path(old_dir, dry_run)
            freed += b

        kept_dir = items[0][1]
        if kept_dir.is_dir():
            sessions = []
            for s in kept_dir.iterdir():
                if s.is_dir() and s.name.startswith('s-'):
                    try:
                        sessions.append((s.stat().st_mtime, s))
                    except OSError:
                        pass
            sessions.sort(key=lambda x: x[0], reverse=True)
            for _, old_sess in sessions[1:]:
                b = remove_path(old_sess, dry_run)
                freed += b

            # Clean orphaned .lock files
            if sessions and not dry_run:
                kept_name = sessions[0][1].name
                for f in kept_dir.iterdir():
                    if f.is_file() and f.name.endswith('.lock'):
                        if not kept_name.startswith(f.name[:-5]):
                            try:
                                f.unlink()
                            except OSError:
                                pass
    return freed


# Cargo artifact extensions that live in deps/ and accumulate one hash per build.
_DEPS_HASHED_EXTS = ('.rlib', '.rmeta', '.dll', '.pdb', '.o', '.lib', '.exp', '.d')
# The trailing hash cargo appends to an artifact name, e.g. -72b767e8aa10d533.
_HASH_SUFFIX_RE = re.compile(r'-[0-9a-f]{16}$')


def _strip_hash_suffix(stem: str):
    """Return the crate base name if stem ends with a cargo hash, else None."""
    m = _HASH_SUFFIX_RE.search(stem)
    if not m:
        return None
    return stem[:m.start()]


def prune_cargo_deps(target_dir: Path, dry_run: bool) -> int:
    """Keep only the newest artifact per crate in deps/, removing the older
    hash generations that cargo never garbage-collects (rust-lang/cargo#5026).
    """
    deps_dir = target_dir / 'debug' / 'deps'
    if not deps_dir.is_dir():
        return 0

    groups = {}
    for entry in deps_dir.iterdir():
        if not entry.is_file():
            continue
        if not entry.name.lower().endswith(_DEPS_HASHED_EXTS):
            continue
        base = _strip_hash_suffix(entry.stem)
        if base is None:
            continue
        try:
            groups.setdefault((base, entry.suffix.lower()), []).append((entry.stat().st_mtime, entry))
        except OSError:
            pass

    freed = 0
    for _, items in groups.items():
        if len(items) <= 1:
            continue
        items.sort(key=lambda x: x[0], reverse=True)
        for _, old in items[1:]:
            freed += remove_path(old, dry_run)
    return freed


def prune_dangling_fingerprints(target_dir: Path, dry_run: bool) -> int:
    """Remove .fingerprint/<crate>-<hash> dirs whose deps artifact is gone,
    which otherwise breaks later builds with missing rmeta errors.
    """
    fp_dir = target_dir / 'debug' / '.fingerprint'
    deps_dir = target_dir / 'debug' / 'deps'
    if not fp_dir.is_dir() or not deps_dir.is_dir():
        return 0

    dep_hashes = set()
    for entry in deps_dir.iterdir():
        if not entry.is_file():
            continue
        m = _HASH_SUFFIX_RE.search(entry.stem)
        if m:
            dep_hashes.add(m.group(0)[1:])

    freed = 0
    for entry in fp_dir.iterdir():
        if not entry.is_dir():
            continue
        m = _HASH_SUFFIX_RE.search(entry.name)
        if not m:
            continue
        if m.group(0)[1:] not in dep_hashes:
            freed += remove_path(entry, dry_run)
    return freed


def main():
    parser = argparse.ArgumentParser(description='Prune old build caches in Operit2, keeping 1 latest build.')
    parser.add_argument('--dry-run', action='store_true', help='Report potential reclaimed space without deleting.')
    args = parser.parse_args()

    print(f'=== Pruning Operit2 Build Caches (dry_run={args.dry_run}) ===')
    total_freed = 0

    # 1. Whole stale/legacy build directories
    stale_dirs = [
        REPO_ROOT / 'apps' / 'flutter' / 'native' / 'operit-flutter-bridge' / 'target' / 'x86_64-pc-windows-msvc',
        REPO_ROOT / 'core' / 'target' / 'wasm32-unknown-unknown',
        REPO_ROOT / 'core' / 'target' / 'release',
        REPO_ROOT / 'core' / 'target' / 'x86_64-pc-windows-msvc',
        REPO_ROOT / 'target',
        REPO_ROOT / 'rust-learning' / 'target',
        REPO_ROOT / 'apps' / 'web_access' / 'build',
        REPO_ROOT / 'apps' / 'flutter' / 'theme_preview' / 'build',
        REPO_ROOT / 'apps' / 'flutter' / 'app' / 'build' / 'test_cache',
        REPO_ROOT / 'apps' / 'flutter' / 'packages' / 'operit_theme' / 'build' / 'test_cache',
        REPO_ROOT / '_investigation' / 'Operit-iOS' / 'apps' / 'flutter' / 'app' / 'build',
    ]
    stale_freed = 0
    for sd in stale_dirs:
        if sd.exists():
            b = remove_path(sd, args.dry_run)
            stale_freed += b
    if stale_freed > 0:
        print(f'  [Stale Dirs] Freed: {stale_freed / (1024*1024):.2f} MB')
    total_freed += stale_freed

    # 2. Flutter .dart_tool/flutter_build (keep 1 newest hash)
    fb_freed = 0
    fb_freed += prune_flutter_build_dirs(REPO_ROOT / 'apps' / 'flutter' / 'app' / '.dart_tool' / 'flutter_build', args.dry_run)
    fb_freed += prune_flutter_build_dirs(REPO_ROOT / 'apps' / 'flutter' / 'theme_preview' / '.dart_tool' / 'flutter_build', args.dry_run)
    if fb_freed > 0:
        print(f'  [Flutter Build Hash Dirs] Freed: {fb_freed / (1024*1024):.2f} MB')
    total_freed += fb_freed

    # 3. Theme preview development-* (keep 1 newest)
    tp_freed = prune_theme_preview_dirs(REPO_ROOT / 'build' / 'theme-preview', args.dry_run)
    if tp_freed > 0:
        print(f'  [Theme Preview] Freed: {tp_freed / (1024*1024):.2f} MB')
    total_freed += tp_freed

    # 4. Cargo incremental caches in core and flutter bridge (keep 1 newest session per crate)
    inc_freed = 0
    inc_freed += prune_cargo_incremental(REPO_ROOT / 'apps' / 'flutter' / 'native' / 'operit-flutter-bridge' / 'target', args.dry_run)
    inc_freed += prune_cargo_incremental(REPO_ROOT / 'core' / 'target', args.dry_run)
    if inc_freed > 0:
        print(f'  [Cargo Incremental] Freed: {inc_freed / (1024*1024):.2f} MB')
    total_freed += inc_freed

    # 5. Stale hashed artifacts in deps/ (keep 1 newest generation per crate)
    deps_freed = 0
    deps_freed += prune_cargo_deps(REPO_ROOT / 'apps' / 'flutter' / 'native' / 'operit-flutter-bridge' / 'target', args.dry_run)
    deps_freed += prune_cargo_deps(REPO_ROOT / 'core' / 'target', args.dry_run)
    deps_freed += prune_cargo_deps(REPO_ROOT / 'apps' / 'cli' / 'target', args.dry_run)
    if deps_freed > 0:
        print(f'  [Cargo Stale Deps] Freed: {deps_freed / (1024*1024):.2f} MB')
    total_freed += deps_freed

    # 6. Dangling .fingerprint dirs whose deps artifact no longer exists
    fp_freed = 0
    fp_freed += prune_dangling_fingerprints(REPO_ROOT / 'apps' / 'flutter' / 'native' / 'operit-flutter-bridge' / 'target', args.dry_run)
    fp_freed += prune_dangling_fingerprints(REPO_ROOT / 'core' / 'target', args.dry_run)
    fp_freed += prune_dangling_fingerprints(REPO_ROOT / 'apps' / 'cli' / 'target', args.dry_run)
    if fp_freed > 0:
        print(f'  [Cargo Dangling Fingerprints] Freed: {fp_freed / (1024*1024):.2f} MB')
    total_freed += fp_freed

    action = 'Would free' if args.dry_run else 'Successfully freed'
    print(f'Done. {action} {total_freed / (1024*1024):.2f} MB ({total_freed / (1024*1024*1024):.2f} GB).')


if __name__ == '__main__':
    main()
