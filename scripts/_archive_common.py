"""Shared helpers for social archive importers shipped with the
``hugo-techie-personal`` theme.

Used by the sibling ``import_twitter.py``, ``import_linkedin.py``,
``import_instagram.py`` and ``import_facebook.py`` to write Hugo page bundles
under ``content/archive/<platform>/<id>/`` with media files as page resources.

Each bundle is idempotent: a ``.manifest.json`` file in the bundle stores the
content hash of the source record plus the list of media files. Re-running an
importer only rewrites the bundle when the hash changes.

Site-root resolution
--------------------

These scripts live inside the theme at
``<site>/themes/hugo-techie-personal/scripts/`` so they can be shipped as a
theme feature. The site root is resolved as follows (first match wins):

1. ``HUGO_SITE_ROOT`` environment variable, if set.
2. ``<script>/../../..`` — the conventional theme layout
   (``<site>/themes/<theme>/scripts/<script>.py``).
3. ``Path.cwd()`` fallback.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import yaml


def _resolve_site_root() -> Path:
    env = os.environ.get("HUGO_SITE_ROOT")
    if env:
        p = Path(env).expanduser().resolve()
        if p.is_dir():
            return p
    # themes/<theme>/scripts/<this-file>.py  →  parents[3] is the site root
    candidate = Path(__file__).resolve().parents[3]
    if (candidate / "content").is_dir() or (candidate / "hugo.toml").exists() or (
        candidate / "config.toml"
    ).exists():
        return candidate
    return Path.cwd().resolve()


SITE_ROOT = _resolve_site_root()
CONTENT_ROOT = SITE_ROOT / "content" / "archive"
TAKEOUTS_ROOT = SITE_ROOT / "takeouts"

PLATFORMS = ("twitter", "linkedin", "instagram", "facebook")

MANIFEST_NAME = ".manifest.json"

AUTO_PUBLISH_CONFIG_FILENAME = "auto-publish.yml"

DEFAULT_OWN_DOMAINS: tuple[str, ...] = (
    "anantshri.info",
    "cyfinoid.com",
)

DEFAULT_OWN_GITHUB_ORGS: tuple[str, ...] = (
    "anantshri",
    "cyfinoid",
    "AndroidTamer",
    "CodeVigilant",
)


@dataclass
class MediaItem:
    """A media attachment to be copied into a bundle and referenced in frontmatter."""

    src_path: Path
    kind: str  # "image" | "video" | "gif"
    alt: str = ""
    poster_src: Path | None = None

    def target_basename(self, index: int) -> str:
        suffix = self.src_path.suffix.lower() or ".bin"
        return f"media-{index}{suffix}"

    def poster_basename(self, index: int) -> str | None:
        if not self.poster_src:
            return None
        suffix = self.poster_src.suffix.lower() or ".jpg"
        return f"media-{index}-poster{suffix}"


@dataclass
class ArchiveRecord:
    """Normalized representation of a single social post across platforms."""

    platform: str  # "twitter" | "linkedin" | "instagram" | "facebook"
    post_id: str
    url: str  # site-relative path, e.g. "/x.com/user/status/123/"
    original_url: str
    date: datetime
    body: str  # post text as markdown-safe content
    title: str = ""  # if empty, derived from body
    platform_user: str = ""
    reply_to: str = ""
    retweet_of: str = ""
    sensitive: bool = False
    draft: bool = True  # default to draft so the user curates what's public
    # Mark bundles that should never auto-publish regardless of signals.
    # Used for e.g. LinkedIn Pulse drafts that were never published on the
    # source platform, sensitive posts whose text looks innocuous to the
    # heuristics, or any bundle the user explicitly wants excluded from the
    # promote/demote loop. The flag is sticky across importer re-runs and
    # does not participate in the idempotency hash.
    never_auto_publish: bool = False
    media: list[MediaItem] = field(default_factory=list)
    extra: dict = field(default_factory=dict)  # platform-specific extras

    def derived_title(self) -> str:
        if self.title:
            return self.title
        text = re.sub(r"\s+", " ", self.body).strip()
        if not text:
            return f"{self.platform.title()} post {self.post_id}"
        if len(text) <= 70:
            return text
        return text[:67].rstrip() + "..."


@dataclass
class ImportStats:
    added: int = 0
    updated: int = 0
    skipped: int = 0
    media_copied: int = 0
    auto_published: int = 0
    auto_drafted: int = 0

    def summary(self) -> str:
        parts = [
            f"added={self.added}",
            f"updated={self.updated}",
            f"skipped={self.skipped}",
            f"media={self.media_copied}",
        ]
        if self.auto_published or self.auto_drafted:
            parts.append(
                f"auto_publish={self.auto_published}/"
                f"{self.auto_published + self.auto_drafted}"
            )
        return " ".join(parts)


@dataclass
class AutoPublishPolicy:
    """Thresholds and allowlists for the archive auto-publish policy.

    Used by :func:`evaluate_auto_publish` to decide whether a freshly-imported
    record is "impactful original content" that can ship as ``draft: false``
    without manual review. Defaults mirror the policy documented in
    ``AGENTS.md``; override via ``takeouts/auto-publish.yml``.
    """

    min_longform_chars: int = 280
    min_caption_chars: int = 40
    min_quote_reshare_chars: int = 140
    # Facebook posts whose title matches a system-generated pattern
    # (e.g. "added a new photo", "shared a memory") are hard-excluded from
    # auto-publish when the body, after stripping FB boilerplate lines
    # (tagged people, location metadata, memory headers), has fewer than
    # this many remaining characters. Set high enough to catch typical
    # FB auto-posts without genuine user captions.
    min_fb_auto_remainder_chars: int = 20
    own_domains: tuple[str, ...] = DEFAULT_OWN_DOMAINS
    own_github_orgs: tuple[str, ...] = DEFAULT_OWN_GITHUB_ORGS


def load_auto_publish_policy() -> AutoPublishPolicy:
    """Read ``takeouts/auto-publish.yml`` if present, else return defaults.

    Unknown keys are ignored so the config file stays forward-compatible.
    Malformed YAML falls back to defaults with a warning printed to stderr.
    """
    path = TAKEOUTS_ROOT / AUTO_PUBLISH_CONFIG_FILENAME
    defaults = AutoPublishPolicy()
    if not path.exists():
        return defaults
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        print(f"  ! ignoring malformed {AUTO_PUBLISH_CONFIG_FILENAME}: {exc}")
        return defaults
    if not isinstance(data, dict):
        print(
            f"  ! {AUTO_PUBLISH_CONFIG_FILENAME} should be a YAML mapping, got "
            f"{type(data).__name__}; using defaults"
        )
        return defaults

    def _int(key: str, fallback: int) -> int:
        value = data.get(key, fallback)
        try:
            return int(value)
        except (TypeError, ValueError):
            print(
                f"  ! {AUTO_PUBLISH_CONFIG_FILENAME}: {key!r} must be an int, "
                f"got {value!r}; using default {fallback}"
            )
            return fallback

    def _str_tuple(key: str, fallback: tuple[str, ...]) -> tuple[str, ...]:
        value = data.get(key, None)
        if value is None:
            return fallback
        if not isinstance(value, list):
            print(
                f"  ! {AUTO_PUBLISH_CONFIG_FILENAME}: {key!r} must be a list; "
                f"using default"
            )
            return fallback
        return tuple(str(x).strip() for x in value if str(x).strip())

    return AutoPublishPolicy(
        min_longform_chars=_int("min_longform_chars", defaults.min_longform_chars),
        min_caption_chars=_int("min_caption_chars", defaults.min_caption_chars),
        min_quote_reshare_chars=_int(
            "min_quote_reshare_chars", defaults.min_quote_reshare_chars
        ),
        min_fb_auto_remainder_chars=_int(
            "min_fb_auto_remainder_chars", defaults.min_fb_auto_remainder_chars
        ),
        own_domains=_str_tuple("own_domains", defaults.own_domains),
        own_github_orgs=_str_tuple("own_github_orgs", defaults.own_github_orgs),
    )


_URL_RE = re.compile(r"https?://\S+")


def _visible_text(body: str) -> str:
    """Return ``body`` with URLs and collapsed whitespace removed.

    Used by the auto-publish policy to measure "real" caption/commentary
    length — a body that is just a bare link should not count as long-form.
    """
    stripped = _URL_RE.sub(" ", body or "")
    return re.sub(r"\s+", " ", stripped).strip()


# ----------------------------------------------------------------------------
# Facebook auto-generated post detection
# ----------------------------------------------------------------------------
#
# Facebook stamps system-generated titles on posts that don't have a
# user-written story — e.g. "added a new photo", "shared a memory", "followed
# a person on SoundCloud". The body on such posts is typically FB boilerplate
# too: a "You tagged X, Y and Z" line, location metadata ("Place:" header,
# latitude/longitude tuple, "Address:" line), or the memory "N years ago /
# <original title> / <date> / Updated <date>" block. These posts are rarely
# impactful content worth auto-publishing; the helpers below let
# ``evaluate_auto_publish`` hard-exclude them when the body has no meaningful
# remainder after the boilerplate is stripped.

_FB_AUTO_TITLE_RE = re.compile(
    r"(?:"
    r"added (?:a |an |\d+ )?new (?:photo|photos|video|videos|cover photo)"
    r"|added a new photo to [^.]+?timeline"
    r"|shared a memory"
    r"|followed a person on \w+"
    r"|added [^.]*? to books (?:he|she|they)[^.]*?read"
    r"|recommends [^.]+"
    r"|doesn'?t recommend [^.]+"
    r"|likes a link"
    r")",
    re.IGNORECASE,
)

_FB_BOILERPLATE_LINE_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"^you tagged\s", re.IGNORECASE),
    re.compile(r"^you were tagged in\s", re.IGNORECASE),
    re.compile(r"^place:\s*$", re.IGNORECASE),
    re.compile(r"^location:\s*$", re.IGNORECASE),
    re.compile(r"^address:\s", re.IGNORECASE),
    re.compile(r"^\(-?\d+(?:\.\d+)?,\s*-?\d+(?:\.\d+)?\)$"),
    re.compile(r"^\d+\s+years?\s+ago$", re.IGNORECASE),
    re.compile(
        r"^(?:updated\s+)?\d{1,2}\s+\w+\s+\d{4}(?:,?\s*\d{1,2}:\d{2}(?:\s*[AP]M)?)?$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^anant shrivastava\s+(?:added|shared|updated|wrote|posted|followed|"
        r"recommends|likes|created|was tagged)",
        re.IGNORECASE,
    ),
)

_FB_PLACE_HEADER_RE = re.compile(r"^(?:place|location):\s*$", re.IGNORECASE)


def _strip_fb_boilerplate_body(body: str) -> str:
    """Remove FB auto-generated metadata lines from ``body``.

    The remaining text approximates what the user actually wrote. Lines
    matching any of :data:`_FB_BOILERPLATE_LINE_RES` are dropped; a
    ``Place:`` / ``Location:`` header line also consumes the next non-blank
    line (the place-name value). Used by :func:`_is_fb_auto_post` to decide
    whether a FB post is pure system-generated content.
    """
    if not body:
        return ""
    kept: list[str] = []
    skip_place_value = False
    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        if skip_place_value:
            skip_place_value = False
            continue
        if _FB_PLACE_HEADER_RE.match(s):
            skip_place_value = True
            continue
        if any(rx.match(s) for rx in _FB_BOILERPLATE_LINE_RES):
            continue
        kept.append(s)
    return "\n".join(kept).strip()


def _is_fb_auto_post(
    title: str, body: str, *, min_remainder_chars: int
) -> tuple[bool, str]:
    """Return ``(is_auto, reason)`` for a possibly auto-generated FB post.

    A post qualifies when its ``title`` matches an FB system-generated
    pattern (:data:`_FB_AUTO_TITLE_RE`) AND the body, after stripping FB
    boilerplate lines, has fewer than ``min_remainder_chars`` visible
    characters. Those posts are typically photo uploads with no real
    caption — just "You tagged X, Y" and optional location metadata.
    """
    if not title:
        return False, ""
    if not _FB_AUTO_TITLE_RE.search(title):
        return False, ""
    remainder = _strip_fb_boilerplate_body(body or "")
    remainder_visible = _visible_text(remainder)
    if len(remainder_visible) >= min_remainder_chars:
        return False, ""
    return True, (
        f"fb auto-post ({len(remainder_visible)}<{min_remainder_chars} "
        "chars after boilerplate)"
    )


def evaluate_auto_publish(
    record: ArchiveRecord, policy: AutoPublishPolicy
) -> tuple[bool, str]:
    """Return ``(publish, reason)`` for an auto-publish decision.

    Hard exclusions (always stay draft):
      * sensitive posts
      * Twitter replies (``reply_to``) and plain retweets (``retweet_of``)
      * LinkedIn plain reposts (``extra.kind == "repost"``)
      * Low-effort quote-reshares (``extra.reshare_of_url`` set and commentary
        shorter than ``policy.min_quote_reshare_chars``)
      * Completely empty posts with no media (and not a Pulse article)
      * Facebook auto-generated posts — title matches a system-generated
        pattern (e.g. "added a new photo", "shared a memory") and the body
        has no meaningful remainder after FB boilerplate lines are stripped
        (see :func:`_is_fb_auto_post`)

    Publish signals (any one is enough):
      1. LinkedIn Pulse article (``extra.kind == "article"``)
      2. Long-form body (>= ``policy.min_longform_chars`` visible chars)
      3. Media present with a meaningful caption
         (>= ``policy.min_caption_chars`` visible chars)
      4. Body mentions one of the owned domains or GitHub orgs
    """
    extra = record.extra or {}

    if record.never_auto_publish:
        return False, "never_auto_publish set"
    if extra.get("kind") == "article_draft":
        return False, "unpublished pulse draft"
    if record.sensitive:
        return False, "sensitive"
    if record.reply_to:
        return False, "reply"
    if record.retweet_of:
        return False, "retweet"
    if extra.get("kind") == "repost":
        return False, "plain repost"

    if record.platform == "facebook":
        is_auto, reason = _is_fb_auto_post(
            record.title,
            record.body,
            min_remainder_chars=policy.min_fb_auto_remainder_chars,
        )
        if is_auto:
            return False, reason

    visible = _visible_text(record.body)
    visible_len = len(visible)

    reshare_of = extra.get("reshare_of_url")
    if reshare_of and visible_len < policy.min_quote_reshare_chars:
        return (
            False,
            f"low-effort quote-reshare ({visible_len}<"
            f"{policy.min_quote_reshare_chars} chars)",
        )

    is_article = extra.get("kind") == "article"
    if not is_article and visible_len == 0 and not record.media:
        return False, "empty body, no media"

    if is_article:
        return True, "pulse article"
    if visible_len >= policy.min_longform_chars:
        return True, f"long-form ({visible_len} chars)"
    if record.media and visible_len >= policy.min_caption_chars:
        return True, f"media + caption ({visible_len} chars)"

    body_lower = (record.body or "").lower()
    for domain in policy.own_domains:
        needle = domain.strip().lower()
        if needle and needle in body_lower:
            return True, f"links to {domain}"
    for org in policy.own_github_orgs:
        needle = f"github.com/{org.strip().lower()}"
        if needle in body_lower:
            return True, f"links to github.com/{org}"

    return False, "no publish signals"


def slugify(text: str, fallback: str = "post") -> str:
    """Return a Hugo/filesystem-safe slug for use in paths or filenames."""
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9\s_-]+", "", text)
    text = re.sub(r"[\s_-]+", "-", text).strip("-")
    return text or fallback


def content_hash(record: ArchiveRecord) -> str:
    """Stable hash of the record's logical content, used for idempotent rewrite."""
    h = hashlib.sha256()
    payload = {
        "platform": record.platform,
        "post_id": record.post_id,
        "url": record.url,
        "original_url": record.original_url,
        "date": record.date.isoformat(),
        "body": record.body,
        "platform_user": record.platform_user,
        "reply_to": record.reply_to,
        "retweet_of": record.retweet_of,
        "sensitive": record.sensitive,
        "media": [
            {
                "type": m.kind,
                "src": str(m.src_path),
                "poster": str(m.poster_src) if m.poster_src else "",
                "alt": m.alt,
            }
            for m in record.media
        ],
        "extra": record.extra,
    }
    h.update(json.dumps(payload, sort_keys=True).encode("utf-8"))
    return h.hexdigest()


