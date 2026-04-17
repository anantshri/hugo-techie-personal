#!/usr/bin/env python3
"""Import a Facebook data export into ``content/archive/facebook/``.

Usage
-----

    uv run --with pyyaml python3 themes/hugo-techie-personal/scripts/import_facebook.py \
        --takeout takeouts/facebook-2026-04-10.zip \
        --user anantshrivastava

Facebook's JSON export stores your posts in files named like
``your_facebook_activity/posts/your_posts__check_ins__photos_and_videos_1.json``.
Each entry has a ``timestamp``, a ``data`` list (usually containing the post
text under ``post``) and optional ``attachments`` referencing media files that
live elsewhere in the archive.

URL caveat
----------

Like Instagram, the Facebook takeout does not reliably include the public
permalink for each post. To serve archived posts at the mirrored URL
(``/www.facebook.com/<user>/posts/<id>/`` or a full custom permalink), supply
``takeouts/facebook-url-map.json``. Keys can be the first attachment's media
URI, the basename of that URI, or the ``timestamp`` as a string. Values can be
either a raw post id or a full URL::

    {
      "posts/media/abc.jpg": "pfbid0abc123",
      "def.mp4": "https://www.facebook.com/permalink.php?story_fbid=12345&id=9876",
      "1728750000": "pfbid0xyz"
    }

Posts without a mapping are archived at
``/www.facebook.com/archive/ts-<timestamp>/`` and still show up in the browse
index, but pasting the original URL won't route to them.
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

POSTS_GLOBS = (
    "your_facebook_activity/posts/your_posts__check_ins__photos_and_videos_*.json",
    "your_facebook_activity/posts/your_posts_*.json",
    "posts/your_posts__check_ins__photos_and_videos_*.json",
    "posts/your_posts_*.json",
)

URL_MAP_FILE = "facebook-url-map.json"

FB_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def _open_takeout(path: Path) -> tuple[Path, Path | None]:
    if path.is_dir():
        return path, None
    if path.is_file() and path.suffix.lower() == ".zip":
        tmp = Path(tempfile.mkdtemp(prefix="facebook-takeout-"))
        with zipfile.ZipFile(path) as zf:
            zf.extractall(tmp)
        return tmp, tmp
    raise SystemExit(f"Takeout path not found or unsupported: {path}")


def _locate_posts_files(root: Path) -> list[Path]:
    results: list[Path] = []
    for pattern in POSTS_GLOBS:
        results.extend(sorted(root.glob(pattern)))
    if results:
        # Deduplicate while preserving order
        seen: set[Path] = set()
        unique: list[Path] = []
        for p in results:
            rp = p.resolve()
            if rp not in seen:
                seen.add(rp)
                unique.append(p)
        return unique
    # Last-resort deep search
    fallback = [
        p
        for p in root.rglob("your_posts*.json")
        if p.is_file() and "posts" in p.parts
    ]
    if fallback:
        return sorted(fallback)
    raise SystemExit(
        "Could not find posts JSON in Facebook takeout. Looked for: "
        + ", ".join(POSTS_GLOBS)
    )


def _load_url_map() -> dict[str, str]:
    map_path = TAKEOUTS_ROOT / URL_MAP_FILE
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
    """Facebook (like Instagram) emits UTF-8 bytes encoded via latin-1."""
    if not text:
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


def _extract_body(post: dict) -> str:
    parts: list[str] = []
    for entry in post.get("data", []) or []:
        if not isinstance(entry, dict):
            continue
        text = entry.get("post")
        if text:
            parts.append(_fix_mojibake(text))
    # Some share-link posts only carry context in attachments
    for att in post.get("attachments", []) or []:
        for d in att.get("data", []) or []:
            ec = d.get("external_context")
            if isinstance(ec, dict):
                for k in ("name", "source", "url"):
                    v = ec.get(k)
                    if v and v not in parts:
                        parts.append(_fix_mojibake(str(v)))
            text_block = d.get("text")
            if text_block:
                parts.append(_fix_mojibake(str(text_block)))
    title = _fix_mojibake(post.get("title") or "")
    body = "\n\n".join(parts).strip()
    if not body and title:
        body = title
    return body


def _collect_media(post: dict, root: Path) -> tuple[list[MediaItem], list[str]]:
    items: list[MediaItem] = []
    uris: list[str] = []
    for att in post.get("attachments", []) or []:
        for entry in att.get("data", []) or []:
            media = entry.get("media")
            if not isinstance(media, dict):
                continue
            uri = media.get("uri")
            if not uri:
                continue
            uris.append(uri)
            src = (root / uri).resolve()
            if not src.exists():
                matches = list(root.rglob(Path(uri).name))
                if matches:
                    src = matches[0]
                else:
                    continue
            kind = guess_media_kind(src)
            alt = _fix_mojibake(media.get("description") or media.get("title") or "")
            items.append(MediaItem(src_path=src, kind=kind, alt=alt))
    return items, uris


def _resolve_permalink(
    user: str,
    media_uris: list[str],
    url_map: dict[str, str],
    timestamp: int,
) -> tuple[str, str, str] | None:
    """Return (post_id, site_url, original_url) if a mapping exists."""
    mapped: str | None = None
    for uri in media_uris:
        if uri in url_map:
            mapped = url_map[uri]
            break
        base = Path(uri).name
        if base in url_map:
            mapped = url_map[base]
            break
    if mapped is None:
        mapped = url_map.get(str(timestamp))
    if mapped is None:
        return None

    if FB_URL_RE.match(mapped):
        # Full URL supplied; derive local path by stripping the scheme.
        # We flatten every URL-significant separator (':', '?', '&', '=') into
        # folder boundaries so the result is a pure path. The smart 404
        # handler mirrors the same transformation for requests that come in
        # with the original separators intact.
        original_url = mapped
        stripped = re.sub(r"^https?://", "", mapped).rstrip("/")
        for ch in (":", "?", "&", "="):
            stripped = stripped.replace(ch, "/")
        local = "/" + stripped + "/"
        local = re.sub(r"/+", "/", local)
        # Use the last meaningful path segment as the post_id for storage
        segments = [s for s in local.strip("/").split("/") if s]
        post_id = segments[-1] if segments else "post"
        return post_id, local, original_url

    post_id = mapped
    site_url = f"/www.facebook.com/{user}/posts/{post_id}/"
    original_url = f"https://www.facebook.com/{user}/posts/{post_id}/"
    return post_id, site_url, original_url


def _post_id_and_url(
    user: str,
    media_uris: list[str],
    url_map: dict[str, str],
    timestamp: int,
) -> tuple[str, str, str]:
    resolved = _resolve_permalink(user, media_uris, url_map, timestamp)
    if resolved:
        return resolved
    post_id = f"ts-{timestamp}"
    return (
        post_id,
        f"/www.facebook.com/archive/{post_id}/",
        f"https://www.facebook.com/{user}/",
    )


def _build_records(
    posts: Iterable[dict],
    *,
    root: Path,
    user: str,
    url_map: dict[str, str],
    exclude_ids: set[str],
    draft: bool,
) -> Iterable[ArchiveRecord]:
    for post in posts:
        timestamp = int(post.get("timestamp") or 0)
        if not timestamp:
            # Some posts nest the timestamp under data[] entries
            for entry in post.get("data", []) or []:
                if isinstance(entry, dict):
                    ts = entry.get("update_timestamp") or entry.get("timestamp")
                    if ts:
                        timestamp = int(ts)
                        break
        if not timestamp:
            continue
        date = parse_utc(float(timestamp))
        body = _extract_body(post)
        media_items, media_uris = _collect_media(post, root)
        post_id, url, original_url = _post_id_and_url(
            user, media_uris, url_map, timestamp
        )
        if post_id in exclude_ids:
            continue
        title = _fix_mojibake(post.get("title") or "")
        yield ArchiveRecord(
            platform="facebook",
            post_id=post_id,
            url=url,
            original_url=original_url,
            date=date,
            body=body,
            title=title if title and title != body else "",
            platform_user=user,
            draft=draft,
            media=media_items,
            extra=(
                {"creation_timestamp": timestamp}
                if url.startswith("/www.facebook.com/archive/")
                else {}
            ),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--takeout", required=True, type=Path, help="Zip or directory")
    parser.add_argument(
        "--user",
        required=True,
        help="Facebook username / vanity handle (used in the mirrored URL)",
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
        posts_files = _locate_posts_files(root)
        print(f"reading {len(posts_files)} posts file(s):")
        posts: list[dict] = []
        for pf in posts_files:
            print(f"  - {pf.relative_to(root)}")
            data = json.loads(pf.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                items = data.get("posts") or data.get("status_updates_v2") or []
                if not items:
                    # Some exports store a top-level list under a single key
                    for v in data.values():
                        if isinstance(v, list):
                            items = v
                            break
                posts.extend(items)
            elif isinstance(data, list):
                posts.extend(data)

        print(f"found {len(posts)} facebook posts")

        url_map = _load_url_map()
        if url_map:
            print(f"loaded {len(url_map)} URL mappings from {URL_MAP_FILE}")
        else:
            print(
                "no URL map; posts will be archived under "
                "/www.facebook.com/archive/ts-<timestamp>/"
            )

        exclude_ids = load_exclude_set()
        records = list(
            _build_records(
                posts,
                root=root,
                user=args.user,
                url_map=url_map,
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

        print(f"facebook import: {stats.summary()}")
    finally:
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
