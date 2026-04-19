#!/usr/bin/env python3
"""Backfill ``https://lnkd.in/`` short-URL resolution across existing bundles.

The sibling ``import_*.py`` importers call ``resolve_short_urls`` (in
``_archive_common.py``) on freshly-imported post bodies so LinkedIn's
``lnkd.in`` short URLs are replaced with their real destinations at write
time. That handles *new* imports.

This script retroactively applies the same transform to pre-existing bundles
under ``content/archive/**``. Useful once after adding the feature, or any
time the upstream ``lnkd.in`` resolver was unreachable during the original
import and the short URLs got baked into the bundles.

Behaviour
---------

* Walks every ``content/archive/<platform>/<slug>/index.md`` (optionally
  filtered with ``--platform``).
* Splits frontmatter from body using the existing ``---`` delimiter. The
  frontmatter is preserved byte-for-byte; only the body is rewritten.
* Calls ``resolve_short_urls`` on the body. Unresolvable URLs are left as-is
  so the next run can retry them after a network recovers.
* Resolutions are cached in ``takeouts/lnkd-in-cache.json`` so repeat runs
  and concurrent importer invocations don't re-hit the network.
* If the body changes and the bundle has no media page resources (typical
  for LinkedIn Pulse articles and most feed shares without attachments),
  the ``.manifest.json`` ``content_hash`` is refreshed so the next importer
  run reports ``skipped`` instead of ``updated``. For bundles with media,
  the manifest is left alone — its hash depends on takeout-local src_paths
  that can't be recovered from the bundle — and the next importer re-run
  will rewrite it correctly on its own.

Flags
-----

``--dry-run``    Report what would change without writing files or hitting
                 the network (uncached URLs are left alone).
``--platform P`` Restrict to one platform (e.g. ``linkedin``).
``--limit N``    Process at most N bundles (useful for quick testing).

Usage
-----

    uv run --with pyyaml python3 \\
        themes/hugo-techie-personal/scripts/resolve_archive_short_urls.py \\
        --platform linkedin --dry-run

    uv run --with pyyaml python3 \\
        themes/hugo-techie-personal/scripts/resolve_archive_short_urls.py
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
    resolve_short_urls,
    save_short_url_cache,
)


def _split_frontmatter(text: str) -> tuple[str, str] | None:
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
            "Report what would change; do not write files or contact the "
            "network for uncached URLs (cached entries are still applied)."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process at most N bundles (0 = no limit).",
    )
    args = parser.parse_args()

    bundles = _iter_bundles(args.platform)
    if args.limit > 0:
        bundles = bundles[: args.limit]

    total_resolved = 0
    total_cached = 0
    total_rewritten = 0
    total_failed = 0
    bundles_changed = 0
    bundles_scanned = 0
    manifests_refreshed = 0

    try:
        for bundle in bundles:
            bundles_scanned += 1
            index_md = bundle / "index.md"
            try:
                raw = index_md.read_text(encoding="utf-8")
            except OSError as exc:
                print(f"! {bundle.name}: cannot read index.md ({exc})")
                continue
            if "lnkd.in" not in raw.lower():
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

            body_has = "lnkd.in" in body.lower()
            fm_has = "lnkd.in" in fm_text.lower()

            if not body_has and not fm_has:
                continue

            # Resolve body.
            if body_has:
                new_body, stats = resolve_short_urls(body, dry_run=args.dry_run)
            else:
                new_body = body
                stats = {"resolved": 0, "cached": 0, "rewritten": 0, "failed": []}

            # Resolve known short-URL-bearing frontmatter fields stashed by
            # the importer (e.g. LinkedIn ``extra.shared_url``). We build a
            # per-URL replacement map and apply it as a surgical string
            # substitution on the original ``fm_text`` so all other
            # frontmatter keys keep their original formatting byte-for-byte.
            fm_stats = {"resolved": 0, "cached": 0, "rewritten": 0, "failed": []}
            replacements: list[tuple[str, str]] = []
            extra = fm.get("extra")
            if isinstance(extra, dict):
                for key in ("shared_url", "reshare_of_url"):
                    val = extra.get(key)
                    if not isinstance(val, str) or "lnkd.in" not in val.lower():
                        continue
                    new_val, stats_one = resolve_short_urls(
                        val, dry_run=args.dry_run
                    )
                    fm_stats["resolved"] += stats_one["resolved"]
                    fm_stats["cached"] += stats_one["cached"]
                    fm_stats["rewritten"] += stats_one["rewritten"]
                    fm_stats["failed"].extend(stats_one["failed"])
                    if new_val != val:
                        replacements.append((val, new_val))
                        # Keep the parsed frontmatter dict in sync so the
                        # ArchiveRecord/content_hash reconstruction below
                        # reflects the new URL too.
                        extra[key] = new_val

            new_fm_text = fm_text
            for old_url, new_url in replacements:
                new_fm_text = new_fm_text.replace(old_url, new_url)
            fm_changed = new_fm_text != fm_text

            total_resolved += stats["resolved"] + fm_stats["resolved"]
            total_cached += stats["cached"] + fm_stats["cached"]
            total_rewritten += stats["rewritten"] + fm_stats["rewritten"]
            total_failed += len(stats["failed"]) + len(fm_stats["failed"])

            rel = bundle.relative_to(CONTENT_ROOT)
            if stats["failed"] or fm_stats["failed"]:
                print(f"{rel}:")
                for short, reason in stats["failed"]:
                    print(f"  ! failed (body): {short} ({reason})")
                for short, reason in fm_stats["failed"]:
                    print(f"  ! failed (frontmatter): {short} ({reason})")

            body_changed = new_body != body
            if not body_changed and not fm_changed:
                continue

            bundles_changed += 1
            total_rw = stats["rewritten"] + fm_stats["rewritten"]
            total_res = stats["resolved"] + fm_stats["resolved"]
            total_ca = stats["cached"] + fm_stats["cached"]
            where = []
            if body_changed:
                where.append("body")
            if fm_changed:
                where.append("frontmatter")
            print(
                f"{rel}: rewrote {total_rw} lnkd.in URL(s) in {'+'.join(where)} "
                f"(resolved={total_res}, cached={total_ca})"
            )

            if args.dry_run:
                continue

            fm_out = new_fm_text
            fm_sep = "" if fm_out.endswith("\n") else "\n"
            new_text = f"---\n{fm_out}{fm_sep}---\n{leading}{new_body}"
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
    finally:
        if not args.dry_run:
            save_short_url_cache()

    print()
    print(
        f"scanned={bundles_scanned} changed={bundles_changed} "
        f"rewritten={total_rewritten} resolved={total_resolved} "
        f"cached={total_cached} failed={total_failed} "
        f"manifests-refreshed={manifests_refreshed}"
    )
    if args.dry_run:
        print("(dry-run: no files written; uncached URLs were skipped)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
