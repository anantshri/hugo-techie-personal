# AGENTS.md — `hugo-techie-personal`

> **Who this file is for:** AI coding assistants (Cursor, Claude Code, Codex, Aider, ChatGPT with browsing, Windsurf, …) helping a user build or maintain a Hugo site that uses the `hugo-techie-personal` theme. The user is expected to be **non-technical** and to drive everything through chat — the assistant runs the shell.

If you are a human, see [`README.md`](README.md) and [`docs/`](docs/).

---

## Zero-CLI contract

The user does **not** open a terminal. You do. That means:

- You run `hugo new site …`, `git submodule add …`, `hugo server`, `./themes/hugo-techie-personal/scripts/*`, and every other command.
- Never tell the user "run this command yourself" unless a tool explicitly refuses (e.g. a package manager prompting for a sudo password).
- After every significant change, run `hugo` (or keep `hugo server` going in a background terminal) and report the URL / any errors.
- If a dependency is missing (`hugo`, `poppler`, `cwebp`, `imagemagick`, `uv`, …), install it: `brew install …` on macOS, `apt-get install …` on Debian/Ubuntu. Ask for sudo only when required.
- Use `uv` for every Python invocation (importers, scripts). Never `pip` / `python3 -m pip`.

---

## How to use this file

1. When the site is created, copy this file to the **site root** as `AGENTS.md`:

   ```sh
   cp themes/hugo-techie-personal/AGENTS.md ./AGENTS.md
   ```

   The installer script does this for you — see below.

2. Run the installer once per site:

   ```sh
   ./themes/hugo-techie-personal/agents/install.sh
   ```

   It copies this file to the site root (if missing) and wires every skill under [`agents/skills/`](agents/skills/) into `.cursor/skills/hugo-techie-*/` and/or `.claude/skills/hugo-techie-*/` if those directories exist. If the theme is a git submodule it symlinks; otherwise it copies. A `.agents-skills` symlink always points at the canonical skills folder so assistants that just scan directories can find them.

3. From that point on, the user can say things like *"add a talk I gave at DefCon"* or *"build me a portfolio from my GitHub handle"* and your job is to pick the matching skill below and follow it.

---

## What this theme provides (one-line summary)

A timeline-driven personal site for tech professionals. Content types: **timeline entries** (talks, trainings, panels, tools, awards, articles…), **slide decks** (PDF → WebP viewer), **projects**, **gadgets**, **interests**, a **bio page**, a **map of events**, **badges** (Credly, Accredible, Bugcrowd, HackerOne, Badgr, Open Badges, manual), and a **social archive** (importers for X, LinkedIn, Instagram, Facebook takeouts).

For the feature list see [`README.md`](README.md). For config details see [`docs/configuration.md`](docs/configuration.md). For layouts see [`docs/layouts.md`](docs/layouts.md). For shortcodes see [`docs/shortcodes.md`](docs/shortcodes.md).

---

## Content types at a glance

Pick the skill that matches what the user is asking for. Each skill is self-contained — read its `SKILL.md` and follow the instructions there.

| The user wants to…                               | Skill                                                                                 |
|--------------------------------------------------|---------------------------------------------------------------------------------------|
| Start a new site from nothing                    | [`bootstrap-portfolio`](agents/skills/bootstrap-portfolio/SKILL.md)                   |
| Add a talk / training / panel / podcast / award  | [`create-timeline-entry`](agents/skills/create-timeline-entry/SKILL.md)               |
| Add a presentation deck (PDF)                    | [`create-slide-deck`](agents/skills/create-slide-deck/SKILL.md)                       |
| Add a project                                    | [`create-project`](agents/skills/create-project/SKILL.md)                             |
| Add a gadget / device review                     | [`create-gadget`](agents/skills/create-gadget/SKILL.md)                               |
| Add an interest page                             | [`create-interest`](agents/skills/create-interest/SKILL.md)                           |
| Write or update the bio page                     | [`write-bio-page`](agents/skills/write-bio-page/SKILL.md)                             |
| Edit `config.toml`, menus, socials, analytics    | [`configure-site`](agents/skills/configure-site/SKILL.md)                             |
| Configure Credly / Accredible / etc.             | [`set-up-badges`](agents/skills/set-up-badges/SKILL.md)                               |
| Import an X / LinkedIn / IG / FB takeout         | [`import-social-archive`](agents/skills/import-social-archive/SKILL.md)               |
| Deploy the site                                  | [`deploy-site`](agents/skills/deploy-site/SKILL.md)                                   |

