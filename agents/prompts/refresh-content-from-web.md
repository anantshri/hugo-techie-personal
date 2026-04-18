# Refresh content from the web

Copy everything below into your AI assistant.

---

Check my public online presence for anything new since the site was last updated, and add it here. Use the `bootstrap-portfolio` skill's research checklist (`.cursor/skills/hugo-techie-bootstrap-portfolio/research-checklist.md` or `themes/hugo-techie-personal/agents/skills/bootstrap-portfolio/research-checklist.md`). Follow the zero-CLI contract in `AGENTS.md`.

Use what's already on disk to figure out the "known set":

1. Read `content/_index.md` and `content/bio.md` to figure out who I am and my handles.
2. List everything under `content/timeline/`, `content/slides/`, `content/projects/`, `content/gadget/` and note each entry's title + date.
3. Read `config.toml` for badge platform usernames and analytics config.

Then research what's new:

- **GitHub** — new public repos since the most recent `content/projects/*` entry's date. Skip forks, archived-for-a-while repos, and anything already covered.
- **Conference archives / Sessionize / Notist** — sessions tagged with my handle since the most recent `content/timeline/*` entry with `activity: talk` or `training`.
- **LinkedIn / personal domain / Mastodon / Bluesky** — announcements of talks / trainings / articles not yet on the site.
- **Credly / Accredible / Badgr / HackerOne / Bugcrowd** — new badges not yet cached.
- **Google Scholar / arXiv / whitepapers** — new publications.

Produce a **proposed changeset** first — a plain list of "I'd add X at /path (skill: create-timeline-entry)". Let me confirm before you write anything. Treat this as mode **C (Interactive)** from the `bootstrap-portfolio` skill, not full-generate.

For each confirmed item, chain into the appropriate skill:

- Timeline: `create-timeline-entry`
- Slides: `create-slide-deck` (ask me where the PDF is first)
- Project: `create-project`
- Badges: `set-up-badges` if a new platform; otherwise just rebuild to let the existing shortcodes pick up new badges.

When done, `hugo server -D`, show me the new URLs, and tell me what you skipped and why.

Don't fabricate dates. If you can't confirm a date from the source, **ask me** rather than guess.
