---
name: hugo-techie-create-project
description: Create a project page under content/projects/ on a hugo-techie-personal site. Handles frontmatter (github_url, website_url, focus_area, tags, featured_image), TL;DR fields, optional long-form body, and discontinued/archived/planned status markers. Use when the user wants to add a new project, document a GitHub repo, or mark an existing project as discontinued.
---

# create-project

Add a single project page under `content/projects/<slug>.md`.

## When to use

- *"Add my project X."*
- *"I have a GitHub repo, make a project page for it."*
- *"Document this tool I built."*

## Inputs

| Field              | Required? | Notes |
|--------------------|-----------|-------|
| Slug (filename)    | yes       | lowercase-hyphens; matches what timeline entries use in `project_links:`. |
| Title              | yes       | Display name. |
| Date               | yes       | First public release or repo creation. `YYYY-MM-DD`. Ask if unknown. |
| GitHub URL         | optional  | `github_url:` |
| Website URL        | optional  | `website_url:` |
| Focus area         | recommended | One short phrase, e.g. `"Application Security"`. |
| Tags               | recommended | 3–6 tags. |
| Featured image     | optional  | Save to `static/images/projects/<slug>.png`, reference as `images/projects/<slug>.png` (no leading slash). |
| Status             | only if not active | `discontinued`, `archived`, `planned`. |

## Frontmatter template

```yaml
---
title: "Project Name"
date: 2021-03-14
draft: false
featured_image: "images/projects/project-name.png"   # omit if none
tags: ["tag1", "tag2", "security", "github"]
github_url: "https://github.com/user/repo"
website_url: "https://project-website.com"            # omit if none
focus_area: "Primary Focus Area"
tldr_description: "One-line description."
tldr_best_for: "Target audience."
tldr_key_features: "Key features in brief."
# status: discontinued       # only for discontinued / archived / planned
# discontinue_date: 2023-06-01
# show_content: true          # set to render the long-form body below
---
```

## Content body template

The body renders when `show_content: true` or by default depending on the theme's layout cascade. Use the following structure when the user wants more than a TL;DR:

```markdown
One-paragraph elevator pitch.

## Project overview

What it does, why it exists, who it's for.

## Key features

### Category 1
- Feature 1
- Feature 2

### Category 2
- Feature 3

## Technical implementation

- **Language/stack:** Go + SQLite
- **Architecture:** single binary, embedded web UI
- **APIs integrated:** GitHub, VirusTotal

## Usage

### Quick start
1. Install: `brew install <name>`
2. Run: `<name> scan .`

## Use cases

- Use case 1
- Use case 2

## Future development

- Planned feature A
- Planned feature B
```

## Procedure

1. **Write** `content/projects/<slug>.md` with the frontmatter + body (body is optional).
2. **Save the image** (if any) to `static/images/projects/<slug>.png`. Do not hotlink.
3. **Cross-link**: when writing timeline entries about this project, set `project_links: [<slug>]` in their frontmatter.
4. **Verify**: `hugo server -D`, open `/projects/<slug>/`.

## Status handling

- `status: discontinued` → appears in a "Discontinued Projects" section on the list page. Add `discontinue_date`.
- `status: archived` → kept for historical reference, styled as archived.
- `status: planned` → something the user plans to build but hasn't yet. Renders with a "planned" marker.

No `status:` → currently active.

## Helper files

- [`tool-specific-tips.md`](tool-specific-tips.md) — notes on GitHub API extraction.

## Common pitfalls

- **Wrong image path.** Projects use `images/projects/<slug>.png` (relative, no leading slash). Timeline / slides use absolute paths. Don't mix.
- **Slug drift.** The project slug appears in `project_links` from timeline entries — if you rename later, update those too.
- **Inventing a date.** If unknown, use the GitHub repo's `created_at` from `https://api.github.com/repos/<user>/<repo>` — don't guess.
