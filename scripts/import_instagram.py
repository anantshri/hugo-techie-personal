#!/usr/bin/env python3
"""Import an Instagram data export into ``content/archive/instagram/``.

Both the JSON-format and the HTML-format data exports are supported. Newer
Instagram takeouts default to HTML; older ones (and the JSON opt-in) ship
``posts_1.json``. The importer auto-detects which format the archive uses.

Usage
-----

    # JSON format
    uv run --with pyyaml python3 themes/hugo-techie-personal/scripts/import_instagram.py \
        --takeout takeouts/instagram-2026-04-10.zip \
        --user anantshri

    # HTML format (requires beautifulsoup4 + lxml)
    uv run --with pyyaml --with beautifulsoup4 --with lxml python3 \
        themes/hugo-techie-personal/scripts/import_instagram.py \
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _archive_common import (  # noqa: E402
    ArchiveRecord,
    AutoPublishPolicy,
    ImportStats,
    MediaItem,
    TAKEOUTS_ROOT,
    evaluate_auto_publish,
    guess_media_kind,
    load_auto_publish_policy,
    load_exclude_set,
    parse_utc,
    write_bundle,
)

POSTS_JSON_CANDIDATES = (
    "your_instagram_activity/content/posts_1.json",
    "content/posts_1.json",
    "your_instagram_activity/content/posts.json",
)

POSTS_HTML_CANDIDATES = (
    "your_instagram_activity/media/posts_1.html",
    "content/posts_1.html",
    "your_instagram_activity/content/posts_1.html",
)

# Instagram HTML exports render each timestamp in one of these formats.
# 2021-era: "Sep 28, 2020, 3:08 PM"
# 2026-era: "Feb 09, 2026 12:18 pm"
_HTML_DATE_FORMATS = (
    "%b %d, %Y, %I:%M %p",
    "%b %d, %Y %I:%M %p",
    "%b %d, %Y, %I:%M%p",
    "%b %d, %Y %I:%M%p",
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


def _locate_posts_json(root: Path) -> Path | None:
    for candidate in POSTS_JSON_CANDIDATES:
        p = root / candidate
        if p.exists():
            return p
    for match in root.rglob("posts_1.json"):
        if match.is_file():
            return match
    return None


def _locate_posts_html(root: Path) -> Path | None:
    for candidate in POSTS_HTML_CANDIDATES:
        p = root / candidate
        if p.exists():
            return p
    for match in root.rglob("posts_1.html"):
        if match.is_file():
            return match
    return None


def _parse_html_timestamp(text: str) -> int | None:
    """Parse an Instagram HTML timestamp string into epoch seconds (UTC).

    Instagram HTML exports don't include a timezone; treat as UTC for parity
    with the JSON exporter (which also emits ``creation_timestamp`` as UTC
    epoch seconds).
    """
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return None
    # Normalise "pm"/"am" to uppercase for %p compatibility on some locales.
    normalised = re.sub(r"\b([ap])m\b", lambda m: m.group(1).upper() + "M", cleaned)
    for fmt in _HTML_DATE_FORMATS:
        try:
            dt = datetime.strptime(normalised, fmt)
        except ValueError:
            continue
        return int(dt.replace(tzinfo=timezone.utc).timestamp())
    return None


def _load_posts_from_html(html_path: Path) -> list[dict]:
    """Parse an Instagram HTML ``posts_1.html`` into JSON-shaped post dicts.

    Returns a list shaped like the JSON ``posts`` array so the rest of the
    pipeline (``_build_records``) can stay untouched::

        [{"creation_timestamp": 1728750000,
          "title": "caption text",
          "media": [{"uri": "media/posts/.../xyz.jpg", "title": ""}]}, ...]
    """
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "HTML Instagram export detected but beautifulsoup4 is not installed. "
            "Re-run with: uv run --with pyyaml --with beautifulsoup4 --with lxml python3 ..."
        ) from exc

    html = html_path.read_text(encoding="utf-8", errors="replace")
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:  # lxml missing or parse error
        soup = BeautifulSoup(html, "html.parser")

    # Posts live inside ``main._a706`` (2026 layout) or ``div._4t5n`` (2021).
    container = soup.find("main", class_="_a706") or soup.find(class_="_4t5n")
    if container is None:
        container = soup.body or soup

    posts: list[dict] = []
    for card in container.find_all("div", class_="pam"):
        classes = card.get("class") or []
        if "uiBoxWhite" not in classes:
            continue

        # --- caption -------------------------------------------------------
        caption = ""
        h2 = card.find("h2")
        if h2 and h2.get_text(strip=True):
            caption = h2.get_text("\n", strip=True)
        else:
            cap_div = card.find("div", class_="_2lek")
            if cap_div:
                caption = cap_div.get_text("\n", strip=True)

        # --- media ---------------------------------------------------------
        media: list[dict] = []
        seen_uris: set[str] = set()
        for a in card.find_all("a", href=True):
            href = a["href"].strip()
            if not href.startswith(("media/", "./media/")):
                continue
            uri = href[2:] if href.startswith("./") else href
            if uri in seen_uris:
                continue
            seen_uris.add(uri)
            media.append({"uri": uri, "title": ""})
        if not media:
            for tag in card.find_all(["img", "video", "source"], src=True):
                src = tag["src"].strip()
                if not src.startswith(("media/", "./media/")):
                    continue
                uri = src[2:] if src.startswith("./") else src
                if uri in seen_uris:
                    continue
                seen_uris.add(uri)
                media.append({"uri": uri, "title": ""})

        # --- timestamp -----------------------------------------------------
        ts_div = None
        for candidate in card.find_all("div"):
            cls = candidate.get("class") or []
            if "_a6-o" in cls or "_2lem" in cls:
                ts_div = candidate  # keep last match to prefer the footer
        timestamp = _parse_html_timestamp(ts_div.get_text(" ", strip=True)) if ts_div else None
        if timestamp is None:
            # Skip cards whose timestamp couldn't be parsed; these are
            # typically layout shells rather than real posts.
            continue

        posts.append(
            {
                "creation_timestamp": timestamp,
                "title": caption,
                "media": media,
            }
        )

    # Instagram HTML timestamps are minute-granular (seconds always ":00"),
    # so multiple posts on the same minute would map to the same bundle id
    # (``ts-<timestamp>``) and overwrite each other. Bump colliding
    # timestamps by 1 second to keep every post distinct while preserving
    # chronological order.
    posts.sort(key=lambda p: p["creation_timestamp"])
    used: set[int] = set()
    for p in posts:
        ts = p["creation_timestamp"]
        while ts in used:
            ts += 1
        used.add(ts)
        p["creation_timestamp"] = ts

    return posts


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
    parser.add_argument(
        "--auto-publish",
        action="store_true",
        default=False,
        help=(
            "Apply the auto-publish policy (see AGENTS.md): newly-imported "
            "posts that look like impactful original content are marked "
            "draft: false, everything else stays draft: true. Mutually "
            "exclusive with --publish. Existing bundles are untouched."
        ),
    )
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    if args.publish and args.auto_publish:
        parser.error("--publish and --auto-publish are mutually exclusive")

    root, tmp = _open_takeout(args.takeout)
    try:
        posts_json = _locate_posts_json(root)
        if posts_json is not None:
            print(f"reading {posts_json.relative_to(root)}")
            data = json.loads(posts_json.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                posts = data.get("posts") or data.get("media") or []
            else:
                posts = data
        else:
            posts_html = _locate_posts_html(root)
            if posts_html is None:
                raise SystemExit(
                    f"Could not find posts_1.json or posts_1.html in {root}"
                )
            print(f"reading {posts_html.relative_to(root)} (HTML export)")
            posts = _load_posts_from_html(posts_html)
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

        policy: AutoPublishPolicy | None = (
            load_auto_publish_policy() if args.auto_publish else None
        )

        stats = ImportStats()
        for count, record in enumerate(records):
            if args.limit and count >= args.limit:
                break
            if policy is not None:
                publish, reason = evaluate_auto_publish(record, policy)
                record.draft = not publish
                verdict = "publish" if publish else "draft  "
                print(f"  [{verdict}] {record.post_id}: {reason}")
                if publish:
                    stats.auto_published += 1
                else:
                    stats.auto_drafted += 1
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