def bundle_dir(record: ArchiveRecord) -> Path:
    """Return the Hugo content bundle directory for this record."""
    return CONTENT_ROOT / record.platform / record.post_id


def _load_manifest(bundle: Path) -> dict | None:
    mf = bundle / MANIFEST_NAME
    if not mf.exists():
        return None
    try:
        return json.loads(mf.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _write_manifest(bundle: Path, data: dict) -> None:
    (bundle / MANIFEST_NAME).write_text(
        json.dumps(data, indent=2, sort_keys=True), encoding="utf-8"
    )


def _frontmatter_yaml(
    record: ArchiveRecord,
    media_refs: list[dict],
    *,
    draft: bool,
    never_auto_publish: bool,
    existing_reason: str | None = None,
) -> str:
    fm: dict = {
        "title": record.derived_title(),
        "date": record.date.astimezone(timezone.utc).isoformat(),
        "draft": draft,
        "type": "archive",
        "platform": record.platform,
        "url": record.url,
        "original_url": record.original_url,
        "platform_user": record.platform_user,
        "platform_id": record.post_id,
        "archived_at": datetime.now(timezone.utc).isoformat(),
        "sensitive": record.sensitive,
    }
    if never_auto_publish:
        fm["never_auto_publish"] = True
        if existing_reason:
            fm["reason"] = existing_reason
    if record.reply_to:
        fm["reply_to"] = record.reply_to
    if record.retweet_of:
        fm["retweet_of"] = record.retweet_of
    if media_refs:
        fm["media"] = media_refs
    if record.extra:
        fm["extra"] = record.extra
    yml = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=10_000)
    return yml


