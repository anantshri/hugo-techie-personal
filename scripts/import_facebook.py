#!/usr/bin/env python3
"""Import a Facebook data export into ``content/archive/facebook/``.

Both the JSON-format and the HTML-format data exports are supported. Facebook
used to ship HTML-only; newer takeouts let you pick. The importer auto-detects
the format.

Usage
-----

    # JSON format
    uv run --with pyyaml python3 themes/hugo-techie-personal/scripts/import_facebook.py \
        --takeout takeouts/facebook-2026-04-10.zip \
        --user anantshrivastava

    # HTML format (requires beautifulsoup4 + lxml)
    uv run --with pyyaml --with beautifulsoup4 --with lxml python3 \
        themes/hugo-techie-personal/scripts/import_facebook.py \
        --takeout takeouts/facebook-anantshri.zip \
        --user anantshrivastava

Facebook's JSON export stores your posts in files named like
``your_facebook_activity/posts/your_posts__check_ins__photos_and_videos_1.json``.
Each entry has a ``timestamp``, a ``data`` list (usually containing the post
text under ``post``) and optional ``attachments`` referencing media files that
live elsewhere in the archive. The HTML export renders the same information
inside ``posts/your_posts_1.html``; the importer parses each ``.pam.uiBoxWhite``
post card and filters out empty "Updated <date>" album filler rows.

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
from datetime import datetime, timezone
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

POSTS_HTML_GLOBS = (
    "posts/your_posts_*.html",
    "your_facebook_activity/posts/your_posts_*.html",
)

# Facebook HTML timestamps look like "17 Aug 2019, 00:13" or
# "8 Apr 2021, 21:40". Some locales also emit a trailing am/pm.
_FB_HTML_DATE_FORMATS = (
    "%d %b %Y, %H:%M",
    "%d %b %Y %H:%M",
    "%b %d, %Y, %I:%M %p",
    "%b %d, %Y %I:%M %p",
)

# Media roots used for local attachments in the HTML export.
_HTML_MEDIA_PREFIXES = (
    "photos_and_videos/",
    "photos/",
    "videos/",
    "media/",
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
    return []


def _locate_posts_html_files(root: Path) -> list[Path]:
    results: list[Path] = []
    for pattern in POSTS_HTML_GLOBS:
        results.extend(sorted(root.glob(pattern)))
    if results:
        seen: set[Path] = set()
        unique: list[Path] = []
        for p in results:
            rp = p.resolve()
            if rp not in seen:
                seen.add(rp)
                unique.append(p)
        return unique
    fallback = [
        p
        for p in root.rglob("your_posts_*.html")
        if p.is_file() and "posts" in p.parts
    ]
    return sorted(fallback)


def _parse_fb_html_timestamp(text: str) -> int | None:
    """Parse a Facebook HTML timestamp string into epoch seconds (UTC)."""
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return None
    normalised = re.sub(r"\b([ap])m\b", lambda m: m.group(1).upper() + "M", cleaned)
    for fmt in _FB_HTML_DATE_FORMATS:
        try:
            dt = datetime.strptime(normalised, fmt)
        except ValueError:
            continue
        return int(dt.replace(tzinfo=timezone.utc).timestamp())
    return None


def _html_text(node) -> str:
    """Return readable text from a BeautifulSoup node, preserving <br> as newlines."""
    if node is None:
        return ""
    from bs4 import NavigableString  # local import — only needed on HTML path

    # Replace <br> tags with literal newlines so get_text doesn't collapse them.
    for br in node.find_all("br"):
        br.replace_with(NavigableString("\n"))
    text = node.get_text("\n", strip=False)
    # Collapse runs of blank lines and trim trailing whitespace on each line.
    lines = [line.strip() for line in text.splitlines()]
    # Drop leading/trailing empty lines and squash >1 consecutive blanks.
    cleaned: list[str] = []
    prev_blank = True
    for line in lines:
        if not line:
            if prev_blank:
                continue
            cleaned.append("")
            prev_blank = True
        else:
            cleaned.append(line)
            prev_blank = False
    while cleaned and not cleaned[-1]:
        cleaned.pop()
    return "\n".join(cleaned).strip()


def _load_posts_from_html(html_paths: list[Path]) -> list[dict]:
    """Parse Facebook HTML ``your_posts_*.html`` files into JSON-shaped dicts.

    Returns a list shaped like the JSON export entries so ``_build_records``
    can consume it unchanged::

        [{"timestamp": 1566003180,
          "title": "Anant Shrivastava added a new photo.",
          "data": [{"post": "body text..."}],
          "attachments": [{"data": [{"media": {"uri": "photos_and_videos/.../foo.jpg"}}]}]}]

    Empty "Updated <date>" album filler cards (no body text AND no local
    media) are skipped.
    """
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "HTML Facebook export detected but beautifulsoup4 is not installed. "
            "Re-run with: uv run --with pyyaml --with beautifulsoup4 --with lxml python3 ..."
        ) from exc

    posts: list[dict] = []
    for html_path in html_paths:
        html = html_path.read_text(encoding="utf-8", errors="replace")
        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            soup = BeautifulSoup(html, "html.parser")

        container = soup.find(class_="_4t5n") or soup.body or soup
        for card in container.find_all("div", class_="pam"):
            classes = card.get("class") or []
            if "uiBoxWhite" not in classes:
                continue

            # --- attribution header (optional) -----------------------------
            header = ""
            header_div = card.find("div", class_="_2lek")
            if header_div:
                header_text = _html_text(header_div)
                if header_text:
                    header = header_text

            # --- body ------------------------------------------------------
            body_parts: list[str] = []
            body_div = card.find("div", class_="_2let")
            if body_div is None:
                # Occasionally posts use ``_2lek`` alone for text content.
                body_div = None if header_div else card
            if body_div is not None:
                body_text = _html_text(body_div)
                if body_text:
                    body_parts.append(body_text)
            body = "\n\n".join(p for p in body_parts if p).strip()

            # --- media -----------------------------------------------------
            media_uris: list[str] = []
            seen: set[str] = set()
            for tag in card.find_all(["a", "img", "video", "source"]):
                candidate = tag.get("href") or tag.get("src")
                if not candidate:
                    continue
                candidate = candidate.strip()
                if candidate.startswith("./"):
                    candidate = candidate[2:]
                if not candidate.startswith(_HTML_MEDIA_PREFIXES):
                    continue
                if candidate in seen:
                    continue
                seen.add(candidate)
                media_uris.append(candidate)

            # --- timestamp -------------------------------------------------
            ts_div = None
            for div in card.find_all("div"):
                cls = div.get("class") or []
                if "_2lem" in cls:
                    ts_div = div  # last wins (typically the footer)
            ts_text = ""
            if ts_div is not None:
                # The anchor text carries the human-readable date.
                anchor = ts_div.find("a")
                ts_text = (anchor.get_text(" ", strip=True) if anchor else ts_div.get_text(" ", strip=True))
            timestamp = _parse_fb_html_timestamp(ts_text) if ts_text else None
            if timestamp is None:
                continue

            # --- filter noise ---------------------------------------------
            # Empty album "Updated …" rows have no attribution header, no
            # local media, and a body that only says ``Updated <date>``.
            if not media_uris and not header:
                if not body:
                    continue
                if re.match(r"^updated\s+\d", body, re.IGNORECASE):
                    continue

            attachments = [
                {"data": [{"media": {"uri": uri}}]} for uri in media_uris
            ]

            post_entry: dict = {
                "timestamp": timestamp,
                "data": [{"post": body}] if body else [],
                "attachments": attachments,
            }
            if header:
                post_entry["title"] = header
            posts.append(post_entry)

    # Facebook HTML timestamps are minute-granular, so many posts collapse to
    # the same epoch second. The bundle id is keyed on timestamp, so naive
    # collisions would cause later posts to overwrite earlier ones. Bump
    # each colliding timestamp by 1 second until unique — small enough that
    # chronological order is preserved, large enough to give every post its
    # own bundle.
    posts.sort(key=lambda p: p["timestamp"])
    used: set[int] = set()
    for p in posts:
        ts = p["timestamp"]
        while ts in used:
            ts += 1
        used.add(ts)
        p["timestamp"] = ts

    return posts


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
        posts: list[dict] = []
        if posts_files:
            print(f"reading {len(posts_files)} JSON posts file(s):")
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
        else:
            html_files = _locate_posts_html_files(root)
            if not html_files:
                raise SystemExit(
                    "Could not find posts JSON or HTML in Facebook takeout. "
                    "Looked for JSON: " + ", ".join(POSTS_GLOBS)
                    + "; HTML: " + ", ".join(POSTS_HTML_GLOBS)
                )
            print(f"reading {len(html_files)} HTML posts file(s):")
            for hf in html_files:
                print(f"  - {hf.relative_to(root)}")
            posts = _load_posts_from_html(html_files)

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
