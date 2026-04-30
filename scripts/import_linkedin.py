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
ships your commentary text and leaves ``SharedUrl`` empty. The importer
recovers the parent URN automatically by fetching LinkedIn's public embed
endpoint for each candidate post::

    https://www.linkedin.com/embed/feed/update/urn:li:<type>:<id>

If the embed HTML contains a ``data-test-id="feed-reshare-content"`` block
with a ``data-activity-urn`` attribute, that URN is the parent and is written
into ``extra.reshare_of_url``. Results are cached on disk at
``takeouts/.linkedin-reshare-cache.json`` so subsequent imports are offline
and instant. Non-reshare originals are also cached (``parent_url: null``) to
avoid re-fetching. Use ``--no-scrape-reshares`` to skip the network step
entirely, and ``--refresh-reshare-cache`` to invalidate the cache.

You can also maintain an optional manual override map at
``takeouts/linkedin-reshare-map.json``:

.. code-block:: json

    {
      "ugcPost-7411939790561890304":
        "https://www.linkedin.com/feed/update/urn:li:activity:7411939530704080896/",
      "share-7404293582125498370": "urn:li:activity:7404210000000000000"
    }

Keys are the bundle ``platform_id`` (``<urn_type.lower()>-<urn_id>``). Values
may be a full LinkedIn feed URL or a bare ``urn:li:...`` URN. Manual entries
**take precedence** over scraped results — useful when the scrape returns the
wrong parent (e.g. for deleted posts) or for posts where the public embed is
unavailable. The archive template embeds the parent as a LinkedIn iframe
below your commentary when ``reshare_of_url`` is present.

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
import time
import urllib.error
import urllib.request
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
    resolve_short_urls,
    rewrite_archive_body,
    save_short_url_cache,
    slugify,
    strip_tracking_params,
    write_bundle,
)

SHARES_CSV = "Shares.csv"
INSTANT_REPOSTS_CSV = "InstantReposts.csv"
RESHARE_MAP_FILENAME = "linkedin-reshare-map.json"
RESHARE_CACHE_FILENAME = ".linkedin-reshare-cache.json"
MENTION_MAP_FILENAME = "linkedin-mention-map.json"
MENTION_CACHE_FILENAME = ".linkedin-mentions-cache.json"
# Public embed endpoint that reveals (a) the parent URN of a reshare
# inside a ``data-test-id="feed-reshare-content"`` wrapper and (b) the
# fully-anchored ``@-mentions`` of any tagged people / companies in the
# post body. Works without authentication for posts whose author's
# profile allows public view (virtually all).
EMBED_URL_TEMPLATE = (
    "https://www.linkedin.com/embed/feed/update/urn:li:{urn_type}:{urn_id}"
)
FEED_RESHARE_RE = re.compile(
    r'data-test-id="feed-reshare-content"[^>]*'
    r'data-activity-urn="urn:li:activity:(\d+)"',
    re.IGNORECASE | re.DOTALL,
)
# LinkedIn embed pages render @-mentions as anchors that look like
# ``<a class="link" href="https://nl.linkedin.com/in/aseemjakhar?trk=public_post_embed-text"
#  target="_blank" data-tracking-control-name="public_post_embed-text" ...>Aseem Jakhar</a>``
# for people, and similarly with ``/company/<slug>`` for companies/pages.
#
# The reliable mention signal is the combination of (a) host matches
# ``linkedin.com/(in|company)/<slug>`` AND (b) the attribute
# ``data-tracking-control-name="public_post_embed-text"`` is present
# (other anchors on the page — the post author's name, the linked
# article card, social-share / sign-up CTAs — use distinct
# ``data-tracking-control-name`` values like ``…-feed-actor-name``,
# ``…_like-cta`` etc.). We extract every ``<a>`` and post-filter on
# both signals so attribute ordering changes upstream don't break the
# extraction.
ANCHOR_RE = re.compile(
    r'<a\b(?P<attrs>[^>]*?)>(?P<text>[^<]+?)</a>',
    re.DOTALL,
)
ATTR_RE = re.compile(
    r'(?P<name>[a-zA-Z_][a-zA-Z0-9_:-]*)\s*=\s*"(?P<value>[^"]*)"',
    re.DOTALL,
)
MENTION_HREF_RE = re.compile(
    r"^https?://(?:[a-z0-9-]+\.)?linkedin\.com/(?:in|company)/",
    re.IGNORECASE,
)
SCRAPE_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)
SCRAPE_REQUEST_DELAY_S = 0.5
SCRAPE_REQUEST_TIMEOUT_S = 20.0
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


