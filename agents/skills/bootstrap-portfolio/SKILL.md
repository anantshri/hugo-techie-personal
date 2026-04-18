---
name: hugo-techie-bootstrap-portfolio
description: Research a person from their online presence and scaffold a working hugo-techie-personal portfolio site — timeline entries, projects, bio, badges, and config. Use when the user asks to "build a portfolio", "set up a personal site from scratch", "bootstrap a site for <name>", or otherwise wants to start a fresh Hugo site using this theme. Offers three modes (research-only, full-generate, interactive interview) and degrades gracefully when the agent has no web access.
---

# bootstrap-portfolio

Turn a person's name (and/or handles) into a working `hugo-techie-personal` site — site config, home page, bio, projects, timeline entries, badges — in one flow.

## When to use this skill

Trigger it when the user says anything like:

- *"Build me a portfolio site for <name>."*
- *"Set up my personal site — I'm <name> on GitHub."*
- *"Create a starter site based on what you can find about me online."*
- *"I'm new. Make me a techie-personal site from scratch."*

Also invoke it when the user asks to start fresh on an empty or near-empty Hugo site.

## Step 1 — pick a mode

**Before any research, ask the user which mode they want** and briefly describe each:

| Mode | What you do | Best for |
|------|-------------|----------|
| **A. Research-only** | Gather web data into `plans/discoveries.yaml`, summarise for review. No content written. | Users who want a preview before committing. |
| **B. Full-generate** | Research → scaffold `config.toml` → write every page → boot `hugo server`. Assume findings are correct; flag unknowns with `draft: true`. | Users who want to see it running fast and edit afterward. |
| **C. Interactive interview** | Research first, then walk through the findings with the user — confirming each talk, project, bio paragraph, and social link before writing it. | Users who want editorial control without typing everything. |

If the user doesn't pick, default to **C (interactive)** and say so.

## Step 2 — degrade gracefully if you have no web access

Before researching, test whether you can fetch the web:

- Can you call a web-search / web-fetch tool?
- Can you run `curl` from a shell?
- Can you read an attachment the user pastes into chat?

If **none** of those are available, switch to **paste-URLs mode**:

> "I don't have web access from here. Paste me any of the following you have handy and I'll work with what you give me:
>
> - your GitHub profile URL
> - your LinkedIn URL
> - a personal site / blog URL
> - any conference session pages (CFP archives, speaker pages)
> - your Mastodon / Bluesky / X handle
> - a list of projects you want featured
> - a recent bio paragraph (CV, conference program)"

For each URL the user pastes, fetch it if you can; otherwise ask the user to paste its contents. Proceed through the rest of the flow as normal, marking entries you couldn't verify as `draft: true`.

## Step 3 — gather identity

Ask for and confirm:

1. **Display name** (what goes in the header / hero).
2. **Primary role / tagline** (e.g. *"Security Researcher & Trainer"*).
3. **Primary handle** (usually GitHub).
4. **Social handles** — LinkedIn, Twitter/X, Mastodon, Bluesky (ask which they want on the site).
5. **Personal domain(s)**, if any.
6. **Email** to show (or "none").
7. **Profile picture** — user uploads / pastes one, or you generate a placeholder SVG.
8. **What should the site emphasise?** — talks / tools / research / training / gadgets. Drives which top-level sections are prominent.

Keep this short. Five minutes of Q&A, not twenty.

## Step 4 — research the web

Follow [`research-checklist.md`](research-checklist.md). It lists every source to query, what to extract from each, and in what priority order.

Collect findings into an on-disk structured record at `plans/discoveries.yaml`:

```yaml
person:
  name: "Jane Doe"
  handle: "janedoe"
  tagline: "Security Researcher & Trainer"
  location: "Berlin, Germany"
  bio_short: "One paragraph extracted from LinkedIn / personal site."
  bio_long: "Longer narrative assembled from multiple sources."

socials:
  github: "https://github.com/janedoe"
  linkedin: "https://linkedin.com/in/janedoe"
  mastodon: "https://infosec.exchange/@janedoe"
  email: "jane@example.com"

projects:
  - slug: "coolproject"
    name: "CoolProject"
    description: "One-line from GitHub."
    github_url: "https://github.com/janedoe/coolproject"
    website_url: ""
    focus_area: "Application Security"
    tags: ["go", "security", "cli"]
    start_date: "2021-03-14"
    status: "active"       # or discontinued / archived / planned

timeline:
  - slug: "defcon-31-talk"
    title: "Hacking the Impossible @ DefCon 31"
    date: "2023-08-11"
    activity: "talk"
    event: "DefCon 31"
    focus: ["appsec"]
    video_url: "https://youtube.com/watch?v=..."
    slides_url: "https://speakerdeck.com/..."
    source_url: "https://defcon.org/html/defcon-31/..."
    location: { city: "Las Vegas", country: "USA", latitude: 36.17, longitude: -115.14 }

badges:
  credly: "janedoe"          # username, if found
  accredible: ""

focus_areas:
  - appsec
  - fuzzing
  - cloud-security
```

