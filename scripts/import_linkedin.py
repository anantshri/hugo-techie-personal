#!/usr/bin/env python3
"""Import a LinkedIn data export into ``content/archive/linkedin/``.

Usage
-----

    uv run --with pyyaml --with beautifulsoup4 --with markdownify python3 \
        themes/hugo-techie-personal/scripts/import_linkedin.py \
        --takeout takeouts/linkedin-2026-04-10.zip

Three content kinds are handled from a LinkedIn archive:

1. **Feed shares** (``Shares.csv``, in the "Complete" archive). Each row is a
   feed post identified by one of several LinkedIn URN types:

   * ``urn:li:activity:<id>`` — legacy shape kept for backward compat.
   * ``urn:li:share:<id>`` — most common shape in current exports.
   * ``urn:li:ugcPost:<id>`` — newer user-generated content (polls, carousels).
   * ``urn:li:groupPost:<group-id>-<post-id>`` — posts inside a LinkedIn group.

   ``ShareLink`` values are URL-encoded in the export (``urn%3Ali%3A…``); the
   importer decodes them before matching. Each URN is mapped to a typed folder
   (``content/archive/linkedin/<urn_type>-<id>/``) and a flattened URL
   (``/www.linkedin.com/feed/update/urn/li/<urn_type>/<id>/``) while preserving
   the canonical colon URL in ``original_url``. The smart 404 handler in the
   theme turns requests for the colon URL into a redirect to the folder path.

2. **Pulse articles** (``Articles/Articles/*.html``, shipped even in the "Basic"
   archive). Each HTML file is a long-form Pulse article authored on LinkedIn.
   Title, publish date and the canonical slug are extracted from the HTML; the
   article body is converted from HTML to Markdown. Bundle URL:
   ``/www.linkedin.com/pulse/<slug>/``.

3. **Plain reposts** (``InstantReposts.csv``, in the "Complete" archive). Each
   row is a repost-without-commentary action and contains only the parent
   post's URN, not a URN for the repost itself. Bundles land under
   ``content/archive/linkedin/repost-<urn_type>-<urn_id>/`` with an empty body
   and ``extra.reshare_of_url`` pointing at the parent. The template embeds the
   parent in a LinkedIn iframe so the archived page shows what was reshared.

Either source may be absent in a given archive. If all are missing the script
exits with an error; otherwise it processes whichever is present.

Reshare context for quote-reshares
----------------------------------

LinkedIn's export does **not** include the parent URN for reshares that carry
commentary (the common "reshare with your thoughts" flow). ``Shares.csv`` only
ships your commentary text and leaves ``SharedUrl`` empty. To recover the
parent for specific posts you can maintain an optional manual map at
``takeouts/linkedin-reshare-map.json``:

.. code-block:: json

    {
      "ugcPost-7411939790561890304":
        "https://www.linkedin.com/feed/update/urn:li:activity:7411359639843360768/",
      "share-7404293582125498370": "urn:li:activity:7404210000000000000"
    }

Keys are the bundle ``platform_id`` (``<urn_type.lower()>-<urn_id>``). Values
may be a full LinkedIn feed URL or a bare ``urn:li:...`` URN; the importer
normalises both into a canonical URL and writes it into
``extra.reshare_of_url``. The archive template embeds the parent as a LinkedIn
iframe below your commentary when this field is present.

If the archive also contains a ``media/`` directory with images referenced by
``MediaUrl``, those files are copied into the bundles.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _archive_common import (  # noqa: E402
    TAKEOUTS_ROOT,
    ArchiveRecord,
    AutoPublishPolicy,
    ImportStats,
    MediaItem,
    evaluate_auto_publish,
    guess_media_kind,
    load_auto_publish_policy,
    load_exclude_set,
    localize_inline_images,
    parse_utc,
    slugify,
    write_bundle,
)

SHARES_CSV = "Shares.csv"
INSTANT_REPOSTS_CSV = "InstantReposts.csv"
RESHARE_MAP_FILENAME = "linkedin-reshare-map.json"
# LinkedIn feed posts ship under several URN types: ``activity`` (legacy),
# ``share`` (most common), ``ugcPost`` (newer user-generated content: polls,
# multi-image carousels, etc.) and ``groupPost`` (posts inside a group, whose
# id is a composite ``<group-id>-<post-id>``). ``ShareLink`` values are usually
# URL-encoded (``urn%3Ali%3Ashare%3A<id>``) so we decode before matching.
URN_RE = re.compile(
    r"urn:li:(activity|share|ugcPost|groupPost):([\w-]+)", re.IGNORECASE
)
URN_TYPES = {"activity", "share", "ugcpost", "grouppost"}
PULSE_URL_RE = re.compile(
    r"https?://(?:www\.)?linkedin\.com/pulse/([^/?#\s]+)", re.IGNORECASE
)
ARTICLE_FILENAME_DATE_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})[T _]?(\d{2}:\d{2}:\d{2})"
)


def _canonical_urn_type(urn_type: str) -> str:
    """Return the canonical (LinkedIn-documented) casing for a URN type."""
    mapping = {
        "activity": "activity",
        "share": "share",
        "ugcpost": "ugcPost",
        "grouppost": "groupPost",
    }
    return mapping.get(urn_type.lower(), urn_type)


def _open_takeout(path: Path) -> tuple[Path, Path | None]:
    if path.is_dir():
        return path, None
    if path.is_file() and path.suffix.lower() == ".zip":
        tmp = Path(tempfile.mkdtemp(prefix="linkedin-takeout-"))
        with zipfile.ZipFile(path) as zf:
            zf.extractall(tmp)
        return tmp, tmp
    raise SystemExit(f"Takeout path not found or unsupported: {path}")


def _locate_shares_csv(root: Path) -> Path | None:
    direct = root / SHARES_CSV
    if direct.exists():
        return direct
    for match in root.rglob(SHARES_CSV):
        if match.is_file():
            return match
    return None


def _locate_instant_reposts_csv(root: Path) -> Path | None:
    direct = root / INSTANT_REPOSTS_CSV
    if direct.exists():
        return direct
    for match in root.rglob(INSTANT_REPOSTS_CSV):
        if match.is_file():
            return match
    return None


def _locate_articles_dir(root: Path) -> Path | None:
    """Locate the LinkedIn Pulse articles directory.

    LinkedIn exports place article HTML files at ``Articles/Articles/`` (yes,
    nested). Fall back to any directory named ``Articles`` that contains HTML
    files.
    """
    preferred = root / "Articles" / "Articles"
    if preferred.is_dir() and any(preferred.glob("*.html")):
        return preferred
    for candidate in root.rglob("Articles"):
        if not candidate.is_dir():
            continue
        nested = candidate / "Articles"
        if nested.is_dir() and any(nested.glob("*.html")):
            return nested
        if any(candidate.glob("*.html")):
            return candidate
    return None


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


def _extract_urn(share_link: str) -> tuple[str, str] | None:
    """Return ``(urn_type, id)`` for a LinkedIn share link, or ``None``.

    Handles both the URL-encoded form (``urn%3Ali%3Ashare%3A<id>``) used by the
    current export format and the plain colon form. Also tolerates legacy
    ``/activity-<id>`` style paths.
    """
    if not share_link:
        return None
    decoded = unquote(share_link)
    m = URN_RE.search(decoded)
    if m:
        return _canonical_urn_type(m.group(1)), m.group(2)
    m = re.search(r"/activity[-_:](\d+)", decoded, re.IGNORECASE)
    if m:
        return "activity", m.group(1)
    return None


def _normalize_reshare_url(value: str) -> str | None:
    """Return a canonical LinkedIn feed URL for a reshare target, or None.

    Accepts any of:

    * full ``https://www.linkedin.com/feed/update/urn:li:<type>:<id>/`` URLs
    * URL-encoded variants (``urn%3Ali%3A…``)
    * bare ``urn:li:<type>:<id>`` URNs

    All forms are normalised to the canonical colon URL the template already
    knows how to embed via ``https://www.linkedin.com/embed/feed/update/<urn>``.
    """
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    urn = _extract_urn(text)
    if urn is None:
        return None
    urn_type, urn_id = urn
    return f"https://www.linkedin.com/feed/update/urn:li:{urn_type}:{urn_id}/"


def _load_reshare_map() -> dict[str, str]:
    """Read ``takeouts/linkedin-reshare-map.json`` if present.

    Returns a mapping of ``<urn_type_lower>-<urn_id>`` bundle ids to canonical
    parent URLs. Bad entries are skipped with a warning; a missing file is
    silently an empty map (common case).
    """
    path = TAKEOUTS_ROOT / RESHARE_MAP_FILENAME
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"  ! ignoring malformed {RESHARE_MAP_FILENAME}: {exc}")
        return {}
    if not isinstance(data, dict):
        print(
            f"  ! {RESHARE_MAP_FILENAME} should be a JSON object, got "
            f"{type(data).__name__}; ignoring"
        )
        return {}
    out: dict[str, str] = {}
    for key, raw in data.items():
        if not isinstance(key, str) or not isinstance(raw, str):
            continue
        url = _normalize_reshare_url(raw)
        if url is None:
            print(f"  ! {RESHARE_MAP_FILENAME}: cannot parse URN from {raw!r}")
            continue
        out[key.strip().lower()] = url
    return out


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


def _parse_date_text(text: str) -> datetime | None:
    """Extract a UTC datetime from a 'Created on ...' / 'Published on ...' label."""
    if not text:
        return None
    m = re.search(r"(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}(?::\d{2})?))?", text)
    if not m:
        return None
    date_part = m.group(1)
    time_part = m.group(2) or "00:00:00"
    if len(time_part) == 5:
        time_part += ":00"
    try:
        return parse_utc(f"{date_part} {time_part}")
    except ValueError:
        return None


def _parse_filename_date(path: Path) -> datetime | None:
    m = ARTICLE_FILENAME_DATE_RE.match(path.name)
    if not m:
        return None
    try:
        return parse_utc(f"{m.group(1)} {m.group(2)}")
    except ValueError:
        return None


def _derive_article_slug(
    *, pulse_href: str | None, html_path: Path, title: str
) -> str:
    """Return the canonical slug for a Pulse article.

    Preference order:
    1. Slug from the in-HTML ``linkedin.com/pulse/<slug>`` href.
    2. Slug portion of the HTML filename (strip leading date + title prefix).
    3. Slugified title.
    """
    if pulse_href:
        m = PULSE_URL_RE.search(pulse_href)
        if m:
            return m.group(1).rstrip("-/")
    stem = html_path.stem
    # Filenames may start with "YYYY-MM-DD HH:MM:SS.0-<Title>" — strip the date.
    stem = re.sub(r"^\d{4}-\d{2}-\d{2}[ T_]\d{2}:\d{2}:\d{2}(?:\.\d+)?-", "", stem)
    candidate = slugify(stem, fallback="")
    if candidate:
        return candidate
    return slugify(title, fallback="pulse-article")


def _article_body_to_markdown(body_html_element) -> str:
    """Render the article's body HTML to Markdown, trimming trailing blanks."""
    from markdownify import markdownify as md

    html = str(body_html_element)
    text = md(html, heading_style="ATX", strip=["style", "script"])
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def _build_article_records(
    article_paths: Iterable[Path],
    *,
    user: str,
    exclude_ids: set[str],
    draft: bool,
    dry_run: bool = False,
) -> Iterable[ArchiveRecord]:
    from bs4 import BeautifulSoup

    for html_path in article_paths:
        try:
            html = html_path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"  ! cannot read {html_path.name}: {exc}")
            continue
        soup = BeautifulSoup(html, "lxml")
        h1 = soup.find("h1")
        if h1 is None:
            print(f"  ! no <h1> in {html_path.name}, skipping")
            continue
        anchor = h1.find("a")
        pulse_href = anchor.get("href") if anchor and anchor.has_attr("href") else None
        title = h1.get_text(" ", strip=True)

        published_el = soup.find(class_="published")
        created_el = soup.find(class_="created")
        date = (
            _parse_date_text(published_el.get_text(" ", strip=True) if published_el else "")
            or _parse_date_text(created_el.get_text(" ", strip=True) if created_el else "")
            or _parse_filename_date(html_path)
        )
        if date is None:
            print(f"  ! no date found for {html_path.name}, skipping")
            continue

        # LinkedIn's Pulse export includes unpublished drafts in the same
        # directory as real articles. Published ones carry a <span
        # class="published"> element; drafts typically only have
        # <span class="created">. Treat the absence of "published" as a
        # never-published signal so the auto-publish policy never promotes
        # these and the bundle ships as draft: true by default.
        is_pulse_draft = published_el is None

        slug = _derive_article_slug(pulse_href=pulse_href, html_path=html_path, title=title)
        if not slug or slug in exclude_ids:
            continue

        # Body is the last <div> sibling of <body>; fall back to all content after
        # the published paragraph.
        body_div = None
        if soup.body is not None:
            divs = [c for c in soup.body.children if getattr(c, "name", None) == "div"]
            if divs:
                body_div = divs[-1]
        body_md = _article_body_to_markdown(body_div) if body_div else ""

        # Pulse article bodies embed inline images via expiring media.licdn.com
        # signed URLs. Download them into static/images/archive/linkedin/<slug>/
        # and rewrite the markdown to reference /images/... so the content hash
        # is stable across re-imports and the archive keeps working once the
        # signed URLs rot.
        if body_md:
            body_md, img_stats = localize_inline_images(
                body_md,
                platform="linkedin",
                slug=slug,
                dry_run=dry_run,
            )
            if (
                img_stats["downloaded"]
                or img_stats["failed"]
                or img_stats["cached"]
            ):
                failed = len(img_stats["failed"])
                print(
                    f"  {html_path.name}: inline-images "
                    f"downloaded={img_stats['downloaded']} "
                    f"cached={img_stats['cached']} "
                    f"failed={failed}"
                )
                for url, reason in img_stats["failed"]:
                    print(f"    ! failed: {url} ({reason})")

        if pulse_href:
            original_url = pulse_href if pulse_href.endswith("/") else pulse_href + "/"
        else:
            original_url = f"https://www.linkedin.com/pulse/{slug}/"
        url = f"/www.linkedin.com/pulse/{slug}/"

        extra: dict = {"kind": "article_draft" if is_pulse_draft else "article"}
        if created_el:
            created_dt = _parse_date_text(created_el.get_text(" ", strip=True))
            if created_dt and created_dt != date:
                extra["created_at"] = created_dt.astimezone(timezone.utc).isoformat()

        # Drafts override the normal draft flag: a post that was never
        # published on LinkedIn should never ship as draft: false on our
        # mirror either, and should be hard-excluded from the auto-publish
        # policy regardless of body length or other signals. The user can
        # still manually flip draft: false on the bundle — the never_auto_publish
        # flag will remain sticky across importer re-runs.
        effective_draft = True if is_pulse_draft else draft
        yield ArchiveRecord(
            platform="linkedin",
            post_id=slug,
            url=url,
            original_url=original_url,
            date=date,
            title=title,
            body=body_md,
            platform_user=user,
            draft=effective_draft,
            never_auto_publish=is_pulse_draft,
            media=[],
            extra=extra,
        )


