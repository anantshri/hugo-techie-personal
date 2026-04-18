---
name: hugo-techie-create-timeline-entry
description: Create a single entry under content/timeline/ for a talk, training, panel, podcast/interview, tool demo, article, quote, recognition, CTF, whitepaper, or curation activity on a hugo-techie-personal site. Handles frontmatter, oembed for videos/slides, cross-links to projects and related blogs, social chatter embeds, and the events-map location block. Use when the user asks to add a single timeline entry, record a talk/training/podcast/award, or document a conference session.
---

# create-timeline-entry

Add a single timeline entry — talk, training, panel, podcast, award, article, etc. — under `content/timeline/`.

## When to use this skill

Trigger it when the user says:

- *"Add a talk I gave at …"*
- *"I was on a podcast, add it."*
- *"Record this training I delivered."*
- *"I won an award — add it to the timeline."*
- *"Add <event> to my timeline."*

## Inputs you need before writing

Confirm these with the user or extract from a URL they give you. Don't guess.

| Field       | Required? | Notes |
|-------------|-----------|-------|
| Title       | yes       | Full session / entry title. Keep event name out of it unless it's part of the brand (e.g. "DefCon Main Stage Panel"). |
| Activity    | yes       | One of the exact values in [`activity-types.md`](activity-types.md). |
| Event       | yes       | Conference / podcast / publication name. Keep spelling consistent with existing entries if any. |
| Date        | yes       | `YYYY-MM-DD`. Never invent. |
| URL         | no        | External link (session page, video, podcast). Goes to `redirect_url`. |
| Video / slides / oembed URL | no | For embedding. |
| Focus areas | recommended | 1–3 tags from the site's existing `focus` taxonomy. |
| Location    | recommended for physical events | `{city, country, latitude, longitude}`. |
| Online?     | mark if virtual | `online: true` excludes from the events map. |
| Related project | optional | Project slug(s) — filenames in `content/projects/` without `.md`. |

## Step 1 — pick a filename

Pattern: `<event-lowercase-hyphens>-<year>-<activity>.md` or `<event>-<subject>.md`.

Examples from real sites:
- `blackhat-europe-2025-training.md`
- `c0c0n-2024-talk.md`
- `interview-buggyaan.md`

Write to: `content/timeline/<filename>.md`.

## Step 2 — write the file

### Frontmatter template (copy this)

```yaml
---
title: "Talk Title at Event"
date: 2025-06-15
author: "Your Name"
activity: talk
event: "Event Name 2025"
featured_image: /images/event-2025.jpg         # omit if no image
redirect_url: https://conference.com/session   # omit if none
focus:
  - appsec
  - cloud
project_links:
  - cool-project                # omit or drop if no project linked
related_links:                  # omit block if no external references
  - url: "https://blog.example.com/post"
    title: "Companion blog post"
    description: "Optional one-line summary"
social_chatter:                 # omit if no social posts to cite
  - "https://x.com/user/status/123"
  - "https://www.linkedin.com/posts/user_activity-456"
location:                       # omit if virtual or unknown
  city: "Las Vegas"
  country: "USA"
  latitude: 36.1699
  longitude: -115.1398
online: false                   # true for virtual events → excluded from events map
---
```

### Content body template

```markdown
## Official website

- [Event Name 2025](https://conference.com/session)

**Date**: June 15, 2025 | 45-minute session
**Location**: Venue, City
**Track**: Track Name                         <!-- if applicable -->
**Format**: Presentation / Training / Panel   <!-- if applicable -->

## Overview

One or two paragraphs summarising the session.

## Key topics

- Topic 1
- Topic 2
- Topic 3

{{%oembed url="https://www.youtube.com/watch?v=VIDEO_ID" %}}
```

Add `{{%oembed url="…" %}}` only if you have a real YouTube/Vimeo/slide URL. Never make one up.

### Slide decks hosted on this site

If the talk has a local slide deck at `/slides/<slug>/` (see [`../create-slide-deck/SKILL.md`](../create-slide-deck/SKILL.md)), embed it with:

```markdown
{{%oembed url="https://<your-site>/slides/<slug>/" %}}
```

Use the full `https://` URL. Never use `{{< slideviewer … >}}` in content — forbidden in this theme's content files.

## Step 3 — activity-specific variations

### talk / training / panel

Use the frontmatter / body template above. For `training`, add `**Instructor**: Name | Org` in the body.

### discussion (podcast / interview)

```yaml
---
title: "Podcast Name — Episode Title"
date: 2025-03-20
activity: discussion
event: "Podcast Name"
featured_image: /images/podcast-episode.jpg
redirect_url: https://podcast.com/ep/123
focus:
  - topic-area
---

{{%oembed url="https://youtube.com/watch?v=VIDEO_ID" %}}

Brief description of what was discussed.
```

### recognition / award

```yaml
---
title: "Award: Award Name"
date: 2024-11-15
activity: recognition
event: "Award Ceremony 2024"
featured_image: /images/award.png
focus:
  - community
project_links:
  - related-project
---

One-paragraph description of the award and why it was given.

Link to related project or details: <https://example.com>.
```

### article (user wrote for an external publication)

Same template; use `activity: article`, `redirect_url` = the published URL.

### quote (user was quoted / referenced in an article)

`activity: quote`, `redirect_url` = article URL, body = 1–3 sentences summarising the quote or context.

## Step 4 — cross-link

- If a project was featured, add its slug to `project_links`.
- If there's a blog / research post companion, add it to `related_links` (title + url + optional image + optional description). Omitted title/image/description are auto-fetched from Open Graph meta at build time.
- If there's social media chatter worth preserving, add URLs to `social_chatter` (Twitter/X, Bluesky, Mastodon, LinkedIn, Facebook, Instagram).

## Step 5 — image (optional)

If the user gives you a hero image:

1. Save to `static/images/<descriptive-name>.jpg` (or `.png`/`.webp`).
2. Reference as `featured_image: /images/<descriptive-name>.jpg` (absolute path with leading slash).

If no image, omit `featured_image` entirely — the theme renders a placeholder SVG. Do not invent a filename.

## Step 6 — verify

Run:

```sh
hugo server -D
```

Open `http://localhost:1313/timeline/<filename-without-.md>/` and confirm:

- The entry renders.
- The oembed loads (or shows a styled fallback link if the URL is offline).
- Cross-links work — click `project_links` cards, `related_links` cards.
- If `location` was set, the entry appears on `/map/`.

## Common pitfalls

- **Using `{{< slideviewer >}}` in content.** Forbidden. Use `{{% oembed url="https://<site>/slides/<slug>/" %}}` instead. The `slideviewer` shortcode is theme-internal only; Hugo can't self-fetch during build.
- **Inventing a date.** If the user didn't give one and the source URL doesn't expose it, ask. Never guess.
- **Inconsistent event names.** Spell them the same way across entries. "BlackHat Europe 2025" and "Black Hat EU '25" will fragment groupings.
- **Relative oembed URLs.** Always `https://`. Relative paths and `localhost` fail at build time.
- **Forgetting `online: true` for virtual events.** Otherwise they appear on the physical events map at `/map/`.
- **Dropping `focus`.** Even one tag helps the taxonomy-based list layouts (`category`, `priority`).

## Helper files

- [`activity-types.md`](activity-types.md) — the exact allowed `activity:` values.
- [`tool-specific-tips.md`](tool-specific-tips.md) — Cursor / Claude / ChatGPT / Aider notes on fetching Open Graph metadata and writing files.
