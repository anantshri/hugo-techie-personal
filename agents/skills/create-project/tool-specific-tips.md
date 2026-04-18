# tool-specific-tips — create-project

## GitHub API extraction (all assistants)

When the user points you at a GitHub URL, pull structured data once rather than scraping the rendered page:

```sh
curl -sSL "https://api.github.com/repos/<owner>/<repo>" | jq '{
  name, description, created_at, pushed_at, archived,
  homepage, html_url, stargazers_count, language,
  topics
}'
```

Map to frontmatter:

| API field          | Frontmatter                              |
|--------------------|------------------------------------------|
| `name`             | `title` (with human title-casing)        |
| `description`      | `tldr_description`                       |
| `created_at`       | `date` (first 10 chars, `YYYY-MM-DD`)    |
| `archived == true` | `status: discontinued` + `discontinue_date` from `pushed_at` |
| `homepage`         | `website_url`                            |
| `html_url`         | `github_url`                             |
| `language`         | one of the `tags` (lowercase)            |
| `topics`           | merge into `tags`                        |

For a richer description, grab the README:

```sh
curl -sSL "https://raw.githubusercontent.com/<owner>/<repo>/HEAD/README.md" > /tmp/readme.md
```

Summarise into `tldr_*` fields; reserve the long-form body for anything you can't compress.

## Cursor

- `WebFetch` on `https://api.github.com/repos/...` returns JSON cleanly.
- For README, `WebFetch` on the `raw.githubusercontent.com` URL.
- Use `GITHUB_TOKEN` if it's in env to avoid the 60-req/hour anonymous limit.

## Claude Code / ChatGPT / Aider

- Same `curl` / API approach; adapt to each assistant's shell tool.
- ChatGPT's `python` tool can use `requests` directly.

## Image discovery

- GitHub social preview: `https://opengraph.githubassets.com/<random>/<owner>/<repo>` — decent fallback hero.
- Check for a `logo.png` / `docs/logo.png` in the repo root via:
  `curl -sSL "https://api.github.com/repos/<owner>/<repo>/contents/" | jq '.[] | select(.name | test("logo")) | .download_url'`
- Download to `static/images/projects/<slug>.png` and reference locally.
