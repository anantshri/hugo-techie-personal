#!/usr/bin/env python3
"""Backfill archive body rewrites across existing bundles.

Companion to ``import_*.py``: their body pipeline runs three transforms
on every newly-imported post — strip tracking-param query strings,
embed standalone X/Twitter/LinkedIn post URLs via the ``oembed``
shortcode, and wrap any remaining bare URLs as ``<URL>`` markdown
autolinks. For LinkedIn shares, mentions are recovered by scraping the
public embed endpoint and substituted in as ``[Name](profile_url)``
links.

This script applies the same transforms retroactively to bundles that
were imported before the feature existed. Run it once after the
upgrade; subsequent importer runs are no-ops because the rewrites are
idempotent.

Behaviour
---------

* Walks every ``content/archive/<platform>/<slug>/index.md`` (optionally
  filtered with ``--platform``).
* Splits frontmatter from body and rewrites only the body. Frontmatter
  is preserved byte-for-byte.
* For LinkedIn share / Pulse bundles: looks up mentions in
  ``takeouts/.linkedin-mentions-cache.json`` first, then the manual
  ``takeouts/linkedin-mention-map.json`` override map, then (unless
  ``--no-scrape-mentions``) falls back to a fresh embed scrape and
  caches the result.
* For all platforms: runs the same body rewrite as the importer
  (mention substitution → standalone-URL embed → bare-URL autolink +
  tracking-param strip). Idempotent — re-running on already-rewritten
  bundles changes nothing.
* When the body changes and the bundle has no media page resources,
  the ``.manifest.json`` ``content_hash`` is refreshed so the next
  importer run reports ``skipped``. Bundles with media keep their
  manifest unchanged (the hash depends on takeout-local ``src_path``
  values that aren't recoverable from the bundle alone).

Usage
-----

    # Preview what would change across all platforms
    uv run --with pyyaml python3 \\
        themes/hugo-techie-personal/scripts/rewrite_archive_bodies.py \\
        --dry-run

    # Apply for real, scoped to LinkedIn
    uv run --with pyyaml python3 \\
        themes/hugo-techie-personal/scripts/rewrite_archive_bodies.py \\
        --platform linkedin

Flags
-----

``--dry-run``                Report what would change; do not write
                             files or hit the network for uncached
                             mentions.
``--platform P``             Restrict to one platform (twitter,
                             linkedin, instagram, facebook).
``--limit N``                Process at most N bundles.
``--no-scrape-mentions``     LinkedIn-only: skip the public-embed
                             scrape used to recover @-mention links
                             from share posts. Cached mentions and the
                             manual map are still applied.
``--refresh-mention-cache``  LinkedIn-only: re-fetch every share's
                             @-mentions, ignoring the on-disk cache.
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
    parse_utc,
    rewrite_archive_body,
)
from import_linkedin import (  # noqa: E402
    _enrich_mentions,
    _load_mention_map,
)


def _split_frontmatter(text: str) -> tuple[str, str] | None:
    """Return ``(frontmatter_text, body_text)`` or ``None`` when no
    frontmatter is present.

    Mirrors the implementation in :mod:`resolve_archive_short_urls` so
    the two backfill scripts stay byte-compatible with each other.
    """
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    fm_text = text[3:end]
    if fm_text.startswith("\n"):
        fm_text = fm_text[1:]
    rest_start = end + len("\n---")
    if rest_start < len(text) and text[rest_start] == "\n":
        rest_start += 1
    body_text = text[rest_start:]
    return fm_text, body_text


def _leading_blank_lines(text: str) -> tuple[str, str]:
    i = 0
    while i < len(text) and text[i] == "\n":
        i += 1
    return text[:i], text[i:]


def _record_from_frontmatter(
    fm: dict, body: str, *, slug: str
) -> ArchiveRecord | None:
    """Reconstruct an :class:`ArchiveRecord` from on-disk frontmatter.

    Returns ``None`` when the frontmatter doesn't carry the keys we
    need to compute a content hash, or when the bundle has media (whose
    page resources aren't faithfully reflected in frontmatter alone).
    Bundles with media are still rewritten on disk; the manifest is
    just left alone.
    """
    required = ("platform", "platform_id", "url", "original_url", "date")
    if not all(k in fm for k in required):
        return None
    if fm.get("media"):
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


def _build_linkedin_mention_lookup(
    bundles: list[Path],
    *,
    scrape: bool,
    refresh_cache: bool,
    dry_run: bool,
) -> dict[str, list[tuple[str, str]]]:
    """Return ``{post_id: [(name, url), ...]}`` for every LinkedIn bundle.

    Reuses :func:`import_linkedin._enrich_mentions` so cache schema and
    scraping behaviour match the importer exactly. We synthesise
    minimal :class:`ArchiveRecord` instances purely for the enrichment
    pass, then collect their populated ``extra.mentions``.
    """
    manual_map = _load_mention_map()
    records: list[ArchiveRecord] = []
    bundle_for_post: dict[str, Path] = {}
    for bundle in bundles:
        index_md = bundle / "index.md"
        try:
            raw = index_md.read_text(encoding="utf-8")
        except OSError:
            continue
        split = _split_frontmatter(raw)
        if split is None:
            continue
        fm_text, _body = split
        try:
            fm = yaml.safe_load(fm_text) or {}
        except yaml.YAMLError:
            continue
        if not isinstance(fm, dict):
            continue
        if fm.get("platform") != "linkedin":
            continue
        platform_id = str(fm.get("platform_id") or bundle.name)
        if platform_id.startswith("repost-"):
            continue
        extra = dict(fm.get("extra") or {})
        urn_type = extra.get("urn_type")
        urn_id = extra.get("urn_id")
        if not urn_type or not urn_id:
            continue
        try:
            date = parse_utc(fm.get("date") or "")
        except (ValueError, TypeError):
            continue
        rec = ArchiveRecord(
            platform="linkedin",
            post_id=platform_id,
            url=str(fm.get("url") or ""),
            original_url=str(fm.get("original_url") or ""),
            date=date,
            body="",
            platform_user=str(fm.get("platform_user") or ""),
            media=[],
            extra=extra,
        )
        records.append(rec)
        bundle_for_post[platform_id] = bundle

    if not records and not manual_map:
        return {}

    _enrich_mentions(
        records,
        manual_map=manual_map,
        scrape=scrape,
        refresh_cache=refresh_cache,
        dry_run=dry_run,
    )

    out: dict[str, list[tuple[str, str]]] = {}
    for rec in records:
        mentions = rec.extra.get("mentions") or []
        pairs = [
            (str(m.get("name") or ""), str(m.get("url") or ""))
            for m in mentions
            if isinstance(m, dict)
        ]
        pairs = [(n, u) for n, u in pairs if n and u]
        if pairs:
            out[rec.post_id] = pairs
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
        help=(
            "Report what would change; do not write files or contact "
            "the network for uncached mentions (cached entries are "
            "still applied)."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process at most N bundles (0 = no limit).",
    )
    parser.add_argument(
        "--no-scrape-mentions",
        action="store_true",
        default=False,
        help=(
            "LinkedIn-only: skip the public-embed scrape used to "
            "recover @-mention profile links. Cached mentions and the "
            "manual map at takeouts/linkedin-mention-map.json are "
            "still applied."
        ),
    )
    parser.add_argument(
        "--refresh-mention-cache",
        action="store_true",
        default=False,
        help=(
            "LinkedIn-only: re-fetch every share's @-mentions, "
            "ignoring the on-disk cache at "
            "takeouts/.linkedin-mentions-cache.json."
        ),
    )
    args = parser.parse_args()

    bundles = _iter_bundles(args.platform)
    if args.limit > 0:
        bundles = bundles[: args.limit]

    # LinkedIn mention lookup is built up-front so per-bundle rewrites
    # don't pay a repeated map-load cost. The lookup is scoped to the
    # bundles we'll actually process (post-``--limit``).
    linkedin_mentions: dict[str, list[tuple[str, str]]] = {}
    process_linkedin = (
        args.platform is None or args.platform == "linkedin"
    )
    if process_linkedin:
        linkedin_bundles = [b for b in bundles if b.parent.name == "linkedin"]
        if linkedin_bundles:
            linkedin_mentions = _build_linkedin_mention_lookup(
                linkedin_bundles,
                scrape=not args.no_scrape_mentions,
                refresh_cache=args.refresh_mention_cache,
                dry_run=args.dry_run,
            )

    bundles_scanned = 0
    bundles_changed = 0
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
        platform_id = str(fm.get("platform_id") or bundle.name)
        mentions: list[tuple[str, str]] = []
        if platform == "linkedin":
            mentions = list(linkedin_mentions.get(platform_id, ()))

        new_body = rewrite_archive_body(body, mentions=mentions)
        if new_body == body:
            continue

        bundles_changed += 1
        rel = bundle.relative_to(CONTENT_ROOT)
        flag = ""
        if mentions:
            flag = f" mentions={len(mentions)}"
        print(f"{rel}: rewrote body{flag}")

        if args.dry_run:
            continue

        # Preserve the frontmatter block byte-for-byte, including
        # whether or not the source ended with a newline before the
        # closing ``---``.
        fm_sep = "" if fm_text.endswith("\n") else "\n"
        new_text = f"---\n{fm_text}{fm_sep}---\n{leading}{new_body}"
        index_md.write_text(new_text, encoding="utf-8")

        record = _record_from_frontmatter(fm, new_body, slug=bundle.name)
        manifest_path = bundle / MANIFEST_NAME
        if record is not None and manifest_path.exists():
            try:
                manifest = json.loads(
                    manifest_path.read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError):
                manifest = None
            if isinstance(manifest, dict):
                new_hash = content_hash(record)
                if manifest.get("content_hash") != new_hash:
                    manifest["content_hash"] = new_hash
                    manifest["written_at"] = datetime.now(
                        timezone.utc
                    ).isoformat()
                    manifest_path.write_text(
                        json.dumps(manifest, indent=2, sort_keys=True),
                        encoding="utf-8",
                    )
                    manifests_refreshed += 1

    print()
    print(
        f"scanned={bundles_scanned} changed={bundles_changed} "
        f"manifests-refreshed={manifests_refreshed}"
    )
    if args.dry_run:
        print("(dry-run: no files written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
