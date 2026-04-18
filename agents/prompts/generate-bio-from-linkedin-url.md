# Generate a bio page from a LinkedIn / about-page URL

Copy everything below into your AI assistant.

---

Write my bio page. Use the `write-bio-page` skill (`.cursor/skills/hugo-techie-write-bio-page/` or `themes/hugo-techie-personal/agents/skills/write-bio-page/SKILL.md`) and follow the zero-CLI contract in `AGENTS.md`.

**Source URL:** `<paste LinkedIn profile, about page, or speaker bio URL>`

Please fetch that page and produce `content/bio.md` with:

- **`short_bio`** — one tight paragraph, ≤ 100 words, suitable for conference programs and speaker introductions.
- **`long_bio`** — 3–5 paragraphs covering career arc, expertise, current focus, and notable achievements.
- **`subtitle`** — my current professional title.

Use **third person** unless I tell you otherwise — speaker bios read better that way.

Don't invent anything. If a claim isn't in the source I gave you, either leave it out or ask me.

If I've already run `bootstrap-portfolio` and there's a `person.bio_short` / `person.bio_long` in `discoveries.yaml`, merge that material in instead of starting from scratch.

For photos: ask me. Don't try to generate or hotlink a headshot. If I have photos, remind me that they must go under `assets/images/bio/` (not `static/`) because the bio layout uses `resources.Get`.

When done, start `hugo server -D` and show me `/bio/` — I want to see the tabbed Rendered / Markdown / Plain text blocks and the copy buttons working.