When in doubt, start with `bootstrap-portfolio` — it delegates to the other skills.

---

## Shared conventions (apply to every content type)

### Dates

- Always `YYYY-MM-DD`. No `2025/06/15`, no `June 15, 2025`, no `15th June`.
- For future events, use the scheduled date.
- **Never guess a date.** If the user hasn't given one and it can't be derived from a GitHub repo / URL / page metadata, ask for it.

### Drafts

- `draft: true` keeps a page out of production builds (`hugo` without `-D`).
- New content starts as `draft: false` unless the user says otherwise — the theme is a personal site, so users expect what they add to show up. The social archive importers are the one exception: they default to `draft: true` so the user can curate.

### Images

- Site images live under `static/images/` and are referenced as `/images/foo.jpg`.
- Project images live under `static/images/projects/` and are referenced as `images/projects/foo.png` (no leading slash — it's relative to the static root).
- If the user doesn't provide an image, omit `featured_image` entirely; the theme renders a placeholder SVG. Don't invent filenames.
- For profile pics, bio photos, and anything else Hugo needs to resize, put it under `assets/` (e.g. `assets/images/bio/headshot.jpg`).

### Shortcodes you will use constantly

- `{{% oembed url="https://…" %}}` — videos, slides, social posts. Always use the full `https://` URL, never a relative or localhost URL (Hugo can't fetch from itself at build time).
- `{{< notice warning "Title" >}}…{{< /notice >}}` — styled callouts: `warning`, `info`, `tip`, `note`.
- `{{< badges >}}` and platform-specific badge shortcodes — see [`set-up-badges`](agents/skills/set-up-badges/SKILL.md).

### Shortcodes you must NOT use in content

- `{{< slideviewer … >}}` — **theme-internal only.** In any `content/…` file always use `{{% oembed url="https://<site>/slides/<slug>/" %}}` instead. This rule exists because Hugo's `resources.GetRemote` can't fetch from itself; the `slideviewer` shortcode works inside the theme's own layout templates but fails from content.

### Cross-linking

- Timeline → project: `project_links: [project-slug]` in timeline frontmatter. The slug is the project filename without `.md`.
- Timeline → external blog / research page: `related_links` (card-style, auto-fetches Open Graph metadata).
- Timeline → social posts: `social_chatter: [url, url, …]` — Twitter/X, Bluesky, Mastodon, LinkedIn, Facebook, Instagram.
- Slide → timeline: `timeline_entry: "/timeline/entry-slug/"` in slide frontmatter.
- Slide → slide: `related_presentations: ["/slides/other/"]`.

### Events map

Timeline and slide entries with `location: {latitude, longitude}` (and `online` unset or `false`) appear on the map at `/map/`. When a slide has `timeline_entry` set, the slide is excluded from the map — the linked timeline entry represents the event instead. Set `online: true` for virtual events to exclude them entirely.

---

## Bootstrapping a brand-new site

If the user has nothing yet, follow the [`bootstrap-portfolio`](agents/skills/bootstrap-portfolio/SKILL.md) skill. It will:

1. Offer the user three modes (research-only / full-generate / interactive interview).
2. Gather identity info (name, handles, domains).
3. Research the user across GitHub, LinkedIn, conference archives, personal domains, Google Scholar, Mastodon/Bluesky/X, Wikipedia.
4. Produce either a draft outline, a fully-populated site, or an interview-confirmed set of pages.
5. Boot `hugo server` and hand the user a URL.

**If you have no web access**, the skill degrades to a paste-URLs flow: ask the user for their handles/links, fetch what they paste, and build from that. Do not fail fast.

---

## Running commands on the user's behalf

### Expected tooling

| Tool           | Required for                         | macOS install            | Debian/Ubuntu install               |
|----------------|--------------------------------------|--------------------------|-------------------------------------|
| `hugo`         | everything (≥ 0.158.0)               | `brew install hugo`      | `snap install hugo --channel=extended` |
| `git`          | everything                           | preinstalled / `brew`    | `apt-get install git`               |
| `poppler-utils`| slide processing (`pdftoppm`)        | `brew install poppler`   | `apt-get install poppler-utils`     |
| `libwebp`      | slide processing (`cwebp`)           | `brew install webp`      | `apt-get install libwebp-dev`       |
| `imagemagick`  | slide processing (`magick`/`convert`)| `brew install imagemagick` | `apt-get install imagemagick`     |
| `uv`           | every Python script (importers)      | `brew install uv`        | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

If a command fails with "command not found", install the tool and retry. Do not ask the user to do it.

### Theme scripts you will run

All under `themes/hugo-techie-personal/scripts/`:

- `scaffold-slides.sh` — create `content/slides/<slug>/index.md` for each new PDF in `assets/slides/pdf_files/`.
- `process-slides.sh` — convert PDFs to WebP slide images, copy PDFs to `static/` for download, update `page_count` frontmatter. Idempotent.
- `import_twitter.py`, `import_linkedin.py`, `import_instagram.py`, `import_facebook.py` — social takeout importers. See [`import-social-archive`](agents/skills/import-social-archive/SKILL.md).
- `fetch-related-images.sh` — pre-fetch Open Graph images for `related_links`.
- `migrate-notist.py`, `migrate-slides.sh` — one-time migration helpers for legacy content. Unlikely to be needed on a new site.

---

## Patterns you may want to adopt

These are conventions from sites using this theme (notably [anantshri.info](https://anantshri.info)) that aren't baked into the theme but work well with it. Offer them to the user when relevant.

### `ai_summary/` — external AI-generated summaries

Store AI-generated summaries outside `content/` so they don't pollute the markdown source and can be regenerated idempotently. Typical layout:

```
ai_summary/
├── video/<timeline-slug>.md      # raw summary from a transcript
├── slides/<slide-slug>.md        # raw summary from a PDF
└── unified/<timeline-slug>.md    # merged narrative for the timeline page
```

Teach the timeline/slide single-page templates to `{{ with … }}` include the matching file at build time and prepend a heading + `{{< ai-summary-disclaimer >}}`. The content files stay pure markdown; summaries refresh by swapping files.

### `defunk_links` — preserve dead external references

Over time, external links in `related_links` (blog posts, conference session pages, press coverage) go dead. Instead of deleting them, move them to a `defunk_links:` frontmatter list with the same shape — they stop rendering as cards but the historical record is preserved. Add a small helper that regenerates `.lycheeignore` from every `defunk_links` URL across the site so the CI link checker skips them automatically.

Both patterns are optional. Document them in the user's site-level `AGENTS.md` (the one at the site root) if they decide to adopt them.

---

## When you are stuck

- Re-read the skill's `SKILL.md`. If the answer isn't there, check the skill's `tool-specific-tips.md` for notes about Cursor / Claude / ChatGPT / Aider.
- If a skill is missing something, consult [`docs/`](docs/) and [`README.md`](README.md) — they are the authoritative human reference.
- If you still don't know, ask the user rather than guess. Especially for dates, event names, and URLs.

---

## License

This guide and every skill under [`agents/skills/`](agents/skills/) ship under the same MIT license as the theme itself — see [`LICENSE.md`](LICENSE.md). You and the user are free to copy, adapt, and extend anything here.
