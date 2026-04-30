#!/usr/bin/env python3
"""Import an X / Twitter takeout into ``content/archive/twitter/``.

Usage
-----

    uv run --with pyyaml python3 themes/hugo-techie-personal/scripts/import_twitter.py \
        --takeout takeouts/twitter-2026-04-10.zip \
        --user anantshri

The takeout can be supplied either as the downloaded ``.zip`` or an already
extracted directory. Tweet media are copied from ``data/tweets_media/`` into
the corresponding page bundle as resources.

The script is idempotent: re-running it only rewrites bundles whose normalized
content has changed since the last run.
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
    AutoPublishPolicy,
    ImportStats,
    MediaItem,
    evaluate_auto_publish,
    guess_media_kind,
    load_auto_publish_policy,
    load_exclude_set,
    parse_utc,
    resolve_short_urls,
    rewrite_archive_body,
    save_short_url_cache,
    write_bundle,
)

TWEETS_JS_CANDIDATES = ("data/tweet.js", "data/tweets.js")
TWEETS_MEDIA_DIR = "data/tweets_media"


def _open_takeout(path: Path) -> tuple[Path, Path | None]:
    """Return (root, tempdir). ``tempdir`` is set when a zip was extracted."""
    if path.is_dir():
        return path, None
    if path.is_file() and path.suffix.lower() == ".zip":
        tmp = Path(tempfile.mkdtemp(prefix="twitter-takeout-"))
        with zipfile.ZipFile(path) as zf:
            zf.extractall(tmp)
        return tmp, tmp
    raise SystemExit(f"Takeout path not found or unsupported: {path}")


def _locate_tweets_js(root: Path) -> Path:
    for candidate in TWEETS_JS_CANDIDATES:
        p = root / candidate
        if p.exists():
            return p
    # Some older exports nest everything under an extra folder
    for candidate in TWEETS_JS_CANDIDATES:
        for match in root.rglob(Path(candidate).name):
            if match.is_file():
                return match
    raise SystemExit(
        f"Could not find tweet.js in takeout at {root}. Looked for "
        + ", ".join(TWEETS_JS_CANDIDATES)
    )


def _parse_tweets_js(tweets_js: Path) -> list[dict]:
    text = tweets_js.read_text(encoding="utf-8")
    # Strip JS assignment prefix like: window.YTD.tweets.part0 = [ ... ];
    m = re.match(r"\s*window\.YTD\.[a-zA-Z0-9_]+\.part\d+\s*=\s*", text)
    if m:
        text = text[m.end():]
    text = text.strip().rstrip(";")
    data = json.loads(text)
    tweets: list[dict] = []
    for item in data:
        if isinstance(item, dict) and "tweet" in item:
            tweets.append(item["tweet"])
        elif isinstance(item, dict):
            tweets.append(item)
    return tweets


def _expand_body(tweet: dict) -> str:
    """Apply t.co expansions to produce readable post text."""
    text: str = tweet.get("full_text") or tweet.get("text") or ""
    entities = tweet.get("entities", {}) or {}
    replacements: list[tuple[str, str]] = []
    for url in entities.get("urls", []) or []:
        short = url.get("url")
        expanded = url.get("expanded_url") or url.get("display_url") or short
        if short and expanded and short != expanded:
            replacements.append((short, expanded))
    for media in entities.get("media", []) or []:
        short = media.get("url")
        if short:
            # Media is rendered separately; strip the inline t.co link
            replacements.append((short, ""))
    for short, expanded in replacements:
        text = text.replace(short, expanded)
    return text.strip()


def _collect_media_items(tweet: dict, media_root: Path) -> list[MediaItem]:
    """Find the media files on disk that belong to this tweet."""
    tweet_id = tweet.get("id_str") or str(tweet.get("id") or "")
    if not tweet_id or not media_root.exists():
        return []
    items: list[MediaItem] = []
    seen: set[str] = set()

    ext_entities = (tweet.get("extended_entities") or {}).get("media") or []
    entities_media = (tweet.get("entities") or {}).get("media") or []

    declared_ids: list[str] = []
    for m in list(ext_entities) + list(entities_media):
        mid = m.get("id_str") or str(m.get("id") or "")
        if mid and mid not in declared_ids:
            declared_ids.append(mid)

    candidate_files: list[Path] = []
    if declared_ids:
        for mid in declared_ids:
            matches = sorted(media_root.glob(f"{tweet_id}-{mid}.*"))
            candidate_files.extend(matches)
    else:
        candidate_files = sorted(media_root.glob(f"{tweet_id}-*.*"))

    for f in candidate_files:
        if f.name in seen:
            continue
        seen.add(f.name)
        kind = guess_media_kind(f)
        items.append(MediaItem(src_path=f, kind=kind))
    return items


def _is_reply(tweet: dict) -> str:
    reply_to = tweet.get("in_reply_to_status_id_str") or tweet.get("in_reply_to_status_id")
    return str(reply_to) if reply_to else ""


def _is_retweet(tweet: dict) -> str:
    body = tweet.get("full_text") or tweet.get("text") or ""
    if body.startswith("RT @"):
        return body[: body.index(":")] if ":" in body else "RT"
    return ""


def _build_records(
    tweets: Iterable[dict],
    *,
    user: str,
    media_root: Path,
    include_replies: bool,
    include_retweets: bool,
    exclude_ids: set[str],
    draft: bool,
    resolve_short: bool,
    dry_run: bool,
) -> Iterable[ArchiveRecord]:
    for tweet in tweets:
        tweet_id = tweet.get("id_str") or str(tweet.get("id") or "")
        if not tweet_id or tweet_id in exclude_ids:
            continue
        reply_to = _is_reply(tweet)
        retweet_of = _is_retweet(tweet)
        if reply_to and not include_replies:
            continue
        if retweet_of and not include_retweets:
            continue
        try:
            date = parse_utc(tweet.get("created_at", ""))
        except ValueError:
            continue
        body = _expand_body(tweet)
        if resolve_short and body and "lnkd.in" in body.lower():
            body, s_stats = resolve_short_urls(body, dry_run=dry_run)
            if s_stats["rewritten"] or s_stats["failed"]:
                failed_count = len(s_stats["failed"])
                print(
                    f"  {tweet_id}: lnkd.in "
                    f"resolved={s_stats['resolved']} "
                    f"cached={s_stats['cached']} "
                    f"failed={failed_count}"
                )
                for short, reason in s_stats["failed"]:
                    print(f"    ! could not resolve {short} ({reason})")
        # Embed standalone X / Twitter / LinkedIn post URLs, autolink any
        # remaining bare URLs, and strip tracking parameters. See
        # ``rewrite_archive_body`` in ``_archive_common.py`` for the
        # full transform list.
        body = rewrite_archive_body(body)
        media_items = _collect_media_items(tweet, media_root)
        original_url = f"https://x.com/{user}/status/{tweet_id}"
        url = f"/x.com/{user}/status/{tweet_id}/"
        yield ArchiveRecord(
            platform="twitter",
            post_id=tweet_id,
            url=url,
            original_url=original_url,
            date=date,
            body=body,
            platform_user=user,
            reply_to=reply_to,
            retweet_of=retweet_of,
            sensitive=bool(tweet.get("possibly_sensitive", False)),
            draft=draft,
            media=media_items,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--takeout", required=True, type=Path, help="Zip or directory")
    parser.add_argument("--user", required=True, help="Twitter/X handle (no @)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Rewrite even if unchanged")
    parser.add_argument("--include-replies", action="store_true", default=False)
    parser.add_argument("--include-retweets", action="store_true", default=False)
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
    parser.add_argument(
        "--limit", type=int, default=0, help="Import at most N tweets (0 = all)"
    )
    parser.add_argument(
        "--no-resolve-short-urls",
        dest="resolve_short_urls",
        action="store_false",
        default=True,
        help=(
            "Do not resolve https://lnkd.in/ short URLs found in tweet "
            "bodies. By default the importer follows each short URL once "
            "and rewrites the body to reference the real link, caching "
            "results in takeouts/lnkd-in-cache.json."
        ),
    )
    args = parser.parse_args()

    if args.publish and args.auto_publish:
        parser.error("--publish and --auto-publish are mutually exclusive")

    root, tmp = _open_takeout(args.takeout)
    try:
        tweets_js = _locate_tweets_js(root)
        print(f"reading {tweets_js.relative_to(root)}")
        tweets = _parse_tweets_js(tweets_js)
        print(f"found {len(tweets)} tweets")

        media_root = tweets_js.parent / "tweets_media"
        if not media_root.exists():
            # Some exports put media alongside the data folder differently
            alt = root / TWEETS_MEDIA_DIR
            if alt.exists():
                media_root = alt

        exclude_ids = load_exclude_set()
        policy: AutoPublishPolicy | None = (
            load_auto_publish_policy() if args.auto_publish else None
        )
        records = _build_records(
            tweets,
            user=args.user,
            media_root=media_root,
            include_replies=args.include_replies,
            include_retweets=args.include_retweets,
            exclude_ids=exclude_ids,
            draft=not args.publish,
            resolve_short=args.resolve_short_urls,
            dry_run=args.dry_run,
        )

        stats = ImportStats()
        count = 0
        for record in records:
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
            count += 1

        print(f"twitter import: {stats.summary()}")
    finally:
        save_short_url_cache()
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
