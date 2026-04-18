# Add a project from a GitHub repo

Copy everything below into your AI assistant.

---

Add a project page for this GitHub repo. Use the `create-project` skill (`.cursor/skills/hugo-techie-create-project/` or `themes/hugo-techie-personal/agents/skills/create-project/SKILL.md`) and follow the zero-CLI contract in `AGENTS.md`.

**Repo URL:** `<paste URL>`

Please fetch from the GitHub API (`https://api.github.com/repos/<owner>/<repo>`) and the repo's README:

- **Title** — the repo's display name, or a nicer human name if the README has one.
- **Slug** — lowercased repo name with hyphens (this becomes `content/projects/<slug>.md`). If timeline entries already use a different slug in `project_links:`, use that instead and tell me.
- **Date** — repo's `created_at`, formatted `YYYY-MM-DD`.
- **`github_url`** — the canonical URL.
- **`website_url`** — the repo's `homepage` field, if set.
- **`focus_area`** — one short phrase you can back up from the README ("Application Security", "DevSecOps", "Android Security", …). Ask me if the README isn't clear.
- **`tags`** — 3–6 topics from the repo's GitHub topics + README.
- **TL;DR fields** (`tldr_description`, `tldr_best_for`, `tldr_key_features`) — each one line, paraphrased from the README.
- **Long-form body** — optional. Use the skill's "Content body template" structure (Overview / Key features / Technical implementation / Usage / Use cases / Future development). Only include what the README actually supports; leave sections out rather than inventing.

If the repo is archived (`archived: true` in the API) set `status: discontinued` and add a `discontinue_date`. If the repo is empty / private / 404s, stop and tell me.

Don't save an image unless I give you one — leave `featured_image` out. When done, run `hugo server -D` and show me `/projects/<slug>/`.
