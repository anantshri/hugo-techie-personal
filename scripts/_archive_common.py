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

    def summary(self) -> str:
        return (
            f"added={self.added} updated={self.updated} "
            f"skipped={self.skipped} media={self.media_copied}"
        )


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
    record: ArchiveRecord, media_refs: list[dict], *, draft: bool
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


def _read_existing_draft(index_md: Path) -> bool | None:
    """Return the current ``draft`` value of an existing bundle, or None.

    Preserves manual curation: if a user has flipped ``draft`` to ``false`` by
    hand, re-running the importer will not clobber that choice.
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
    value = fm.get("draft") if isinstance(fm, dict) else None
    if isinstance(value, bool):
        return value
    return None


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

    # Preserve any manually-curated draft value on existing bundles; the
    # record's default only applies to brand-new imports.
    existing_draft = _read_existing_draft(index_md)
    effective_draft = existing_draft if existing_draft is not None else record.draft

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

    fm_yaml = _frontmatter_yaml(record, media_refs, draft=effective_draft)
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
