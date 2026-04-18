#!/usr/bin/env python3
"""Retroactively apply the auto-publish policy to existing archive bundles.

The four social-archive importers support ``--auto-publish``, which only
affects **newly-imported** bundles (existing ones keep whatever ``draft`` value
is already in their ``index.md``). Use this script to backfill the same policy
across every bundle that was imported before ``--auto-publish`` existed, or to
re-evaluate everything after tuning ``takeouts/auto-publish.yml``.

Default behaviour is **promote-only**: bundles currently marked ``draft: true``
are flipped to ``draft: false`` when the policy says "publish"; bundles already
at ``draft: false`` (your manual curation) are never demoted. Pass ``--demote``
to also flip published bundles back to ``draft: true`` where the policy says
no-publish.

Usage
-----

    # Preview which drafts would be auto-published across the whole archive
    uv run --with pyyaml python3 \
        themes/hugo-techie-personal/scripts/apply_archive_policy.py --dry-run

    # Actually flip the eligible drafts to draft: false
    uv run --with pyyaml python3 \
        themes/hugo-techie-personal/scripts/apply_archive_policy.py

    # Only the LinkedIn section
    uv run --with pyyaml python3 \
        themes/hugo-techie-personal/scripts/apply_archive_policy.py \
        --platform linkedin

    # Promote eligible drafts AND demote ineligible published bundles
    uv run --with pyyaml python3 \
        themes/hugo-techie-personal/scripts/apply_archive_policy.py --demote

The script never touches the bundle content hash or media files; only the
``draft:`` frontmatter value is rewritten, which is deliberately excluded from
the idempotency hash so future importer runs remain no-ops.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _archive_common import (  # noqa: E402
    CONTENT_ROOT,
    PLATFORMS,
    ArchiveRecord,
    AutoPublishPolicy,
    MediaItem,
    evaluate_auto_publish,
    load_auto_publish_policy,
)


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)
# Match the draft: line anywhere in the frontmatter block, tolerating both
# bare booleans and quoted strings. We rewrite the value in place so key order
# and surrounding keys are preserved exactly.
DRAFT_LINE_RE = re.compile(
    r"^(?P<indent>[ \t]*)draft:[ \t]*(?P<value>[^\s#]+)(?P<trailing>[ \t]*(?:#.*)?)$",
    re.MULTILINE,
)


@dataclass
class BundleDecision:
    path: Path
    platform: str
    post_id: str
    current_draft: bool
    would_publish: bool
    reason: str

    @property
    def action(self) -> str:
        if self.current_draft and self.would_publish:
            return "promote"
        if not self.current_draft and not self.would_publish:
            return "demote"
        return "keep"


def _parse_frontmatter(text: str) -> tuple[dict, str, str]:
    """Return ``(frontmatter_dict, frontmatter_raw, body)``.

    Raises ``ValueError`` if the file has no frontmatter block or the YAML is
    malformed.
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError("missing or malformed frontmatter block")
    raw = m.group(1)
    body = m.group(2)
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        raise ValueError("frontmatter is not a YAML mapping")
    return data, raw, body


def _record_from_frontmatter(
    fm: dict, body: str, bundle_dir: Path
) -> ArchiveRecord | None:
    """Build a minimal :class:`ArchiveRecord` from an existing bundle.

    Only the fields ``evaluate_auto_publish`` consults are populated; other
    fields use safe defaults since this record is never written back.
    Returns ``None`` for non-archive files (anything missing ``type: archive``).
    """
    if fm.get("type") != "archive":
        return None

    platform = str(fm.get("platform", "")).strip()
    post_id = str(fm.get("platform_id") or bundle_dir.name)

    date_value = fm.get("date")
    if isinstance(date_value, datetime):
        date = date_value if date_value.tzinfo else date_value.replace(tzinfo=timezone.utc)
    else:
        date = datetime.now(timezone.utc)

    media_refs = fm.get("media") or []
    media_items: list[MediaItem] = []
    if isinstance(media_refs, list):
        for ref in media_refs:
            if not isinstance(ref, dict):
                continue
            fname = ref.get("file")
            if not fname:
                continue
            media_items.append(
                MediaItem(
                    src_path=bundle_dir / str(fname),
                    kind=str(ref.get("type") or "image"),
                    alt=str(ref.get("alt") or ""),
                )
            )

    extra = fm.get("extra")
    if not isinstance(extra, dict):
        extra = {}

    return ArchiveRecord(
        platform=platform,
        post_id=post_id,
        url=str(fm.get("url") or ""),
        original_url=str(fm.get("original_url") or ""),
        date=date,
        body=body or "",
        platform_user=str(fm.get("platform_user") or ""),
        reply_to=str(fm.get("reply_to") or ""),
        retweet_of=str(fm.get("retweet_of") or ""),
        sensitive=bool(fm.get("sensitive", False)),
        draft=bool(fm.get("draft", True)),
        never_auto_publish=bool(fm.get("never_auto_publish", False)),
        media=media_items,
        extra=extra,
    )


