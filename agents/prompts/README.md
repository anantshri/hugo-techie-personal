# `agents/prompts/` — ready-to-paste prompts

Copy any of these into your AI assistant of choice (Cursor, Claude Code, ChatGPT, Aider, Windsurf, …) from a Hugo site that has the `hugo-techie-personal` theme installed and this guide wired in (see [`../README.md`](../README.md)).

Each prompt is intentionally short. The real instructions live in the skills the assistant is pointed at (`.cursor/skills/hugo-techie-*`, `.claude/skills/hugo-techie-*`, or `.agents-skills/…` / `themes/hugo-techie-personal/agents/skills/…`).

| Prompt | What it does |
|---|---|
| [`bootstrap-from-name.md`](bootstrap-from-name.md) | Research a person and scaffold a full site. |
| [`add-talk-from-conference-url.md`](add-talk-from-conference-url.md) | Add one timeline entry from a conference session URL. |
| [`add-project-from-github-repo.md`](add-project-from-github-repo.md) | Add a project page from a GitHub repo URL. |
| [`generate-bio-from-linkedin-url.md`](generate-bio-from-linkedin-url.md) | Write a `content/bio.md` using a LinkedIn profile / about page. |
| [`refresh-content-from-web.md`](refresh-content-from-web.md) | Re-check online sources for new talks/projects/badges since the last import. |

Human notes only — the assistant should follow the skills, not these files.
