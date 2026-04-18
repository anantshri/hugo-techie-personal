# Bootstrap a portfolio from a name

Copy everything below into your AI assistant.

---

I want you to build me a working `hugo-techie-personal` portfolio site from public information online.

Use the `bootstrap-portfolio` skill that ships with the theme (look for it in `.cursor/skills/hugo-techie-bootstrap-portfolio/`, `.claude/skills/hugo-techie-bootstrap-portfolio/`, or `themes/hugo-techie-personal/agents/skills/bootstrap-portfolio/` — whichever your tooling uses). Also read the top-level `AGENTS.md` first so you know the zero-CLI contract: you run every command, I don't touch a terminal.

Here's what I can give you:

- **Name:** `<full name>`
- **Primary handle / preferred GitHub user:** `<handle>` (optional)
- **Personal domain, if any:** `<domain>` (optional)
- **Mode I want:** <pick one>
  - **A — Research-only:** gather discoveries, show me the summary, don't write content yet.
  - **B — Full-generate:** research, scaffold `config.toml`, create real content entries, end with a running `hugo server`.
  - **C — Interactive:** research, then ask me to confirm each discovered item before writing it.

If you can't access the web, tell me — I'll paste URLs and content and we'll switch into the "degrade gracefully" flow from the skill. Don't fabricate anything.

When you're done, give me the local URL to open in a browser.
