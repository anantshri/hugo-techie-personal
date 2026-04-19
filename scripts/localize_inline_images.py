#!/usr/bin/env python3
"""Backfill inline-image localization across existing archive bundles.

The sibling ``import_*.py`` importers call ``localize_inline_images`` (in
``_archive_common.py``) on newly-imported article bodies so remote
``media.licdn.com`` / other-CDN URLs are downloaded to
``static/images/archive/<platform>/<slug>/`` and the markdown body is rewritten
to absolute ``/images/archive/...`` paths. That handles *new* imports.

This script retroactively applies the same transform to pre-existing bundles
under ``content/archive/**``. Useful once after adding the feature, or any
time tuning/regex changes demand a re-sweep of already-imported content.

Behaviour
---------

* Walks every ``content/archive/<platform>/<slug>/index.md`` (optionally
  filtered with ``--platform``).
* Splits frontmatter from body using the existing ``---`` delimiter. The
  frontmatter is preserved byte-for-byte; only the body is rewritten.
* Calls ``localize_inline_images`` with the bundle's platform + slug. Remote
  ``http(s)://`` markdown images are downloaded to
  ``static/images/archive/<platform>/<slug>/inline-N.<ext>`` and the body
  links are rewritten to ``/images/archive/<platform>/<slug>/inline-N.<ext>``.
* If the body changes and the bundle has no media page resources (as is the
  case for LinkedIn Pulse articles), the ``.manifest.json`` ``content_hash``
  is refreshed so the next importer run reports ``skipped`` instead of
  ``updated``. For bundles *with* media, manifest refresh is skipped — the
  content hash depends on takeout-local ``src_path`` values we cannot recover
  from the bundle alone, and the next importer run will rewrite the manifest
  correctly on its own.

Flags
-----

``--dry-run``    Report what would change without writing files.
``--platform P`` Restrict to one platform (e.g. ``linkedin``).
``--force``      Re-download every remote image even if a local file exists.
``--limit N``    Process at most N bundles (useful for quick testing).

Usage
-----

    uv run --with pyyaml python3 \\
        themes/hugo-techie-personal/scripts/localize_inline_images.py

    uv run --with pyyaml python3 \\
        themes/hugo-techie-personal/scripts/localize_inline_images.py \\
        --platform linkedin --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _archive_common import (  # noqa: E402
    CONTENT_ROOT,
    MANIFEST_NAME,
    PLATFORMS,
    ArchiveRecord,
    content_hash,
    localize_inline_images,
    parse_utc,
)


def _split_frontmatter(text: str) -> tuple[str, str] | None:
    """Return ``(frontmatter_text, body_text)`` or ``None`` if not a bundle.

    ``frontmatter_text`` is the raw YAML (no surrounding ``---`` fences);
    ``body_text`` is everything after the closing ``---`` including the blank
    line(s) that typically follow it. Both are strings, not parsed.
    """
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    fm_text = text[3:end]
    if fm_text.startswith("\n"):
        fm_text = fm_text[1:]
    # Skip the closing '---' line and its trailing newline.
    rest_start = end + len("\n---")
    if rest_start < len(text) and text[rest_start] == "\n":
        rest_start += 1
    body_text = text[rest_start:]
    return fm_text, body_text


def _rebuild_file(fm_text: str, new_body: str, *, original_prefix_newlines: str) -> str:
    """Rebuild an index.md preserving the exact frontmatter bytes."""
    return f"---\n{fm_text}---\n{original_prefix_newlines}{new_body}"


def _leading_blank_lines(text: str) -> tuple[str, str]:
    """Split ``text`` into ``(leading_blank_lines, rest)``.

    Used to preserve the exact number of blank lines between the closing
    ``---`` and the body start, so byte-identical files (post rewrite-of-body-only)
    stay byte-identical.
    """
    i = 0
    while i < len(text) and text[i] == "\n":
        i += 1
    return text[:i], text[i:]


def _record_from_frontmatter(
    fm: dict, body: str, *, slug: str
) -> ArchiveRecord | None:
    """Reconstruct an ``ArchiveRecord`` from bundle frontmatter + body.

    Returns ``None`` for bundles we cannot faithfully reconstruct (missing
    required keys, or media present — see module docstring). The returned
    record is used *only* to recompute the content hash; the media list is
    always empty because we cannot recover the original takeout src_paths.
    """
    required = ("platform", "platform_id", "url", "original_url", "date")
    if not all(k in fm for k in required):
        return None
    if fm.get("media"):
        # Hash would depend on takeout-local src_paths we can't recover.
        return None
    try:
        date = parse_utc(fm["date"])
    except (ValueError, TypeError):
        return None
    return ArchiveRecord(
        platform=str(fm["platform"]),
        post_id=str(fm.get("platform_id") or slug),
        url=str(fm["url"]),
        original_url=str(fm["original_url"]),
        date=date,
        body=body,
        title=str(fm.get("title") or ""),
        platform_user=str(fm.get("platform_user") or ""),
        reply_to=str(fm.get("reply_to") or ""),
        retweet_of=str(fm.get("retweet_of") or ""),
        sensitive=bool(fm.get("sensitive", False)),
        media=[],
        extra=dict(fm.get("extra") or {}),
    )


def _iter_bundles(platform: str | None) -> list[Path]:
    if not CONTENT_ROOT.exists():
        return []
    platforms = (platform,) if platform else PLATFORMS
    out: list[Path] = []
    for p in platforms:
        root = CONTENT_ROOT / p
        if not root.is_dir():
            continue
        for entry in sorted(root.iterdir()):
            if entry.is_dir() and (entry / "index.md").exists():
                out.append(entry)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--platform",
        choices=PLATFORMS,
        default=None,
        help="Restrict to a single platform (default: all).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change; do not write files or download.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download every remote image even if a local file exists.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process at most N bundles (0 = no limit).",
    )
    args = parser.parse_args()

    bundles = _iter_bundles(args.platform)
    if args.limit > 0:
        bundles = bundles[: args.limit]

    total_downloaded = 0
    total_cached = 0
    total_failed = 0
    total_rewritten = 0
    bundles_changed = 0
    bundles_scanned = 0
    manifests_refreshed = 0

    for bundle in bundles:
        bundles_scanned += 1
        index_md = bundle / "index.md"
        try:
            raw = index_md.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"! {bundle.name}: cannot read index.md ({exc})")
            continue
        split = _split_frontmatter(raw)
        if split is None:
            continue
        fm_text, body_and_leading = split
        leading, body = _leading_blank_lines(body_and_leading)

        try:
            fm = yaml.safe_load(fm_text) or {}
        except yaml.YAMLError as exc:
            print(f"! {bundle.name}: cannot parse frontmatter ({exc})")
            continue
        if not isinstance(fm, dict):
            continue

        platform = str(fm.get("platform") or bundle.parent.name)
        slug = bundle.name

        new_body, stats = localize_inline_images(
            body,
            platform=platform,
            slug=slug,
            dry_run=args.dry_run,
            force=args.force,
        )

        total_downloaded += stats["downloaded"]
        total_cached += stats["cached"]
        total_failed += len(stats["failed"])
        total_rewritten += stats["rewritten"]

        if stats["failed"]:
            print(f"{bundle.relative_to(CONTENT_ROOT)}:")
            for url, reason in stats["failed"]:
                print(f"  ! failed: {url} ({reason})")

        if new_body == body:
            continue

        bundles_changed += 1
        rel = bundle.relative_to(CONTENT_ROOT)
        print(
            f"{rel}: rewrote {stats['rewritten']} image(s) "
            f"(downloaded={stats['downloaded']}, cached={stats['cached']})"
        )

        if args.dry_run:
            continue

        fm_sep = "" if fm_text.endswith("\n") else "\n"
        new_text = f"---\n{fm_text}{fm_sep}---\n{leading}{new_body}"
        index_md.write_text(new_text, encoding="utf-8")

        record = _record_from_frontmatter(fm, new_body, slug=slug)
        manifest_path = bundle / MANIFEST_NAME
        if record is not None and manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                manifest = None
            if isinstance(manifest, dict):
                new_hash = content_hash(record)
                if manifest.get("content_hash") != new_hash:
                    manifest["content_hash"] = new_hash
                    manifest["written_at"] = datetime.now(timezone.utc).isoformat()
                    manifest_path.write_text(
                        json.dumps(manifest, indent=2, sort_keys=True),
                        encoding="utf-8",
                    )
                    manifests_refreshed += 1

    print()
    print(
        f"scanned={bundles_scanned} changed={bundles_changed} "
        f"rewritten-image-refs={total_rewritten} "
        f"downloaded={total_downloaded} cached={total_cached} "
        f"failed={total_failed} manifests-refreshed={manifests_refreshed}"
    )
    if args.dry_run:
        print("(dry-run: no files written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