def _load_reshare_cache() -> dict[str, dict]:
    """Read ``takeouts/.linkedin-reshare-cache.json`` if present.

    The cache memoises results from the public-embed scrape. Structure::

        {
          "share-7450442243523514368": {
            "parent_url": "https://www.linkedin.com/feed/update/urn:li:activity:74504.../",
            "fetched_at": "2026-04-19T12:00:00+00:00"
          },
          "share-1234": {
            "parent_url": null,   # scraped, not a reshare (original post)
            "fetched_at": "..."
          }
        }

    Missing file or malformed JSON silently yield an empty cache.
    """
    path = TAKEOUTS_ROOT / RESHARE_CACHE_FILENAME
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"  ! ignoring malformed {RESHARE_CACHE_FILENAME}: {exc}")
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        k: v
        for k, v in data.items()
        if isinstance(k, str) and isinstance(v, dict)
    }


def _save_reshare_cache(cache: dict[str, dict]) -> None:
    path = TAKEOUTS_ROOT / RESHARE_CACHE_FILENAME
    try:
        TAKEOUTS_ROOT.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(cache, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"  ! could not save {RESHARE_CACHE_FILENAME}: {exc}")


def _load_mention_map() -> dict[str, list[dict]]:
    """Read ``takeouts/linkedin-mention-map.json`` if present.

    Two shapes are accepted, mirroring the existing reshare-map layout:

    1. **Per-post override** — keyed by bundle ``platform_id``
       (``<urn_type_lower>-<urn_id>``). Values are lists of
       ``{"name": ..., "url": ...}`` dicts. Used to add or override
       mentions on a specific post::

          {
            "share-7445150664118231040": [
              {"name": "Aseem Jakhar", "url": "https://nl.linkedin.com/in/aseemjakhar"}
            ]
          }

    2. **Global name → URL** — a flat ``{name: url}`` map keyed by
       display name. Used as a backstop when the embed scrape returns
       no anchor for someone tagged in a body. Indicated by every
       value being a string::

          {
            "Aseem Jakhar": "https://nl.linkedin.com/in/aseemjakhar",
            "Akash Mahajan": "https://www.linkedin.com/in/akashm"
          }

    Returns a per-post dict with the global map injected under the
    pseudo-key ``"*"`` so ``_enrich_mentions`` can look it up cheaply.
    """
    path = TAKEOUTS_ROOT / MENTION_MAP_FILENAME
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"  ! ignoring malformed {MENTION_MAP_FILENAME}: {exc}")
        return {}
    if not isinstance(data, dict):
        print(
            f"  ! {MENTION_MAP_FILENAME} should be a JSON object, got "
            f"{type(data).__name__}; ignoring"
        )
        return {}

    out: dict[str, list[dict]] = {}
    global_pairs: list[dict] = []
    for key, raw in data.items():
        if not isinstance(key, str):
            continue
        if isinstance(raw, str):
            # Global name -> url entry.
            url = raw.strip()
            if url and key.strip():
                global_pairs.append({"name": key.strip(), "url": url})
            continue
        if isinstance(raw, list):
            cleaned: list[dict] = []
            for item in raw:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "").strip()
                url = str(item.get("url") or "").strip()
                if name and url:
                    cleaned.append({"name": name, "url": url})
            if cleaned:
                out[key.strip().lower()] = cleaned
    if global_pairs:
        out["*"] = global_pairs
    return out


