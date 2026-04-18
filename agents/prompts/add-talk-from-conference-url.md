# Add a talk from a conference URL

Copy everything below into your AI assistant.

---

Add a timeline entry for a talk I gave. Use the `create-timeline-entry` skill (`.cursor/skills/hugo-techie-create-timeline-entry/` or `themes/hugo-techie-personal/agents/skills/create-timeline-entry/SKILL.md`) and pick `activity: talk`. Follow the zero-CLI contract in `AGENTS.md` — you run `hugo server` / `hugo`, not me.

**Conference session URL:** `<paste URL>`

From that page please extract:

- Talk title
- Date (use the event date, `YYYY-MM-DD`)
- Conference / event name
- Venue / city / country (for the events map)
- Abstract (for the body)
- Link to the recording and/or slides if listed
- Co-speakers, if any
- Relevant focus areas (pick from existing ones used on the site; ask me if nothing fits)

If the page is missing any of the required fields (especially the date or event name), **ask me** — don't guess. If I have a PDF of the slide deck, I'll tell you and you should then chain into the `create-slide-deck` skill (`create-slide-deck/SKILL.md`) to process the PDF and cross-link the slide page to this timeline entry via `timeline_entry:`.

When done, start `hugo server -D`, show me the URL of the new entry, and report any build warnings.