def _build_records(
    rows: Iterable[dict],
    *,
    media_root: Path | None,
    user: str,
    exclude_ids: set[str],
    draft: bool,
    reshare_map: dict[str, str],
) -> Iterable[ArchiveRecord]:
    for row in rows:
        share_link = row.get("ShareLink") or row.get("Share Link") or ""
        urn = _extract_urn(share_link)
        if urn is None:
            continue
        urn_type, urn_id = urn
        # Use a typed folder name so activity/share/ugcPost/groupPost can coexist
        # without collisions, and so folder names are self-describing.
        post_id = f"{urn_type.lower()}-{urn_id}"
        if urn_id in exclude_ids or post_id in exclude_ids:
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

        # Preserve canonical colon form in ``original_url`` (the 404 handler
        # flattens colons to slashes so pasting this URL still resolves). The
        # local ``url`` uses the flattened form directly.
        original_url = (
            f"https://www.linkedin.com/feed/update/urn:li:{urn_type}:{urn_id}/"
        )
        url = f"/www.linkedin.com/feed/update/urn/li/{urn_type}/{urn_id}/"

        visibility = (row.get("Visibility") or "").strip().lower()
        reshare_of_url = reshare_map.get(post_id.lower())
        yield ArchiveRecord(
            platform="linkedin",
            post_id=post_id,
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
                    "urn_type": urn_type,
                    "urn_id": urn_id,
                    "visibility": visibility,
                    "shared_url": shared_url,
                    "reshare_of_url": reshare_of_url,
                }.items()
                if v
            },
        )