def _load_mentions_cache() -> dict[str, dict]:
    """Read ``takeouts/.linkedin-mentions-cache.json`` if present.

    Cache schema mirrors the reshare cache but stores a list of
    ``{"name", "url"}`` entries plus a fetch timestamp::

        {
          "share-7445150664118231040": {
            "mentions": [
              {"name": "Aseem Jakhar", "url": "https://nl.linkedin.com/in/aseemjakhar"},
              ...
            ],
            "fetched_at": "2026-04-29T12:00:00+00:00"
          },
          "share-9999": {"mentions": [], "fetched_at": "..."}
        }

    Empty ``mentions`` lists are valid: they record posts that have no
    @-mentions so re-runs don't re-hit the network.
    """
    path = TAKEOUTS_ROOT / MENTION_CACHE_FILENAME
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"  ! ignoring malformed {MENTION_CACHE_FILENAME}: {exc}")
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        k: v
        for k, v in data.items()
        if isinstance(k, str) and isinstance(v, dict)
    }


def _save_mentions_cache(cache: dict[str, dict]) -> None:
    path = TAKEOUTS_ROOT / MENTION_CACHE_FILENAME
    try:
        TAKEOUTS_ROOT.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(cache, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"  ! could not save {MENTION_CACHE_FILENAME}: {exc}")


# In-memory embed-HTML cache for the current import run. Keyed by
# ``(urn_type, urn_id)``; values are ``str`` (HTML), ``None`` (loaded but
# not found / 404), or ``False`` (transient network failure). Reshare
# detection and mention extraction both consult this cache so each post
# is fetched at most once per run, even when both enrichment passes are
# enabled.
_embed_html_cache: dict[tuple[str, str], str | None | bool] = {}


def _scrape_embed_html(urn_type: str, urn_id: str) -> str | None | bool:
    """Fetch (and per-run-cache) the LinkedIn public embed HTML for a URN.

    Returns:
        * the raw HTML string on a successful fetch.
        * ``None`` on a definitive "not available" response (HTTP 404/410
          or empty body). Callers should cache this as "not a recoverable
          target".
        * ``False`` on a transient network error (timeouts, 5xx, DNS).
          Callers should *not* persist this so a future run can retry.
    """
    key = (urn_type, urn_id)
    if key in _embed_html_cache:
        return _embed_html_cache[key]

    url = EMBED_URL_TEMPLATE.format(urn_type=urn_type, urn_id=urn_id)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": SCRAPE_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=SCRAPE_REQUEST_TIMEOUT_S) as resp:
            if resp.status != 200:
                _embed_html_cache[key] = False
                return False
            html = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        if exc.code in (404, 410):
            _embed_html_cache[key] = None
            return None
        _embed_html_cache[key] = False
        return False
    except (urllib.error.URLError, TimeoutError, OSError):
        _embed_html_cache[key] = False
        return False

    if not html:
        _embed_html_cache[key] = None
        return None

    _embed_html_cache[key] = html
    return html


def _parse_reshare_parent_from_html(html: str) -> str | None:
    """Return the canonical parent feed URL when ``html`` is a reshare embed.

    Returns ``None`` when the embed isn't a reshare (no
    ``feed-reshare-content`` block).
    """
    m = FEED_RESHARE_RE.search(html)
    if not m:
        return None
    return f"https://www.linkedin.com/feed/update/urn:li:activity:{m.group(1)}/"


def _parse_mentions_from_html(html: str) -> list[dict]:
    """Return ``[{"name": ..., "url": ...}, ...]`` for every @-mention in
    the embed.

    Mentions are anchors that (a) link to ``linkedin.com/(in|company)/<slug>``
    and (b) carry ``data-tracking-control-name="public_post_embed-text"``.
    The trailing ``?trk=…`` tracking parameter on the href is stripped via
    :func:`strip_tracking_params`. Duplicate names are de-duplicated
    (longest URL wins, then first occurrence) so a name tagged twice in
    the same post yields one mention entry.
    """
    if not html:
        return []
    seen: dict[str, str] = {}
    order: list[str] = []
    for m in ANCHOR_RE.finditer(html):
        attrs = m.group("attrs") or ""
        text = (m.group("text") or "").strip()
        if not text:
            continue
        attr_map = {
            am.group("name").lower(): am.group("value")
            for am in ATTR_RE.finditer(attrs)
        }
        if attr_map.get("data-tracking-control-name") != "public_post_embed-text":
            continue
        href = attr_map.get("href") or ""
        if not MENTION_HREF_RE.match(href):
            continue
        cleaned = strip_tracking_params(href)
        # Drop a trailing slash difference so the cache hits the same key
        # whether or not LinkedIn appends one to the embed-rendered URL.
        if cleaned not in seen:
            seen[cleaned] = text
            order.append(cleaned)
    out: list[dict] = []
    for url in order:
        out.append({"name": seen[url], "url": url})
    return out


