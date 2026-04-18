# AI Guidance for `hugo-techie-personal`

Build and maintain your site by talking to an AI assistant — no terminal required on your side.

This folder ships with the theme. It contains everything an AI coding assistant (Cursor, Claude Code, Codex, Aider, Windsurf, ChatGPT with browsing, …) needs to author content for you.

## 5-minute quickstart

### 1. Create the site (have your AI do this)

Open your AI assistant in an empty folder and say:

> "Create a new Hugo site here and add the `hugo-techie-personal` theme as a git submodule."

The assistant will run:

```sh
hugo new site .
git init
git submodule add https://github.com/anantshri/hugo-techie-personal.git themes/hugo-techie-personal
cp themes/hugo-techie-personal/exampleSite/config.toml .
```

### 2. Install the AI guidance

Ask your AI:

> "Run the theme's AI install script."

The assistant will run:

```sh
./themes/hugo-techie-personal/agents/install.sh
```

This:

- Copies `AGENTS.md` to your site root so the AI can find it.
- Wires each skill under `themes/hugo-techie-personal/agents/skills/` into `.cursor/skills/hugo-techie-*/` and/or `.claude/skills/hugo-techie-*/` (whichever your assistant uses). Symlinks if the theme is a git submodule; copies otherwise.
- Creates a `.agents-skills` pointer at the site root for assistants that just scan folders.

### 3. Drive it with plain English

From here, talk to the AI assistant like this:

| You say…                                           | What happens                                                |
|----------------------------------------------------|-------------------------------------------------------------|
| *"Build me a portfolio site. I'm Jane Doe, @janedoe on GitHub."* | Runs the `bootstrap-portfolio` skill — researches you, fills timeline/projects/bio, boots `hugo server`. |
| *"Add a talk I gave at DefCon 31. Here's the link."* | Runs `create-timeline-entry` — writes the markdown, links the YouTube video. |
| *"I have a PDF of my slides, here it is."*         | Runs `create-slide-deck` — converts the PDF to WebP slides, creates a viewer page. |
| *"Add my new project."*                            | Runs `create-project`.                                      |
| *"Set up my Credly badges — my handle is `janedoe`."* | Runs `set-up-badges`.                                    |
| *"Import my LinkedIn takeout from this zip."*      | Runs `import-social-archive`.                               |
| *"Deploy this to GitHub Pages."*                   | Runs `deploy-site`.                                         |

The assistant will ask clarifying questions when needed (dates, event names, image preferences) and run every shell command on your behalf.

## What's in this folder

```
agents/
├── README.md             # you are here
├── install.sh            # wires the skills into your Hugo site
├── skills/               # one folder per skill
│   ├── bootstrap-portfolio/
│   ├── create-timeline-entry/
│   ├── create-slide-deck/
│   ├── create-project/
│   ├── create-gadget/
│   ├── create-interest/
│   ├── write-bio-page/
│   ├── configure-site/
│   ├── set-up-badges/
│   ├── import-social-archive/
│   └── deploy-site/
└── prompts/              # ready-to-paste prompts you can send to any assistant
```

Each skill folder has:

| File                      | Purpose                                                                 |
|---------------------------|-------------------------------------------------------------------------|
| `SKILL.md`                | Single file combining Cursor/Claude frontmatter (`name`, `description`) with the full portable Markdown instructions. Any AI can read the Markdown body; tools that understand the `SKILL.md` convention (Cursor, Claude Code) also use the frontmatter for discovery. |
| `tool-specific-tips.md`   | Notes for Cursor, Claude Code, ChatGPT, Aider — how each handles web access, shell, etc. |
| (additional helper files) | Lookups, checklists, interview questions, etc.                          |

## FAQ

**Q: I already have a Hugo site and the theme. Do I need to run `install.sh` again?**
Yes, once. It's idempotent — safe to re-run. Pass `--force` to overwrite an existing `AGENTS.md` at the site root.

**Q: The theme updates. How do I get the new skills?**
If the theme is a git submodule and `install.sh` used symlinks (the default in that case), new skills appear automatically. Otherwise: `./themes/hugo-techie-personal/agents/install.sh --force`.

**Q: My AI doesn't know about Cursor/Claude skills. Will this still work?**
Yes. Every `SKILL.md` is plain Markdown with a YAML frontmatter header that non-skill-aware assistants simply treat as a documentation block. The `AGENTS.md` at your site root points at them. The `.agents-skills` symlink makes them discoverable even for assistants that don't know the `skills/` convention.

**Q: Can my AI actually do web research?**
If your assistant has any web-fetch or web-search tool (Cursor's `WebSearch`, Claude's web search, ChatGPT browsing, or just `curl` in a shell), the research-heavy skills will use it. If it can't, the `bootstrap-portfolio` skill degrades to "paste the URLs you want me to use and I'll work from those."

**Q: Can I customise the skills?**
Yes. They ship under the theme's MIT license. Copy any skill out of `themes/hugo-techie-personal/agents/skills/` into your own `.cursor/skills/` or `.claude/skills/` and edit freely. If you find improvements that generalise, consider contributing them back upstream.

## Related docs

- [`../AGENTS.md`](../AGENTS.md) — the router your AI reads first.
- [`../README.md`](../README.md) — theme features for humans.
- [`../docs/configuration.md`](../docs/configuration.md) — all `config.toml` parameters.
- [`../docs/layouts.md`](../docs/layouts.md) — bio page, map page, list layouts.
- [`../docs/shortcodes.md`](../docs/shortcodes.md) — every shortcode.

## License

MIT, same as the theme. See [`../LICENSE.md`](../LICENSE.md).