def _build_instant_repost_records(
    rows: Iterable[dict],
    *,
    user: str,
    exclude_ids: set[str],
    draft: bool,
) -> Iterable[ArchiveRecord]:
    """Yield ArchiveRecords for plain reposts from ``InstantReposts.csv``.

    LinkedIn doesn't assign a distinct URN to a plain repost action — the
    ``Link`` column points at the parent post that was reshared. We mint a
    ``repost-<urn_type>-<urn_id>`` bundle id so these never collide with our
    own posts (which use ``<urn_type>-<urn_id>``) and stash the parent URL in
    ``extra.reshare_of_url`` for the template to embed.
    """
    for row in rows:
        link = (row.get("Link") or row.get("Url") or row.get("URL") or "").strip()
        urn = _extract_urn(link)
        if urn is None:
            continue
        urn_type, urn_id = urn
        post_id = f"repost-{urn_type.lower()}-{urn_id}"
        if urn_id in exclude_ids or post_id in exclude_ids:
            continue
        date_str = (row.get("Date") or row.get("Date Published") or "").strip()
        try:
            date = parse_utc(date_str)
        except ValueError:
            continue

        parent_url = (
            f"https://www.linkedin.com/feed/update/urn:li:{urn_type}:{urn_id}/"
        )
        # Local path for our browse index. Kept distinct from any feed-share
        # bundle we might also own for the same URN (highly unlikely, but
        # cheap to guarantee).
        url = f"/www.linkedin.com/reposts/{urn_type}/{urn_id}/"

        yield ArchiveRecord(
            platform="linkedin",
            post_id=post_id,
            url=url,
            original_url=parent_url,
            date=date,
            body="",
            title="Reposted a LinkedIn post",
            platform_user=user,
            draft=draft,
            media=[],
            extra={
                "kind": "repost",
                "urn_type": urn_type,
                "urn_id": urn_id,
                "reshare_of_url": parent_url,
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
        shares_csv = _locate_shares_csv(root)
        articles_dir = _locate_articles_dir(root)
        instant_reposts_csv = _locate_instant_reposts_csv(root)
        if shares_csv is None and articles_dir is None and instant_reposts_csv is None:
            raise SystemExit(
                f"No Shares.csv, Articles/ directory or InstantReposts.csv "
                f"found in {root}. Is this a LinkedIn takeout?"
            )

        media_root = _locate_media_root(root)
        if media_root:
            print(f"media root: {media_root.relative_to(root)}")

        exclude_ids = load_exclude_set()
        reshare_map = _load_reshare_map()
        if reshare_map:
            print(
                f"reshare map: {len(reshare_map)} quote-reshare parents loaded "
                f"from takeouts/{RESHARE_MAP_FILENAME}"
            )
        records: list[ArchiveRecord] = []

        if shares_csv is not None:
            print(f"reading shares: {shares_csv.relative_to(root)}")
            with shares_csv.open("r", encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                share_records = list(
                    _build_records(
                        reader,
                        media_root=media_root,
                        user=args.user,
                        exclude_ids=exclude_ids,
                        draft=not args.publish,
                        reshare_map=reshare_map,
                    )
                )
            print(f"found {len(share_records)} linkedin feed posts")
            records.extend(share_records)
        else:
            print(
                "no Shares.csv in this archive (Basic export?); "
                "skipping feed-post import"
            )

        if articles_dir is not None:
            print(f"reading articles: {articles_dir.relative_to(root)}")
            article_paths = sorted(articles_dir.glob("*.html"))
            article_records = list(
                _build_article_records(
                    article_paths,
                    user=args.user,
                    exclude_ids=exclude_ids,
                    draft=not args.publish,
                    dry_run=args.dry_run,
                )
            )
            print(f"found {len(article_records)} linkedin pulse articles")
            records.extend(article_records)

        if instant_reposts_csv is not None:
            print(f"reading reposts: {instant_reposts_csv.relative_to(root)}")
            with instant_reposts_csv.open(
                "r", encoding="utf-8-sig", newline=""
            ) as fh:
                reader = csv.DictReader(fh)
                repost_records = list(
                    _build_instant_repost_records(
                        reader,
                        user=args.user,
                        exclude_ids=exclude_ids,
                        draft=not args.publish,
                    )
                )
            print(f"found {len(repost_records)} linkedin plain reposts")
            records.extend(repost_records)
        else:
            print(
                "no InstantReposts.csv in this archive (Basic export?); "
                "skipping plain-repost import"
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

        print(f"linkedin import: {stats.summary()}")
    finally:
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
