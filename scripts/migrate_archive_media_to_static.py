#!/usr/bin/env python3
"""Move archive media from Hugo page bundles to ``static/images/archive/``.

Historically every archive importer wrote media attachments alongside
``index.md`` inside the Hugo page bundle, so files like
``content/archive/facebook/<slug>/media-0.jpg`` were resolved at render
time via ``.Resources.GetMatch``. For platforms that ship thousands of
trivial photo-upload bundles (notably Facebook), this bloats the
``content/`` tree, slows Hugo's bundle scan, and makes git diffs noisy.

The archive importer now routes any platform listed in
``STATIC_MEDIA_PLATFORMS`` (see ``_archive_common.py``) to
``<site>/static/images/archive/<platform>/<slug>/`` and references each
file from frontmatter via an absolute ``/images/archive/...`` URL. This
one-shot migration moves existing bundles over to the new layout:

1. Walk every ``content/archive/<platform>/<slug>/``.
2. Determine the new media directory with ``media_storage`` (same helper
   the importer uses, so the forward and backfill paths stay in sync).
3. Move each media file from the bundle into the new directory.
4. Rewrite the ``file:`` (and ``poster:``) fields in ``index.md``
   frontmatter from basenames to absolute URLs via surgical string
   replacement so every other frontmatter byte is preserved.
5. Leave ``.manifest.json`` alone: ``content_hash`` is independent of the
   rendered ``file`` path (it hashes the takeout-local ``src_path``), so
   the next importer run still reports ``skipped``.

Flags
-----

``--platform P``  Restrict to one platform (default: all platforms in
                  ``STATIC_MEDIA_PLATFORMS``).
``--dry-run``     Report what would change without moving files or
                  rewriting frontmatter.
``--limit N``     Process at most N bundles (useful for testing).

Usage
-----

    # Preview (no writes)
    uv run --with pyyaml python3 \\
        themes/hugo-techie-personal/scripts/migrate_archive_media_to_static.py \\
        --dry-run

    # Apply
    uv run --with pyyaml python3 \\
        themes/hugo-techie-personal/scripts/migrate_archive_media_to_static.py
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _archive_common import (  # noqa: E402
    CONTENT_ROOT,
    MANIFEST_NAME,
    SITE_ROOT,
    STATIC_MEDIA_PLATFORMS,
)


_MEDIA_BASENAME_RE = re.compile(r"^media-\d+(?:-poster)?\.[A-Za-z0-9]+$")


def _split_frontmatter(text: str) -> tuple[str, str, str] | None:
    """Return ``(leading, frontmatter_text, rest)`` or ``None``.

    ``leading`` is the literal ``---\\n`` delimiter (so callers can glue
    the new frontmatter back in place without re-guessing the exact
    whitespace). ``rest`` starts at the closing ``\\n---`` delimiter so
    the caller gets back an identical byte string when nothing changes.
    """
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    fm_text = text[3:end]
    if fm_text.startswith("\n"):
        fm_text = fm_text[1:]
    rest_start = end  # points at the "\n---" closing delimiter
    return "---\n", fm_text, text[rest_start:]


def _collect_media_basenames(manifest: dict | None, bundle: Path) -> list[str]:
    """Return the basenames of media files that belong to this bundle.

    Prefers the manifest's ``media_files`` list (authoritative, includes
    the exact order used at import time). Falls back to scanning the
    bundle directory for ``media-*`` files so bundles with a missing or
    stale manifest still migrate cleanly.
    """
    names: list[str] = []
    seen: set[str] = set()
    if manifest:
        for name in manifest.get("media_files", []) or []:
            if not isinstance(name, str):
                continue
            if name in seen:
                continue
            seen.add(name)
            names.append(name)
    if names:
        return names
    for entry in sorted(bundle.iterdir()):
        if not entry.is_file():
            continue
        if _MEDIA_BASENAME_RE.match(entry.name):
            names.append(entry.name)
    return names


def _rewrite_frontmatter(
    fm_text: str, basenames: list[str], url_prefix: str
) -> tuple[str, bool]:
    """Surgically replace bundle-relative media refs with absolute URLs.

    Matches any ``file:`` or ``poster:`` line whose value is exactly one
    of the known media basenames (optionally quoted). Every other line is
    preserved byte-for-byte. Returns ``(new_text, changed)``.
    """
    if not basenames:
        return fm_text, False

    name_pattern = "|".join(re.escape(n) for n in basenames)
    key_re = re.compile(
        r"^(?P<indent>\s*)(?P<key>file|poster):\s*"
        r"(?P<quote>['\"]?)(?P<name>" + name_pattern + r")(?P=quote)\s*$",
        re.MULTILINE,
    )

    changed = False

    def _sub(match: re.Match[str]) -> str:
        nonlocal changed
        name = match.group("name")
        new_value = url_prefix + name
        changed = True
        return f"{match.group('indent')}{match.group('key')}: {new_value}"

    new_text = key_re.sub(_sub, fm_text)
    return new_text, changed


def _parse_media_refs(fm_text: str) -> list[dict]:
    try:
        data = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        return []
    if not isinstance(data, dict):
        return []
    media = data.get("media") or []
    if not isinstance(media, list):
        return []
    return [m for m in media if isinstance(m, dict)]


def _platforms_to_migrate(arg: str | None) -> list[str]:
    if arg:
        if arg not in STATIC_MEDIA_PLATFORMS:
            raise SystemExit(
                f"--platform {arg!r} is not in STATIC_MEDIA_PLATFORMS="
                f"{sorted(STATIC_MEDIA_PLATFORMS)}"
            )
        return [arg]
    return sorted(STATIC_MEDIA_PLATFORMS)


def _iter_bundles(platforms: list[str]) -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    for platform in platforms:
        root = CONTENT_ROOT / platform
        if not root.is_dir():
            continue
        for entry in sorted(root.iterdir()):
            if entry.is_dir() and (entry / "index.md").exists():
                out.append((platform, entry))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--platform",
        default=None,
        help=(
            "Restrict to a single platform. Defaults to every platform listed "
            "in STATIC_MEDIA_PLATFORMS."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report intended moves without touching the filesystem.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process at most N bundles (0 = no limit).",
    )
    args = parser.parse_args()

    platforms = _platforms_to_migrate(args.platform)
    bundles = _iter_bundles(platforms)
    if args.limit > 0:
        bundles = bundles[: args.limit]

    bundles_scanned = 0
    bundles_migrated = 0
    bundles_partial = 0
    files_moved = 0
    files_already_static = 0
    files_missing = 0

    for platform, bundle in bundles:
        bundles_scanned += 1
        slug = bundle.name
        index_md = bundle / "index.md"
        manifest_path = bundle / MANIFEST_NAME

        manifest: dict | None = None
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                manifest = None

        basenames = _collect_media_basenames(manifest, bundle)
        if not basenames:
            continue

        target_dir = (
            SITE_ROOT / "static" / "images" / "archive" / platform / slug
        )
        url_prefix = f"/images/archive/{platform}/{slug}/"

        try:
            raw = index_md.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"! {platform}/{slug}: cannot read index.md ({exc})")
            continue
        split = _split_frontmatter(raw)
        if split is None:
            print(f"! {platform}/{slug}: no frontmatter delimiter, skipping")
            continue
        leading, fm_text, rest = split

        # Only rewrite frontmatter for media basenames that are actually
        # referenced — don't let a stray file on disk hijack some other
        # frontmatter value that happens to match the regex.
        refs = _parse_media_refs(fm_text)
        referenced = {str(r.get("file") or "") for r in refs}
        referenced.update(str(r.get("poster") or "") for r in refs)
        referenced.discard("")
        relevant = [n for n in basenames if n in referenced] or basenames

        new_fm_text, fm_changed = _rewrite_frontmatter(
            fm_text, relevant, url_prefix
        )

        # Move files. Track per-bundle counts so we can print a meaningful
        # log line even when some files are already where they belong.
        moved_here = 0
        missing_here = 0
        already_here = 0
        for name in basenames:
            src = bundle / name
            dst = target_dir / name
            if not src.exists():
                if dst.exists():
                    already_here += 1
                else:
                    missing_here += 1
                continue
            if args.dry_run:
                moved_here += 1
                continue
            target_dir.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                # Unlikely but possible if an earlier aborted run left
                # a half-migrated bundle. Prefer the bundle copy as the
                # authoritative source and overwrite.
                try:
                    dst.unlink()
                except OSError:
                    pass
            shutil.move(str(src), str(dst))
            moved_here += 1

        files_moved += moved_here
        files_already_static += already_here
        files_missing += missing_here

        if moved_here == 0 and not fm_changed:
            continue

        if fm_changed and not args.dry_run:
            new_text = leading + new_fm_text
            if not new_text.endswith("\n"):
                new_text += "\n"
            new_text += rest
            index_md.write_text(new_text, encoding="utf-8")

        state = "migrated"
        if missing_here:
            state = "migrated (partial)"
            bundles_partial += 1
        else:
            bundles_migrated += 1
        dry_suffix = " [dry-run]" if args.dry_run else ""
        print(
            f"{platform}/{slug}: {state} moved={moved_here} "
            f"already_static={already_here} missing={missing_here}"
            f"{dry_suffix}"
        )

    print()
    print(
        f"scanned={bundles_scanned} migrated={bundles_migrated} "
        f"partial={bundles_partial} files_moved={files_moved} "
        f"files_already_static={files_already_static} "
        f"files_missing={files_missing}"
    )
    if args.dry_run:
        print("(dry-run: no files moved and no frontmatter rewritten)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