def _read_existing_frontmatter(index_md: Path) -> dict | None:
    """Return parsed frontmatter of an existing bundle, or ``None``.

    Used by :func:`write_bundle` to preserve manually-curated values
    (``draft``, ``never_auto_publish``, ``reason``) across importer re-runs.
    """
    if not index_md.exists():
        return None
    try:
        text = index_md.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    try:
        fm = yaml.safe_load(text[3:end]) or {}
    except yaml.YAMLError:
        return None
    return fm if isinstance(fm, dict) else None


def _read_existing_draft(index_md: Path) -> bool | None:
    """Return the current ``draft`` value of an existing bundle, or None."""
    fm = _read_existing_frontmatter(index_md)
    if fm is None:
        return None
    value = fm.get("draft")
    return value if isinstance(value, bool) else None


def write_bundle(
    record: ArchiveRecord,
    *,
    dry_run: bool = False,
    force: bool = False,
) -> tuple[str, int]:
    """Write a page bundle for the given record.

    Returns a tuple of (state, media_count) where state is one of
    ``"added"``, ``"updated"``, or ``"skipped"``.
    """
    bundle = bundle_dir(record)
    index_md = bundle / "index.md"
    new_hash = content_hash(record)
    manifest = _load_manifest(bundle)

    # Preserve manually-curated values on existing bundles; the record's
    # defaults only apply to brand-new imports. ``draft``, ``never_auto_publish``
    # and the companion freeform ``reason`` are all sticky across re-runs.
    existing_fm = _read_existing_frontmatter(index_md) or {}
    existing_draft = existing_fm.get("draft")
    effective_draft = (
        existing_draft if isinstance(existing_draft, bool) else record.draft
    )
    existing_never = existing_fm.get("never_auto_publish")
    effective_never = (
        existing_never if isinstance(existing_never, bool) else record.never_auto_publish
    )
    existing_reason = existing_fm.get("reason")
    effective_reason = (
        str(existing_reason) if isinstance(existing_reason, str) and existing_reason.strip() else None
    )

    if manifest and manifest.get("content_hash") == new_hash and not force:
        return "skipped", 0

    state = "updated" if manifest else "added"

    if dry_run:
        return state, len(record.media)

    bundle.mkdir(parents=True, exist_ok=True)

    # Remove stale media from a previous import
    if manifest:
        for old in manifest.get("media_files", []):
            old_path = bundle / old
            if old_path.exists():
                try:
                    old_path.unlink()
                except OSError:
                    pass

    media_refs: list[dict] = []
    media_files: list[str] = []
    for idx, media in enumerate(record.media):
        target_name = media.target_basename(idx)
        target_path = bundle / target_name
        shutil.copy2(media.src_path, target_path)
        media_files.append(target_name)
        ref: dict = {"type": media.kind, "file": target_name}
        if media.alt:
            ref["alt"] = media.alt
        poster_name = media.poster_basename(idx)
        if poster_name and media.poster_src and media.poster_src.exists():
            poster_path = bundle / poster_name
            shutil.copy2(media.poster_src, poster_path)
            media_files.append(poster_name)
            ref["poster"] = poster_name
        media_refs.append(ref)

    fm_yaml = _frontmatter_yaml(
        record,
        media_refs,
        draft=effective_draft,
        never_auto_publish=effective_never,
        existing_reason=effective_reason,
    )
    body = record.body.rstrip() + "\n" if record.body.strip() else ""
    index_md_text = "---\n" + fm_yaml + "---\n\n" + body
    index_md.write_text(index_md_text, encoding="utf-8")

    _write_manifest(
        bundle,
        {
            "content_hash": new_hash,
            "platform": record.platform,
            "post_id": record.post_id,
            "media_files": media_files,
            "written_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    return state, len(record.media)


def iter_bundles(platform: str | None = None) -> Iterable[Path]:
    """Yield existing archive bundles, optionally filtered by platform."""
    if platform:
        root = CONTENT_ROOT / platform
        if not root.exists():
            return
        for item in sorted(root.iterdir()):
            if item.is_dir() and (item / "index.md").exists():
                yield item
    else:
        for p in PLATFORMS:
            yield from iter_bundles(p)


def parse_utc(iso_or_ts: str | int | float) -> datetime:
    """Parse many date formats into a timezone-aware UTC datetime."""
    if isinstance(iso_or_ts, (int, float)):
        return datetime.fromtimestamp(float(iso_or_ts), tz=timezone.utc)
    value = str(iso_or_ts).strip()
    # Twitter's "Tue Mar 05 12:34:56 +0000 2024"
    for fmt in (
        "%a %b %d %H:%M:%S %z %Y",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S %z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(value, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    # Fall back to fromisoformat which handles most remaining cases
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError as exc:
        raise ValueError(f"Unrecognized date format: {iso_or_ts!r}") from exc


def guess_media_kind(path: Path) -> str:
    """Return ``"image"``, ``"video"`` or ``"gif"`` based on file extension."""
    ext = path.suffix.lower()
    if ext in {".mp4", ".mov", ".m4v", ".webm"}:
        return "video"
    if ext == ".gif":
        return "gif"
    return "image"


# ----------------------------------------------------------------------------
# Inline image localization
# ----------------------------------------------------------------------------
#
# Archive article bodies (notably LinkedIn Pulse exports) embed inline images
# via remote URLs pointing at the original platform CDN — e.g. media.licdn.com
# URLs with signed, expiring tokens. Those links rot within months. The
# helpers below download every remote markdown image once, store it under
# ``<site>/static/images/archive/<platform>/<slug>/inline-N.<ext>``, and
# rewrite the markdown body to use absolute ``/images/archive/...`` paths
# that Hugo serves directly from ``static/``. Default Hugo markdown rendering
# handles these with no render hooks or shortcodes.


_MARKDOWN_IMAGE_RE = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\((?P<url>\S+?)(?P<title>\s+\"[^\"]*\")?\)",
    re.DOTALL,
)

_CONTENT_TYPE_TO_EXT: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/pjpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    "image/svg+xml": "svg",
    "image/bmp": "bmp",
    "image/tiff": "tiff",
    "image/x-icon": "ico",
    "image/vnd.microsoft.icon": "ico",
}


def _extension_from_content_type(content_type: str | None) -> str | None:
    if not content_type:
        return None
    base = content_type.split(";", 1)[0].strip().lower()
    return _CONTENT_TYPE_TO_EXT.get(base)


def _extension_from_magic(data: bytes) -> str | None:
    if not data:
        return None
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[:2] == b"BM":
        return "bmp"
    if data[:4] in (b"II*\x00", b"MM\x00*"):
        return "tiff"
    head = data[:256].lstrip().lower()
    if head.startswith(b"<?xml") or head.startswith(b"<svg"):
        return "svg"
    return None


def _find_existing_inline_image(target_dir: Path, n: int) -> Path | None:
    """Return an existing ``inline-<n>.<ext>`` in ``target_dir`` if present."""
    if not target_dir.exists():
        return None
    prefix = f"inline-{n}."
    for entry in target_dir.iterdir():
        if entry.is_file() and entry.name.startswith(prefix):
            return entry
    return None


def _download_inline_image(
    url: str, target_dir: Path, n: int, *, timeout: float = 30.0
) -> tuple[Path | None, str | None]:
    """Download ``url`` into ``target_dir`` as ``inline-<n>.<ext>``.

    Returns ``(path, None)`` on success or ``(None, reason)`` on failure.
    The downloaded file is written atomically: body buffered in memory,
    extension determined from the response Content-Type (falling back to
    magic bytes, then ``jpg``), then written in a single ``Path.write_bytes``.
    """
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; anantshri-archive-importer/1.0; "
            "+https://anantshri.info/)"
        ),
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            if status >= 400:
                return None, f"HTTP {status}"
            content_type = resp.headers.get("Content-Type") if resp.headers else None
            data = resp.read()
    except HTTPError as exc:
        return None, f"HTTP {exc.code}"
    except URLError as exc:
        reason = getattr(exc, "reason", exc)
        return None, f"URL error: {reason}"
    except (TimeoutError, OSError) as exc:
        return None, f"IO error: {exc}"

    if not data:
        return None, "empty response"

    ext = (
        _extension_from_content_type(content_type)
        or _extension_from_magic(data)
        or "jpg"
    )

    # Defence against servers that return HTML (e.g. "Sign in") for dead signed
    # URLs — the magic-byte check would have caught images, so if we got here
    # with HTML content type, bail out.
    if content_type:
        base_ct = content_type.split(";", 1)[0].strip().lower()
        if base_ct.startswith("text/") or base_ct in {
            "application/json",
            "application/xhtml+xml",
        }:
            if _extension_from_magic(data) is None:
                return None, f"non-image content-type: {base_ct}"

    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"inline-{n}.{ext}"
    try:
        target.write_bytes(data)
    except OSError as exc:
        return None, f"write error: {exc}"
    return target, None


def localize_inline_images(
    body_md: str,
    *,
    platform: str,
    slug: str,
    site_root: Path | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> tuple[str, dict]:
    """Download remote markdown inline images and rewrite to local URLs.

    Scans ``body_md`` for every ``![alt](url)`` (optionally with a Markdown
    link title). Every ``url`` matching ``http(s)://...`` is treated as a
    remote image and downloaded to::

        <site_root>/static/images/archive/<platform>/<slug>/inline-<N>.<ext>

    and the match is rewritten to reference ``/images/archive/<platform>/<slug>/
    inline-<N>.<ext>`` (absolute path served by Hugo from ``static/``).

    * Local URLs (paths starting with ``/``, relative paths, ``data:`` URIs,
      etc.) are left untouched.
    * Duplicate remote URLs in the same document reuse the same local file
      and the same sequence number.
    * Idempotent: existing ``inline-<N>.<ext>`` files are reused unless
      ``force=True``.
    * On fetch failure the original URL is kept and the error recorded in
      ``stats["failed"]`` so callers can print a warning.

    Returns ``(new_body_md, stats)`` where ``stats`` is::

        {
          "downloaded": int,    # newly fetched over the network
          "cached": int,        # reused existing local file
          "failed": [(url, reason), ...],
          "rewritten": int,     # total markdown image substitutions applied
          "skipped": int,       # images left alone (already local / data: uri)
        }

    ``dry_run=True`` still rewrites the returned body (so the caller can
    diff / preview) but skips all disk writes.
    """
    stats: dict = {
        "downloaded": 0,
        "cached": 0,
        "failed": [],
        "rewritten": 0,
        "skipped": 0,
    }

    if not body_md or "![" not in body_md:
        return body_md, stats

    root = site_root or SITE_ROOT
    target_dir = root / "static" / "images" / "archive" / platform / slug
    url_prefix = f"/images/archive/{platform}/{slug}/"

    # Map unique remote URL -> (sequence number, local filename). Sequence
    # numbers are assigned in order of first appearance so duplicate URLs
    # share one file.
    url_to_local: dict[str, str] = {}
    next_n = 1

    def _resolve(url: str) -> str | None:
        nonlocal next_n
        if url in url_to_local:
            stats["cached"] += 1
            return url_to_local[url]

        n = next_n
        next_n += 1

        existing = _find_existing_inline_image(target_dir, n)
        if existing is not None and not force:
            name = existing.name
            url_to_local[url] = name
            stats["cached"] += 1
            return name

        if dry_run:
            # Pretend we got an extension — use .jpg as a stand-in for preview.
            # No file is written.
            name = f"inline-{n}.jpg"
            url_to_local[url] = name
            stats["downloaded"] += 1
            return name

        path, err = _download_inline_image(url, target_dir, n)
        if path is None or err is not None:
            stats["failed"].append((url, err or "unknown error"))
            # Roll back the sequence number so the next successful download
            # doesn't leave a gap — callers treat ``inline-<N>`` numbering as
            # arbitrary but contiguous sequences are nicer to read on disk.
            next_n -= 1
            return None

        url_to_local[url] = path.name
        stats["downloaded"] += 1
        return path.name

    def _sub(match: re.Match[str]) -> str:
        url = match.group("url")
        alt = match.group("alt") or ""
        title = match.group("title") or ""

        low = url.lower()
        if not (low.startswith("http://") or low.startswith("https://")):
            stats["skipped"] += 1
            return match.group(0)

        name = _resolve(url)
        if name is None:
            # Failed download — preserve original markdown verbatim.
            return match.group(0)

        new_url = url_prefix + name
        stats["rewritten"] += 1
        return f"![{alt}]({new_url}{title})"

    new_body = _MARKDOWN_IMAGE_RE.sub(_sub, body_md)
    return new_body, stats


def load_exclude_set() -> set[str]:
    """Read ``takeouts/exclude.yml`` if present and return a set of post ids to skip."""
    exclude_path = TAKEOUTS_ROOT / "exclude.yml"
    if not exclude_path.exists():
        return set()
    try:
        data = yaml.safe_load(exclude_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return set()
    ids: set[str] = set()
    if isinstance(data, list):
        ids.update(str(x) for x in data)
    elif isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                ids.update(str(x) for x in v)
            else:
                ids.add(str(v))
    return ids
