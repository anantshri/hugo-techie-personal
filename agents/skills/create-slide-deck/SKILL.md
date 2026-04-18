---
name: hugo-techie-create-slide-deck
description: Add a self-hosted presentation deck to a hugo-techie-personal site. Converts a PDF to per-page WebP images via the theme's process-slides.sh script, writes frontmatter with conference/event/location metadata, and cross-links to a matching timeline entry. Use when the user has a slide PDF to host, wants to add a presentation page, or asks to turn slides into an embeddable viewer on their site.
---

# create-slide-deck

Add a self-hosted presentation deck under `content/slides/`. The theme converts PDFs to per-page WebP images and renders them with an interactive viewer (keyboard/swipe nav, grid overview, download, fullscreen, OEmbed discovery).

## When to use this skill

- *"Host my slides — here's the PDF."*
- *"Add my DefCon 31 deck."*
- *"Turn this presentation into a page on my site."*

Chain with [`../create-timeline-entry/SKILL.md`](../create-timeline-entry/SKILL.md): usually a slide deck has a matching timeline entry, and they cross-link via `timeline_entry` in the slide frontmatter and `{{% oembed %}}` in the timeline body.

## Inputs you need

| Input | Required? | Notes |
|-------|-----------|-------|
| PDF of the slides | yes | Can be a file path, a URL, or the user drops it in chat. |
| Title | yes | Usually the talk title. |
| Conference / event name | yes | e.g. "DefCon 31" |
| Event date | yes | `YYYY-MM-DD`. |
| Location (physical) | optional | `{city, country, latitude, longitude}` if you want it on the events map. |
| Matching timeline entry slug | optional | If there's a `content/timeline/<slug>.md` about this talk. |
| Video URL | optional | YouTube / Vimeo recording. |

Derive the **slug** from the filename the user gives you, or generate: `<topic>-<event>-<year>` (e.g. `supply-chain-blackhat-usa-2025`). Lowercase, hyphens only.

## Prerequisites (install if missing)

The processing script needs:

| Binary       | macOS                 | Debian/Ubuntu                  |
|--------------|-----------------------|--------------------------------|
| `pdftoppm`   | `brew install poppler`| `apt-get install poppler-utils`|
| `cwebp`      | `brew install webp`   | `apt-get install libwebp-dev`  |
| `magick`     | `brew install imagemagick` | `apt-get install imagemagick` |
| `shasum`     | preinstalled          | preinstalled (coreutils)       |

Install silently before running the script; don't ask the user.

## Step 1 — drop the PDF in the inbox

```sh
# make sure the inbox exists the first time
mkdir -p assets/slides/pdf_files

# copy from wherever the user gave it
cp "<source>.pdf" "assets/slides/pdf_files/<slug>.pdf"
```

The **filename (minus `.pdf`) becomes the slug.** If the user gave you a PDF with a noisy name (`IMG_20230811.pdf`, `final-final-v3.pdf`), rename it to a clean slug before copying.

Slugs are normalised: uppercase → lowercase, `_` → `-`, spaces → `-`.

## Step 2 — scaffold the content page

```sh
./themes/hugo-techie-personal/scripts/scaffold-slides.sh
```

This creates `content/slides/<slug>/index.md` with draft frontmatter. The script scans `assets/slides/pdf_files/*.pdf` and creates one content page per PDF that doesn't already have one. Idempotent.

## Step 3 — fill in the frontmatter

Edit `content/slides/<slug>/index.md`. Here's the template (the scaffold writes most of it):

