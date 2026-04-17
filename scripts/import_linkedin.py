#!/usr/bin/env python3
"""Import a LinkedIn data export into ``content/archive/linkedin/``.

Usage
-----

    uv run --with pyyaml python3 themes/hugo-techie-personal/scripts/import_linkedin.py \
        --takeout takeouts/linkedin-2026-04-10.zip

LinkedIn ships ``Shares.csv`` in the "Basic" archive with one row per post,
including the activity URN and text. This importer maps each URN to a clean
folder structure (so ``urn:li:activity:1234`` becomes
``/www.linkedin.com/feed/update/urn/li/activity/1234/``) while preserving the
canonical colon URL in ``original_url``. The smart 404 handler in the theme
turns requests for the colon URL into a redirect to the folder path.

If the archive also contains a ``media/`` directory with images referenced by
``MediaUrl``, those files are copied into the bundle.
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _archive_common import (  # noqa: E402
    ArchiveRecord,
    ImportStats,
    MediaItem,
    guess_media_kind,
    load_exclude_set,
    parse_utc,
    write_bundle,
)

SHARES_CSV = "Shares.csv"
URN_RE = re.compile(r"urn:li:activity:(\d+)", re.IGNORECASE)


def _open_takeout(path: Path) -> tuple[Path, Path | None]:
    if path.is_dir():
        return path, None
    if path.is_file() and path.suffix.lower() == ".zip":
        tmp = Path(tempfile.mkdtemp(prefix="linkedin-takeout-"))
        with zipfile.ZipFile(path) as zf:
            zf.extractall(tmp)
        return tmp, tmp
    raise SystemExit(f"Takeout path not found or unsupported: {path}")


def _locate_shares_csv(root: Path) -> Path:
    direct = root / SHARES_CSV
    if direct.exists():
        return direct
    for match in root.rglob(SHARES_CSV):
        if match.is_file():
            return match
    raise SystemExit(f"Could not find {SHARES_CSV} in {root}")


def _locate_media_root(root: Path) -> Path | None:
    """LinkedIn sometimes ships media under ``media/``, ``Media/`` or nested."""
    for name in ("media", "Media"):
        candidate = root / name
        if candidate.exists() and candidate.is_dir():
            return candidate
    for name in ("media", "Media"):
        for candidate in root.rglob(name):
            if candidate.is_dir():
                return candidate
    return None


def _extract_activity_id(share_link: str) -> str | None:
    if not share_link:
        return None
    m = URN_RE.search(share_link)
    if m:
        return m.group(1)
    # Some exports store the numeric id directly as the URL path
    m = re.search(r"/activity[-_:](\d+)", share_link, re.IGNORECASE)
    if m:
        return m.group(1)
    return None


def _resolve_media_files(media_value: str, media_root: Path | None) -> list[Path]:
    if not media_value or not media_root:
        return []
    results: list[Path] = []
    for raw in re.split(r"[,\s]+", media_value.strip()):
        if not raw:
            continue
        raw = raw.strip()
        if raw.startswith("http://") or raw.startswith("https://"):
            # Remote URLs: takeouts sometimes point at LinkedIn CDN. We can't
            # fetch those at import time; skip so the content at least has text.
            continue
        # Try direct path, then basename lookup anywhere under media_root
        direct = (media_root / raw).resolve()
        try:
            direct.relative_to(media_root.resolve())
        except ValueError:
            direct = None  # outside media_root
        if direct and direct.exists():
            results.append(direct)
            continue
        basename = Path(raw).name
        matches = list(media_root.rglob(basename))
        if matches:
            results.append(matches[0])
    return results


def _build_records(
    rows: Iterable[dict],
    *,
    media_root: Path | None,
    user: str,
    exclude_ids: set[str],
    draft: bool,
) -> Iterable[ArchiveRecord]:
    for row in rows:
        share_link = row.get("ShareLink") or row.get("Share Link") or ""
        activity_id = _extract_activity_id(share_link)
        if not activity_id or activity_id in exclude_ids:
            continue
        date_str = row.get("Date") or row.get("Date Published") or ""
        try:
            date = parse_utc(date_str)
        except ValueError:
            continue
        body_raw = (
            row.get("ShareCommentary")
            or row.get("Share Commentary")
            or row.get("Commentary")
            or ""
        ).strip()
        shared_url = (
            row.get("SharedUrl")
            or row.get("Shared Url")
            or row.get("SharedURL")
            or ""
        ).strip()
        body_parts = [p for p in (body_raw, shared_url) if p]
        body = "\n\n".join(body_parts)

        media_value = row.get("MediaUrl") or row.get("Media Url") or ""
        media_files = _resolve_media_files(media_value, media_root)
        media_items = [
            MediaItem(src_path=f, kind=guess_media_kind(f)) for f in media_files
        ]

        original_url = (
            f"https://www.linkedin.com/feed/update/urn:li:activity:{activity_id}/"
        )
        url = f"/www.linkedin.com/feed/update/urn/li/activity/{activity_id}/"

        visibility = (row.get("Visibility") or "").strip().lower()
        yield ArchiveRecord(
            platform="linkedin",
            post_id=activity_id,
            url=url,
            original_url=original_url,
            date=date,
            body=body,
            platform_user=user,
            draft=draft,
            media=media_items,
            extra={
                k: v
                for k, v in {
                    "visibility": visibility,
                    "shared_url": shared_url,
                }.items()
                if v
            },
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--takeout", required=True, type=Path, help="Zip or directory")
    parser.add_argument(
        "--user",
        default="anantshrivastava",
        help="LinkedIn vanity handle used for display only (default: anantshrivastava)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--publish",
        action="store_true",
        default=False,
        help=(
            "Mark newly-imported posts as draft: false (publish immediately). "
            "Default is draft: true so you can curate. Existing bundles keep "
            "their current draft value regardless of this flag."
        ),
    )
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    root, tmp = _open_takeout(args.takeout)
    try:
        shares_csv = _locate_shares_csv(root)
        print(f"reading {shares_csv.relative_to(root)}")
        media_root = _locate_media_root(root)
        if media_root:
            print(f"media root: {media_root.relative_to(root)}")

        exclude_ids = load_exclude_set()
        with shares_csv.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            records = list(
                _build_records(
                    reader,
                    media_root=media_root,
                    user=args.user,
                    exclude_ids=exclude_ids,
                    draft=not args.publish,
                )
            )

        print(f"found {len(records)} linkedin posts")
        stats = ImportStats()
        for count, record in enumerate(records):
            if args.limit and count >= args.limit:
                break
            state, media_count = write_bundle(
                record, dry_run=args.dry_run, force=args.force
            )
            stats.media_copied += media_count if state != "skipped" else 0
            if state == "added":
                stats.added += 1
            elif state == "updated":
                stats.updated += 1
            else:
                stats.skipped += 1

        print(f"linkedin import: {stats.summary()}")
    finally:
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