If a field is not findable, leave it empty and tag the entry with `draft: true` later.

## Step 5 — branch on mode

### Mode A (research-only)

1. Write `plans/discoveries.yaml` to disk.
2. Write a human-readable summary to `plans/discoveries-summary.md` listing everything you found with sources.
3. Tell the user: *"Here's what I found. Reply 'generate' when you want me to turn this into a site, or tell me what to correct."*
4. **Stop.** Do not write to `content/` or `config.toml`.

### Mode B (full-generate)

Run all of these in order. Each step delegates to another skill — consult that skill's `SKILL.md` for the details.

1. **Scaffold the site** (skip if already done):

   ```sh
   # only if no hugo config yet
   hugo new site . --force
   git init
   git submodule add https://github.com/anantshri/hugo-techie-personal.git themes/hugo-techie-personal
   cp themes/hugo-techie-personal/exampleSite/config.toml .
   ./themes/hugo-techie-personal/agents/install.sh
   ```

2. **Configure the site** — follow [`../configure-site/SKILL.md`](../configure-site/SKILL.md). Set `baseURL`, `title`, `[params] subtitle/description/footer/profile_pic`, menus, taxonomies, and output formats (copy the last two verbatim from `exampleSite/config.toml`).

3. **Write `content/_index.md`** — home page with social links. Social links go here, **not** in `config.toml`:

   ```yaml
   ---
   title: "<name>"
   social_links:
     github: "<url>"
     linkedin: "<url>"
     mastodon: "<url>"
     # verify_1: "<url>"  # rel="me" verification
   ---
   One-paragraph intro. Mention years of experience (you can use
   the literal string `YEARS_EXPERIENCE+` and the theme will substitute
   years since 2008).
   ```

4. **Bio page** — follow [`../write-bio-page/SKILL.md`](../write-bio-page/SKILL.md) with `bio_short` / `bio_long` from step 4.

5. **Projects** — for each entry in `discoveries.yaml:projects`, follow [`../create-project/SKILL.md`](../create-project/SKILL.md). If `github_url` is set and you have web access, fetch the repo's README for description and tags.

6. **Timeline entries** — for each entry in `discoveries.yaml:timeline`, follow [`../create-timeline-entry/SKILL.md`](../create-timeline-entry/SKILL.md). If a slide URL is available and you have the PDF, follow [`../create-slide-deck/SKILL.md`](../create-slide-deck/SKILL.md) to host them locally and cross-link.

7. **Badges** — if `badges.credly` / `badges.accredible` is set, follow [`../set-up-badges/SKILL.md`](../set-up-badges/SKILL.md). If neither is found, skip the badges page.

8. **Verify**:

   ```sh
   hugo --minify
   hugo server -D
   ```

   Report the local URL (`http://localhost:1313`) and any build errors to the user.

9. **Commit** (ask first): `git add -A && git commit -m "Initial portfolio from bootstrap-portfolio skill"`.

### Mode C (interactive interview)

1. Do the research silently.
2. Walk through the findings using [`interview-questions.md`](interview-questions.md):
   - Confirm bio paragraphs (show short + long, ask for edits).
   - Confirm each project (show name + description + URL, ask include/exclude/edit).
   - Confirm each timeline entry (show date + title + event + source, ask include/exclude/edit).
   - Confirm focus areas and taxonomy.
   - Confirm social links.
3. After each confirmation, write just that one thing to disk, using the matching skill.
4. At the end, boot `hugo server` and report the URL.

## Step 6 — hand over

Whatever mode was chosen, end with:

1. A summary of what was created (counts: N timeline entries, M projects, …).
2. The list of items marked `draft: true` that need user attention.
3. A short cheat-sheet of things the user can now say to add more:
   - *"Add a talk I gave at <event>. Here's the link: <url>."*
   - *"I have a new project — here's the GitHub URL."*
   - *"Here's my Credly handle, set up my badges."*

## Helper files in this skill

- [`research-checklist.md`](research-checklist.md) — every source to query and what to extract.
- [`interview-questions.md`](interview-questions.md) — the exact questions to ask in Mode C.
- [`tool-specific-tips.md`](tool-specific-tips.md) — Cursor / Claude / ChatGPT / Aider notes on web access, shell execution, and file writes.

## Common pitfalls

- **Guessing dates.** Don't. If GitHub shows a repo was created in 2021 but no talk record gives a day, ask. Never invent `2021-01-01`.
- **Inventing event names.** If you see "Black Hat USA" on a slide but no year, ask. Event names in the theme are used to group entries on the UI.
- **Forgetting `project_links` in timeline entries.** If a talk is about a project you also created, link them.
- **Skipping `location` / setting `online: true` wrong.** Events without coordinates don't show on the map, and online events are excluded even when coordinates are present. Get this right for the map to be useful.
- **Using `{{< slideviewer >}}` in content.** Forbidden. Use `{{% oembed url="https://<site>/slides/<slug>/" %}}`.
- **Overshadowing the user's voice.** Bio text should be in their tone, not a generic résumé paraphrase. When in doubt, pull a real sentence from their profile and quote it.