```yaml
---
title: "Presentation Title at Conference"
date: 2025-08-07
draft: false

conference: "Conference Name 2025"
conference_url: "https://conference.com/session-link"
event_year: 2025

location:
  city: "Las Vegas"
  state: "NV"                   # optional
  country: "USA"
  latitude: 36.1699
  longitude: -115.1398

# true for virtual/online; excludes from events map
online: false

slides:
  pdf: "slides.pdf"             # always this literal value
  page_count: 0                 # auto-updated by process-slides.sh
  download_enabled: true        # show the download button

videos:                         # optional
  - label: "Conference recording"
    url: "https://youtube.com/watch?v=VIDEO_ID"

resources:                      # optional
  - title: "Project repo"
    url: "https://github.com/user/repo"

timeline_entry: "/timeline/<timeline-slug>/"  # optional but recommended
related_presentations:                         # optional
  - "/slides/other-deck/"

project_links:                   # optional
  - related-project-slug

tags: [supply-chain, sbom]
focus: [supply-chain, sbom]
activity: talk                   # talk / training / tool / panel

oembed:
  author_name: "Your Name"
  author_url: "https://your-site.com"
  provider_name: "Your Name"
  provider_url: "https://your-site.com"
---

Brief one-line abstract of the presentation (shown above the viewer).
```

Keep the abstract short — one to three sentences. Longer context goes in the timeline entry.

## Step 4 — process the PDF into slide images

```sh
./themes/hugo-techie-personal/scripts/process-slides.sh
```

This:

1. Scans `assets/slides/pdf_files/*.pdf`.
2. Checks each has a matching `content/slides/<slug>/index.md` (fails if scaffold was skipped).
3. Skips any PDF whose SHA-256 hash hasn't changed since last run.
4. Converts pages to WebP at 300 DPI, max 1920px width → `assets/slides/<slug>/slide-NNN.webp`.
5. Copies the PDF to `static/slides/<slug>/slides.pdf` for download.
6. Writes `content/slides/<slug>/slides/metadata.json` (page count, hash, dimensions).
7. Updates `slides.page_count` in the frontmatter automatically.

The script is idempotent — safe to run whenever the PDF changes.

## Step 5 — cross-link the timeline entry (if any)

If there's a matching timeline entry:

1. Make sure the slide frontmatter has `timeline_entry: "/timeline/<timeline-slug>/"`.
2. In the timeline body, embed the deck with:

   ```markdown
   {{% oembed url="https://<site>/slides/<slide-slug>/" %}}
   ```

   Use the full `https://` production URL (from `baseURL` in `config.toml`). **Not** a relative path. **Not** `localhost`. Hugo can't self-fetch at build time.

   **Never use `{{< slideviewer … >}}`** in content files — theme-internal only.

## Step 6 — verify

```sh
hugo server -D
```

Open `http://localhost:1313/slides/<slug>/`. Check:

- Viewer loads, arrow keys navigate.
- Download button is visible and downloads the PDF.
- `/slides/<slug>/embed.html` renders the iframe-friendly view.
- `/slides/<slug>/oembed.json` returns valid OEmbed JSON.
- The matching timeline entry embeds the viewer.

For the events map: if `location` was set and `online` is false / unset, the slide appears at `/slides/` (slides map). If a `timeline_entry` is set, the **timeline entry** (not the slide) represents the event on `/map/` — this dedups so each physical event has one marker. Verify the timeline entry has its own `location` block, otherwise it won't show on `/map/`.

## Common pitfalls

- **Forgetting to scaffold first.** `process-slides.sh` refuses to run on a PDF without a matching `content/slides/<slug>/index.md`. Always run `scaffold-slides.sh` first.
- **Giving the PDF a messy filename.** Rename before copying. The filename becomes the public URL.
- **Not updating `baseURL`.** `{{% oembed %}}` in a timeline entry uses the absolute URL. If `baseURL` in `config.toml` is still `https://example.com`, the embed resolves against that and Hugo can't fetch it during build. Fix `baseURL` first.
- **Committing `assets/slides/pdf_files/`.** The PDF inbox should be committed (so re-processing works on other machines) unless the user prefers to keep it out of git. The generated WebPs under `assets/slides/<slug>/` should be committed (they're the source for Hugo's build-time resizing).
- **Giving both a `timeline_entry` and a `location` on the slide.** The slide's own `location` is fine — it still shows on `/slides/` map — but the global `/map/` uses the timeline entry's location, so make sure *that* one is populated too.

## Helper files

- [`tool-specific-tips.md`](tool-specific-tips.md) — how each assistant handles PDF uploads, shell permissions, and long-running scripts.
