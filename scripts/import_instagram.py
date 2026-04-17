#!/usr/bin/env python3
"""Import an Instagram data export into ``content/archive/instagram/``.

Usage
-----

    uv run --with pyyaml python3 themes/hugo-techie-personal/scripts/import_instagram.py \
        --takeout takeouts/instagram-2026-04-10.zip \
        --user anantshri

Caveat
------

Instagram's data export does NOT include the ``/p/<shortcode>/`` URL for each
post. To serve an archived post at ``/www.instagram.com/p/<shortcode>/``, supply
``takeouts/instagram-shortcode-map.json``, a JSON object mapping either the
first media's file name (e.g. ``posts/202410/abc123.jpg``) or the post's
creation timestamp (epoch seconds as a string) to the shortcode::

    {
      "posts/202410/abc123_1.jpg": "DUjOA_yDeae",
      "1728750000": "DUjOA_yDeae"
    }

Posts without a shortcode mapping fall back to the timestamp-based path
``/www.instagram.com/archive/<timestamp>/`` and still show up in the browse
index, but the "paste original URL" trick won't work for them.
"""

from __future__ import annotations

import argparse
import json
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
    TAKEOUTS_ROOT,
    guess_media_kind,
    load_exclude_set,
    parse_utc,
    write_bundle,
)

POSTS_JSON_CANDIDATES = (
    "your_instagram_activity/content/posts_1.json",
    "content/posts_1.json",
    "your_instagram_activity/content/posts.json",
)

SHORTCODE_MAP_FILE = "instagram-shortcode-map.json"


def _open_takeout(path: Path) -> tuple[Path, Path | None]:
    if path.is_dir():
        return path, None
    if path.is_file() and path.suffix.lower() == ".zip":
        tmp = Path(tempfile.mkdtemp(prefix="instagram-takeout-"))
        with zipfile.ZipFile(path) as zf:
            zf.extractall(tmp)
        return tmp, tmp
    raise SystemExit(f"Takeout path not found or unsupported: {path}")


def _locate_posts_json(root: Path) -> Path:
    for candidate in POSTS_JSON_CANDIDATES:
        p = root / candidate
        if p.exists():
            return p
    for match in root.rglob("posts_1.json"):
        if match.is_file():
            return match
    raise SystemExit(f"Could not find posts_1.json in {root}")


def _load_shortcode_map() -> dict[str, str]:
    map_path = TAKEOUTS_ROOT / SHORTCODE_MAP_FILE
    if not map_path.exists():
        return {}
    try:
        data = json.loads(map_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items()}


def _fix_mojibake(text: str) -> str:
    """Instagram emits UTF-8 bytes encoded via latin-1 in JSON strings."""
    if not text:
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


def _collect_media(post: dict, root: Path) -> tuple[list[MediaItem], list[str]]:
    items: list[MediaItem] = []
    uris: list[str] = []
    for media in post.get("media", []) or []:
        uri = media.get("uri")
        if not uri:
            continue
        uris.append(uri)
        src = (root / uri).resolve()
        if not src.exists():
            # Some zips store media under a top-level alternate path
            alt_matches = list(root.rglob(Path(uri).name))
            if alt_matches:
                src = alt_matches[0]
            else:
                continue
        items.append(MediaItem(src_path=src, kind=guess_media_kind(src)))
    return items, uris


def _post_id_and_url(
    post: dict,
    media_uris: list[str],
    shortcode_map: dict[str, str],
    timestamp: int,
) -> tuple[str, str, str]:
    """Return (post_id, site_url, original_url)."""
    shortcode = None
    for uri in media_uris:
        if uri in shortcode_map:
            shortcode = shortcode_map[uri]
            break
        base = Path(uri).name
        if base in shortcode_map:
            shortcode = shortcode_map[base]
            break
    if not shortcode:
        shortcode = shortcode_map.get(str(timestamp))
    if shortcode:
        return (
            shortcode,
            f"/www.instagram.com/p/{shortcode}/",
            f"https://www.instagram.com/p/{shortcode}/",
        )
    post_id = f"ts-{timestamp}"
    return (
        post_id,
        f"/www.instagram.com/archive/{post_id}/",
        f"https://www.instagram.com/",
    )


def _build_records(
    posts: Iterable[dict],
    *,
    root: Path,
    user: str,
    shortcode_map: dict[str, str],
    exclude_ids: set[str],
    draft: bool,
) -> Iterable[ArchiveRecord]:
    for post in posts:
        timestamp = int(post.get("creation_timestamp") or 0)
        if not timestamp:
            # Some exports put the timestamp on the first media only
            media_list = post.get("media") or []
            if media_list:
                timestamp = int(media_list[0].get("creation_timestamp") or 0)
        if not timestamp:
            continue
        date = parse_utc(float(timestamp))
        title = _fix_mojibake(post.get("title") or "")
        media_caption = ""
        for m in post.get("media", []) or []:
            if m.get("title"):
                media_caption = _fix_mojibake(m.get("title") or "")
                break
        body = title or media_caption
        media_items, media_uris = _collect_media(post, root)
        post_id, url, original_url = _post_id_and_url(
            post, media_uris, shortcode_map, timestamp
        )
        if post_id in exclude_ids:
            continue
        yield ArchiveRecord(
            platform="instagram",
            post_id=post_id,
            url=url,
            original_url=original_url,
            date=date,
            body=body,
            platform_user=user,
            draft=draft,
            media=media_items,
            extra={"creation_timestamp": timestamp} if not url.endswith(f"/p/{post_id}/") else {},
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--takeout", required=True, type=Path, help="Zip or directory")
    parser.add_argument("--user", required=True, help="Instagram handle")
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
        posts_json = _locate_posts_json(root)
        print(f"reading {posts_json.relative_to(root)}")
        data = json.loads(posts_json.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            posts = data.get("posts") or data.get("media") or []
        else:
            posts = data
        print(f"found {len(posts)} instagram posts")

        shortcode_map = _load_shortcode_map()
        if shortcode_map:
            print(f"loaded {len(shortcode_map)} shortcode mappings from {SHORTCODE_MAP_FILE}")
        else:
            print(
                "no shortcode map; posts will be archived under "
                "/www.instagram.com/archive/ts-<timestamp>/"
            )

        exclude_ids = load_exclude_set()
        records = list(
            _build_records(
                posts,
                root=root,
                user=args.user,
                shortcode_map=shortcode_map,
                exclude_ids=exclude_ids,
                draft=not args.publish,
            )
        )

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

        print(f"instagram import: {stats.summary()}")
    finally:
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