def _iter_bundle_files(platform_filter: str | None) -> list[Path]:
    """Return every ``index.md`` under ``content/archive/<platform>/*/``."""
    out: list[Path] = []
    platforms = (platform_filter,) if platform_filter else PLATFORMS
    for platform in platforms:
        root = CONTENT_ROOT / platform
        if not root.is_dir():
            continue
        for bundle in sorted(root.iterdir()):
            if not bundle.is_dir():
                continue
            index = bundle / "index.md"
            if index.exists():
                out.append(index)
    return out


def _rewrite_draft(text: str, new_value: bool) -> str | None:
    """Return ``text`` with the ``draft:`` frontmatter value rewritten.

    Only the first ``draft:`` line inside the opening ``---`` block is
    touched. Returns ``None`` if no such line exists (caller can decide to
    skip or error).
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    fm_start, fm_end = m.start(1), m.end(1)
    fm_raw = text[fm_start:fm_end]
    replacement = f"\\g<indent>draft: {'false' if not new_value else 'true'}\\g<trailing>"
    new_fm, n = DRAFT_LINE_RE.subn(replacement, fm_raw, count=1)
    if n == 0:
        return None
    return text[:fm_start] + new_fm + text[fm_end:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print decisions without modifying any files.",
    )
    parser.add_argument(
        "--platform",
        choices=PLATFORMS,
        help="Limit to one platform (default: all four).",
    )
    parser.add_argument(
        "--demote",
        action="store_true",
        default=False,
        help=(
            "Also flip currently-published bundles back to draft: true when "
            "the policy says no-publish. Default is promote-only, which "
            "preserves your manual draft:false curation."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Only print action lines (promote/demote), not kept-as-is bundles.",
    )
    args = parser.parse_args()

    policy: AutoPublishPolicy = load_auto_publish_policy()
    if not args.quiet:
        print(f"policy: {policy}")

    files = _iter_bundle_files(args.platform)
    if not files:
        print("no archive bundles found")
        return 0

    promoted = 0
    demoted = 0
    kept_draft = 0
    kept_published = 0
    errors = 0

    for index_path in files:
        try:
            text = index_path.read_text(encoding="utf-8")
            fm, _fm_raw, body = _parse_frontmatter(text)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            print(f"  ! {index_path.relative_to(CONTENT_ROOT)}: {exc}")
            errors += 1
            continue

        record = _record_from_frontmatter(fm, body.lstrip(), index_path.parent)
        if record is None:
            continue

        # Respect the never_auto_publish flag both ways: don't promote, and
        # don't demote either — the user's manual choice wins regardless of
        # whether --demote is set.
        if record.never_auto_publish:
            rel = index_path.relative_to(CONTENT_ROOT)
            if record.draft:
                kept_draft += 1
                if not args.quiet:
                    print(f"  [kept draft]    {rel}: never_auto_publish set")
            else:
                kept_published += 1
                if not args.quiet:
                    print(f"  [kept publish]  {rel}: never_auto_publish set")
            continue

        publish, reason = evaluate_auto_publish(record, policy)
        decision = BundleDecision(
            path=index_path,
            platform=record.platform,
            post_id=record.post_id,
            current_draft=record.draft,
            would_publish=publish,
            reason=reason,
        )

        rel = index_path.relative_to(CONTENT_ROOT)

        if decision.action == "promote":
            if args.dry_run:
                print(f"  [would promote] {rel}: {reason}")
            else:
                new_text = _rewrite_draft(text, new_value=False)
                if new_text is None:
                    print(f"  ! {rel}: no draft: line found, skipping")
                    errors += 1
                    continue
                index_path.write_text(new_text, encoding="utf-8")
                print(f"  [promoted]      {rel}: {reason}")
            promoted += 1
        elif decision.action == "demote":
            if not args.demote:
                kept_published += 1
                if not args.quiet:
                    print(f"  [kept publish]  {rel}: {reason} (use --demote to flip)")
                continue
            if args.dry_run:
                print(f"  [would demote]  {rel}: {reason}")
            else:
                new_text = _rewrite_draft(text, new_value=True)
                if new_text is None:
                    print(f"  ! {rel}: no draft: line found, skipping")
                    errors += 1
                    continue
                index_path.write_text(new_text, encoding="utf-8")
                print(f"  [demoted]       {rel}: {reason}")
            demoted += 1
        else:
            if record.draft:
                kept_draft += 1
                if not args.quiet:
                    print(f"  [kept draft]    {rel}: {reason}")
            else:
                kept_published += 1
                if not args.quiet:
                    print(f"  [kept publish]  {rel}: {reason}")

    verb = "would apply" if args.dry_run else "applied"
    print(
        f"\narchive policy {verb}: "
        f"promoted={promoted} demoted={demoted} "
        f"kept_draft={kept_draft} kept_published={kept_published} "
        f"errors={errors} total={len(files)}"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