def _scrape_reshare_parent(urn_type: str, urn_id: str) -> str | None | bool:
    """Backwards-compatible wrapper: fetch the embed, parse reshare parent."""
    html = _scrape_embed_html(urn_type, urn_id)
    if html is None or html is False:
        return html
    return _parse_reshare_parent_from_html(html)


def _scrape_post_mentions(
    urn_type: str, urn_id: str
) -> list[dict] | None | bool:
    """Fetch the embed and return @-mention anchors.

    Mirrors :func:`_scrape_reshare_parent`: returns a (possibly empty)
    list of ``{"name", "url"}`` dicts on a successful fetch (empty when
    the post had no mentions), ``None`` on definitive 404/410, or
    ``False`` on transient network failure.
    """
    html = _scrape_embed_html(urn_type, urn_id)
    if html is None or html is False:
        return html
    return _parse_mentions_from_html(html)


def _enrich_reshare_parents(
    records: list[ArchiveRecord],
    *,
    manual_map: dict[str, str],
    scrape: bool,
    refresh_cache: bool,
    dry_run: bool,
) -> None:
    """Populate ``extra.reshare_of_url`` on share records that lack it.

    Priority:
      1. Existing value (set from the manual map at record-build time). If
         ``refresh_cache`` is true, manual-map values still win — they are the
         user's explicit override.
      2. On-disk scrape cache (``takeouts/.linkedin-reshare-cache.json``).
      3. Fresh HTTP scrape of LinkedIn's public embed endpoint.

    Only feed-share records are processed. InstantRepost records already have
    a reliable ``reshare_of_url`` from the CSV, Pulse articles have no URN
    context, and records already annotated by the manual map are left alone.
    """
    candidates: list[ArchiveRecord] = []
    for rec in records:
        if rec.post_id.startswith("repost-"):
            continue
        urn_type = rec.extra.get("urn_type")
        urn_id = rec.extra.get("urn_id")
        if not urn_type or not urn_id:
            continue
        if rec.extra.get("reshare_of_url"):
            # Manual map already supplied a value; respect it.
            continue
        candidates.append(rec)

    if not candidates:
        return

    cache = _load_reshare_cache()
    cache_hits = 0
    scraped_reshare = 0
    scraped_original = 0
    scrape_errors = 0
    dirty = False

    for idx, rec in enumerate(candidates, start=1):
        key = rec.post_id.lower()
        urn_type = rec.extra["urn_type"]
        urn_id = rec.extra["urn_id"]

        # Manual map wins even here (override scraped cache entries).
        manual = manual_map.get(key)
        if manual:
            rec.extra["reshare_of_url"] = manual
            continue

        if not refresh_cache and key in cache:
            cached = cache[key]
            cache_hits += 1
            parent = cached.get("parent_url")
            if parent:
                rec.extra["reshare_of_url"] = parent
            continue

        if not scrape:
            continue

        parent = _scrape_reshare_parent(urn_type, urn_id)
        if parent is False:
            scrape_errors += 1
            # Don't cache failures so we retry next run.
            continue
        cache[key] = {
            "parent_url": parent,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        dirty = True
        if parent:
            rec.extra["reshare_of_url"] = parent
            scraped_reshare += 1
        else:
            scraped_original += 1
        if idx % 20 == 0 or idx == len(candidates):
            print(
                f"  reshare scrape: {idx}/{len(candidates)} "
                f"(reshare={scraped_reshare} original={scraped_original} "
                f"error={scrape_errors})"
            )
        time.sleep(SCRAPE_REQUEST_DELAY_S)

    if dirty and not dry_run:
        _save_reshare_cache(cache)

    print(
        "reshare enrichment: "
        f"candidates={len(candidates)} cache_hits={cache_hits} "
        f"scraped_reshare={scraped_reshare} scraped_original={scraped_original} "
        f"scrape_errors={scrape_errors}"
    )


def _enrich_mentions(
    records: list[ArchiveRecord],
    *,
    manual_map: dict[str, list[dict]],
    scrape: bool,
    refresh_cache: bool,
    dry_run: bool,
) -> None:
    """Populate ``extra.mentions`` on share records that have a URN.

    Priority for each record:
      1. Per-post manual override (``manual_map[post_id]``) — wins outright.
      2. On-disk cache (``takeouts/.linkedin-mentions-cache.json``).
      3. Fresh HTTP scrape of LinkedIn's public embed endpoint.

    The global name → URL map is layered *on top* of every result as a
    backstop: every name from the global map whose URL isn't already
    present is appended. This lets a user maintain a small "known
    contacts" map that fills in gaps the embed scrape can't (deleted
    accounts, scrape misses, etc.).

    Pulse articles (``extra.kind == "article"`` / ``"article_draft"``)
    are skipped — the embed endpoint only exposes feed-share posts.
    InstantRepost records have no original body of their own. Records
    with ``extra.kind == "repost"`` are skipped on the same grounds.
    """
    candidates: list[ArchiveRecord] = []
    for rec in records:
        if rec.post_id.startswith("repost-"):
            continue
        kind = rec.extra.get("kind")
        if kind in {"article", "article_draft", "repost"}:
            continue
        urn_type = rec.extra.get("urn_type")
        urn_id = rec.extra.get("urn_id")
        if not urn_type or not urn_id:
            continue
        candidates.append(rec)

    if not candidates and not manual_map:
        return

    cache = _load_mentions_cache()
    cache_hits = 0
    scraped_with = 0
    scraped_without = 0
    scrape_errors = 0
    dirty = False
    global_pairs: list[dict] = manual_map.get("*", [])

    def _merge_global(mentions: list[dict]) -> list[dict]:
        if not global_pairs:
            return mentions
        seen_urls = {m["url"] for m in mentions if isinstance(m, dict)}
        merged = list(mentions)
        for entry in global_pairs:
            if entry["url"] not in seen_urls:
                merged.append(entry)
                seen_urls.add(entry["url"])
        return merged

    for idx, rec in enumerate(candidates, start=1):
        key = rec.post_id.lower()
        urn_type = rec.extra["urn_type"]
        urn_id = rec.extra["urn_id"]

        # Manual map wins outright.
        manual = manual_map.get(key)
        if manual:
            rec.extra["mentions"] = _merge_global(list(manual))
            continue

        if not refresh_cache and key in cache:
            cached = cache[key]
            cache_hits += 1
            mentions = cached.get("mentions") or []
            if not isinstance(mentions, list):
                mentions = []
            cleaned = [
                {"name": str(m.get("name") or "").strip(),
                 "url": str(m.get("url") or "").strip()}
                for m in mentions
                if isinstance(m, dict)
            ]
            cleaned = [m for m in cleaned if m["name"] and m["url"]]
            merged = _merge_global(cleaned)
            if merged:
                rec.extra["mentions"] = merged
            continue

        if not scrape:
            # Even without a fresh scrape, surface global mentions.
            merged = _merge_global([])
            if merged:
                rec.extra["mentions"] = merged
            continue

        scraped = _scrape_post_mentions(urn_type, urn_id)
        if scraped is False:
            scrape_errors += 1
            # Don't cache failures so we retry next run. Still apply
            # globals so manual entries surface even on a flaky network.
            merged = _merge_global([])
            if merged:
                rec.extra["mentions"] = merged
            continue
        # Successful fetch (possibly empty list, or None for 404/410).
        mentions = list(scraped) if scraped else []
        cache[key] = {
            "mentions": mentions,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        dirty = True
        if mentions:
            scraped_with += 1
        else:
            scraped_without += 1
        merged = _merge_global(mentions)
        if merged:
            rec.extra["mentions"] = merged
        if idx % 20 == 0 or idx == len(candidates):
            print(
                f"  mention scrape: {idx}/{len(candidates)} "
                f"(with={scraped_with} without={scraped_without} "
                f"error={scrape_errors})"
            )
        time.sleep(SCRAPE_REQUEST_DELAY_S)

    if dirty and not dry_run:
        _save_mentions_cache(cache)

    print(
        "mention enrichment: "
        f"candidates={len(candidates)} cache_hits={cache_hits} "
        f"scraped_with={scraped_with} scraped_without={scraped_without} "
        f"scrape_errors={scrape_errors}"
    )


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
    resolve_short: bool,
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
            body_md = _maybe_resolve_short_urls(
                body_md,
                enabled=resolve_short,
                dry_run=dry_run,
                label=html_path.name,
            )

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


def _clean_shares_csv_line_quotes(body: str) -> str:
    """Undo LinkedIn's broken per-line double-quoting in ``Shares.csv``.

    For multi-line share commentary LinkedIn wraps **each individual line**
    of the body in its own ``"..."`` pair inside an already CSV-quoted field.
    Every inner quote is escaped as ``""``, so after standard csv decoding
    each paragraph ends up looking like ``"...text..."`` on its own line and
    blank paragraphs show up as a lone ``""`` (or occasionally a stray ``"``).

    The first line's leading quote is consumed by the csv parser as the
    field opener, so only lines 2+ exhibit the full ``"..."`` wrapping; the
    first line only keeps its trailing ``"``. The final line may end with a
    dangling ``"`` from the closing artifact.

    Only activate the cleanup when *every* non-first line matches the
    artifact pattern so that legitimately quoted text inside a short,
    single-paragraph commentary is never touched.
    """
    if "\n" not in body:
        return body
    lines = body.split("\n")
    # Gate on a clear artifact signature: the first line must end with a
    # stray closing ``"`` (the paragraph's own close, since the field opener
    # ate its leading ``"``), and every subsequent line must look like a
    # wrapped paragraph, a blank artifact, or — for the final line whose
    # trailing ``"`` was consumed by the field closer — at least start with
    # ``"``.
    if not lines[0].endswith('"'):
        return body
    if len(lines) < 2:
        return body
    for idx, line in enumerate(lines[1:], start=1):
        if line in ("", '"', '""'):
            continue
        if len(line) >= 2 and line.startswith('"') and line.endswith('"'):
            continue
        if idx == len(lines) - 1 and line.startswith('"'):
            continue
        return body
    cleaned: list[str] = [lines[0][:-1]]
    for idx, line in enumerate(lines[1:], start=1):
        if line in ("", '"', '""'):
            cleaned.append("")
        elif len(line) >= 2 and line.startswith('"') and line.endswith('"'):
            cleaned.append(line[1:-1])
        elif idx == len(lines) - 1 and line.startswith('"'):
            cleaned.append(line[1:])
        else:
            cleaned.append(line)
    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    return "\n".join(cleaned)


def _maybe_resolve_short_urls(
    text: str,
    *,
    enabled: bool,
    dry_run: bool,
    label: str,
) -> str:
    """Resolve ``lnkd.in`` short URLs in ``text`` and log a one-liner per post.

    Thin wrapper around :func:`_archive_common.resolve_short_urls` that only
    prints a progress line when there's actually something to report, so the
    common case (no ``lnkd.in`` URLs in this post) stays quiet.
    """
    if not enabled or not text or "lnkd.in" not in text.lower():
        return text
    new_text, stats = resolve_short_urls(text, dry_run=dry_run)
    if stats["rewritten"] or stats["failed"]:
        failed_count = len(stats["failed"])
        print(
            f"  {label}: lnkd.in "
            f"resolved={stats['resolved']} "
            f"cached={stats['cached']} "
            f"failed={failed_count}"
        )
        for short, reason in stats["failed"]:
            print(f"    ! could not resolve {short} ({reason})")
    return new_text


def _build_records(
    rows: Iterable[dict],
    *,
    media_root: Path | None,
    user: str,
    exclude_ids: set[str],
    draft: bool,
    reshare_map: dict[str, str],
    resolve_short: bool,
    dry_run: bool,
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
        )
        body_raw = _clean_shares_csv_line_quotes(body_raw).strip()
        shared_url = (
            row.get("SharedUrl")
            or row.get("Shared Url")
            or row.get("SharedURL")
            or ""
        ).strip()
        body_parts = [p for p in (body_raw, shared_url) if p]
        body = "\n\n".join(body_parts)
        body = _maybe_resolve_short_urls(
            body,
            enabled=resolve_short,
            dry_run=dry_run,
            label=f"{urn_type.lower()}-{urn_id}",
        )
        if shared_url and resolve_short and "lnkd.in" in shared_url.lower():
            # Also resolve the ``SharedUrl`` we stash into ``extra.shared_url``
            # so the frontmatter field doesn't keep a dead/obfuscated
            # ``lnkd.in`` link when the body version got rewritten to the real
            # destination above.
            resolved_shared, _stats = resolve_short_urls(
                shared_url, dry_run=dry_run
            )
            shared_url = resolved_shared

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
    parser.add_argument(
        "--no-scrape-reshares",
        action="store_true",
        default=False,
        help=(
            "Skip the public-embed scrape used to recover quote-reshare "
            "parent URNs. Cached results and the manual map are still "
            "applied; uncached candidates simply won't get an embed."
        ),
    )
    parser.add_argument(
        "--refresh-reshare-cache",
        action="store_true",
        default=False,
        help=(
            "Re-fetch every quote-reshare candidate, ignoring the on-disk "
            "cache at takeouts/.linkedin-reshare-cache.json. Manual-map "
            "overrides still win."
        ),
    )
    parser.add_argument(
        "--no-scrape-mentions",
        action="store_true",
        default=False,
        help=(
            "Skip the public-embed scrape used to recover @-mention "
            "profile links from share posts. Cached mentions and the "
            "manual map at takeouts/linkedin-mention-map.json are still "
            "applied; uncached candidates simply won't have their "
            "tagged people resolved to clickable links."
        ),
    )
    parser.add_argument(
        "--refresh-mention-cache",
        action="store_true",
        default=False,
        help=(
            "Re-fetch every share's @-mentions, ignoring the on-disk "
            "cache at takeouts/.linkedin-mentions-cache.json. Manual-map "
            "overrides still win."
        ),
    )
    parser.add_argument(
        "--no-resolve-short-urls",
        dest="resolve_short_urls",
        action="store_false",
        default=True,
        help=(
            "Do not resolve https://lnkd.in/ short URLs to their final "
            "destinations. By default the importer follows each short URL "
            "once and rewrites the body to reference the real link, caching "
            "results in takeouts/lnkd-in-cache.json."
        ),
    )
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
        mention_map = _load_mention_map()
        if mention_map:
            per_post = sum(1 for k in mention_map if k != "*")
            global_count = len(mention_map.get("*", []))
            print(
                f"mention map: {per_post} per-post override(s), "
                f"{global_count} global name(s) loaded from "
                f"takeouts/{MENTION_MAP_FILENAME}"
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
                        resolve_short=args.resolve_short_urls,
                        dry_run=args.dry_run,
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
                    resolve_short=args.resolve_short_urls,
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

        _enrich_reshare_parents(
            records,
            manual_map=reshare_map,
            scrape=not args.no_scrape_reshares,
            refresh_cache=args.refresh_reshare_cache,
            dry_run=args.dry_run,
        )

        _enrich_mentions(
            records,
            manual_map=mention_map,
            scrape=not args.no_scrape_mentions,
            refresh_cache=args.refresh_mention_cache,
            dry_run=args.dry_run,
        )

        # Final body rewrite: mention substitution, standalone-URL embed,
        # bare-URL autolinking, tracking-param strip. Done after both
        # enrichment passes so mentions are populated before substitution
        # runs. The ``mentions`` payload stays on ``extra`` for posterity
        # (so a re-run sees the same cache key without another scrape) but
        # ``rewrite_archive_body`` consumes only ``(name, url)`` tuples.
        for record in records:
            if not record.body:
                continue
            mentions = record.extra.get("mentions") or []
            mention_pairs = [
                (str(m.get("name") or ""), str(m.get("url") or ""))
                for m in mentions
                if isinstance(m, dict)
            ]
            record.body = rewrite_archive_body(
                record.body, mentions=mention_pairs
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
        save_short_url_cache()
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
