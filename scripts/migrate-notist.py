#!/usr/bin/env python3
"""
migrate-notist.py — One-time migration of Noti.st presentations to Hugo page bundles.

Usage:
    python scripts/migrate-notist.py <notist_username> [--output content/slides]

Scrapes the Noti.st profile and individual talk pages, downloads slide images,
and generates Hugo page bundles with frontmatter.

Dependencies: pip install -r scripts/requirements.txt
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
import yaml
from bs4 import BeautifulSoup

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; NotistMigrator/1.0)"
})

# Rate limiting
REQUEST_DELAY = 1.0  # seconds between requests


def fetch(url: str) -> requests.Response:
    """Fetch a URL with rate limiting."""
    time.sleep(REQUEST_DELAY)
    resp = SESSION.get(url, timeout=30)
    resp.raise_for_status()
    return resp


def slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def get_talk_urls(username: str) -> list[dict]:
    """Scrape the Noti.st profile page for talk URLs."""
    profile_url = f"https://noti.st/{username}"
    print(f"Fetching profile: {profile_url}")

    resp = fetch(profile_url)
    soup = BeautifulSoup(resp.text, "lxml")

    # Noti.st talk URLs use short IDs: /<shortId>/<slug>
    # e.g. /siPe3t/beyond-software-dependencies-...
    # Exclude: /, /videos/*, external links, profile link itself
    TALK_RE = re.compile(r"^/([A-Za-z0-9]{5,8})/([a-z0-9][\w-]+)$")

    talks = []
    for link in soup.select("a[href]"):
        href = link.get("href", "")
        if not href.startswith("/") or href.startswith("/videos"):
            continue
        if href == f"/{username}" or href == f"/{username}/":
            continue
        m = TALK_RE.match(href)
        if m:
            full_url = urljoin(profile_url, href)
            title = link.get_text(strip=True) or ""
            talks.append({"url": full_url, "title": title, "path": href})

    # Deduplicate
    seen = set()
    unique = []
    for t in talks:
        if t["url"] not in seen:
            seen.add(t["url"])
            unique.append(t)

    print(f"Found {len(unique)} talks")
    return unique


def scrape_talk(url: str) -> dict:
    """Scrape an individual talk page for metadata and slide images."""
    print(f"  Scraping: {url}")
    resp = fetch(url)
    soup = BeautifulSoup(resp.text, "lxml")

    data = {
        "url": url,
        "title": "",
        "date": "",
        "conference": "",
        "abstract": "",
        "slide_images": [],
        "video_urls": [],
        "notist_path": urlparse(url).path,
    }

    # Title
    title_el = soup.select_one("h1") or soup.select_one(".talk-title")
    if title_el:
        data["title"] = title_el.get_text(strip=True)

    # Conference / event name
    event_el = soup.select_one(".event-name") or soup.select_one("h2")
    if event_el:
        data["conference"] = event_el.get_text(strip=True)

    # Date
    date_el = soup.select_one("time")
    if date_el:
        dt = date_el.get("datetime", "")
        if dt:
            data["date"] = dt[:10]  # YYYY-MM-DD

    # Abstract / description
    desc_el = soup.select_one(".talk-description") or soup.select_one(".description")
    if desc_el:
        data["abstract"] = desc_el.get_text(strip=True)

    # Slide images — Noti.st uses img tags with large-N.jpg pattern
    for img in soup.select("img"):
        src = img.get("src", "") or img.get("data-src", "")
        if src and ("large-" in src or "slide" in src.lower()):
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = urljoin(url, src)
            data["slide_images"].append(src)

    # Also check for image links in data attributes or JSON-LD
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            ld = json.loads(script.string)
            if isinstance(ld, dict):
                if "image" in ld:
                    imgs = ld["image"] if isinstance(ld["image"], list) else [ld["image"]]
                    data["slide_images"].extend(imgs)
        except (json.JSONDecodeError, TypeError):
            pass

    # Deduplicate images
    seen = set()
    unique_imgs = []
    for img_url in data["slide_images"]:
        if img_url not in seen:
            seen.add(img_url)
            unique_imgs.append(img_url)
    data["slide_images"] = unique_imgs

    # Video embeds
    for iframe in soup.select("iframe"):
        src = iframe.get("src", "")
        if "youtube" in src or "vimeo" in src:
            # Extract canonical video URL
            if "youtube.com/embed/" in src:
                vid = src.split("/embed/")[-1].split("?")[0]
                data["video_urls"].append(f"https://www.youtube.com/watch?v={vid}")
            elif "vimeo.com" in src:
                vid = src.split("/")[-1].split("?")[0]
                data["video_urls"].append(f"https://vimeo.com/{vid}")

    return data


def download_slides(talk: dict, output_dir: Path) -> int:
    """Download slide images into the page bundle."""
    slides_dir = output_dir / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for i, img_url in enumerate(talk["slide_images"], 1):
        num = f"{i:03d}"
        ext = ".jpg"

        # Determine extension from URL
        parsed = urlparse(img_url)
        if parsed.path.endswith(".png"):
            ext = ".png"
        elif parsed.path.endswith(".webp"):
            ext = ".webp"

        out_file = slides_dir / f"slide-{num}-full{ext}"

        if out_file.exists():
            print(f"    Slide {num}: already exists, skipping")
            count += 1
            continue

        print(f"    Downloading slide {num}...")
        try:
            resp = fetch(img_url)
            out_file.write_bytes(resp.content)
            count += 1
        except Exception as e:
            print(f"    WARNING: Failed to download {img_url}: {e}")

    # Write metadata
    metadata = {
        "page_count": count,
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_pdf": "",
        "source_hash": "",
        "dimensions": {"width": 0, "height": 0},
        "migrated_from": "notist",
        "original_url": talk["url"],
    }
    (slides_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")

    return count


def generate_frontmatter(talk: dict, slide_count: int) -> str:
    """Generate Hugo frontmatter YAML."""
    date = talk.get("date") or datetime.now().strftime("%Y-%m-%d")

    fm = {
        "title": talk["title"],
        "date": date,
        "draft": False,
        "conference": talk.get("conference", ""),
        "conference_url": "",
        "event_year": int(date[:4]) if date else datetime.now().year,
        "location": {
            "city": "",
            "country": "",
            "latitude": 0,
            "longitude": 0,
        },
        "slides": {
            "pdf": "",
            "page_count": slide_count,
            "download_enabled": True,
        },
        "videos": [{"url": v, "label": "Recording"} for v in talk.get("video_urls", [])],
        "resources": [],
        "social_chatter": [],
        "tags": [],
        "focus": [],
        "activity": "talk",
        "oembed": {
            "author_name": "",
            "author_url": "",
            "provider_name": "",
            "provider_url": "",
        },
    }

    # Add alias for old Noti.st path
    if talk.get("notist_path"):
        fm["aliases"] = [talk["notist_path"]]

    yaml_str = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    abstract = talk.get("abstract", "")

    return f"---\n{yaml_str}---\n\n{abstract}\n"


def migrate_talk(talk_info: dict, output_base: Path) -> None:
    """Migrate a single talk."""
    talk = scrape_talk(talk_info["url"])

    if not talk["title"]:
        talk["title"] = talk_info.get("title", "Untitled")

    slug = slugify(talk["title"])
    if not slug:
        slug = slugify(talk_info.get("path", "").split("/")[-1])

    bundle_dir = output_base / slug
    bundle_dir.mkdir(parents=True, exist_ok=True)

    # Download slides
    slide_count = download_slides(talk, bundle_dir)

    # Generate index.md
    content = generate_frontmatter(talk, slide_count)
    index_md = bundle_dir / "index.md"

    if index_md.exists():
        print(f"  index.md already exists, skipping write")
    else:
        index_md.write_text(content)
        print(f"  Created: {index_md}")

    print(f"  Migrated: {talk['title']} ({slide_count} slides)")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate Noti.st presentations to Hugo page bundles"
    )
    parser.add_argument("username", help="Noti.st username")
    parser.add_argument(
        "--output", "-o",
        default="content/slides",
        help="Output directory (default: content/slides)",
    )
    parser.add_argument(
        "--limit", "-l",
        type=int, default=0,
        help="Limit number of talks to migrate (0=all)",
    )
    args = parser.parse_args()

    output_base = Path(args.output)
    output_base.mkdir(parents=True, exist_ok=True)

    print(f"Migrating Noti.st presentations for: {args.username}")
    print(f"Output directory: {output_base}")
    print()

    talks = get_talk_urls(args.username)

    if args.limit > 0:
        talks = talks[:args.limit]

    for i, talk_info in enumerate(talks, 1):
        print(f"\n[{i}/{len(talks)}] {talk_info.get('title', talk_info['url'])}")
        try:
            migrate_talk(talk_info, output_base)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

    print(f"\nMigration complete. {len(talks)} talks processed.")
    print(f"Output: {output_base}")
    print()
    print("Next steps:")
    print("  1. Review generated index.md files and fill in missing metadata")
    print("  2. Add location coordinates for the map")
    print("  3. Run process-slides.sh to generate multi-resolution images")
    print("     (if you have PDFs, or the downloaded images will be used as-is)")


if __name__ == "__main__":
    main()
