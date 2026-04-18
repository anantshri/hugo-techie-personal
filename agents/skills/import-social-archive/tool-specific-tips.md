# tool-specific-tips — import-social-archive

## `uv` is mandatory

Workspace rule: **never** run `pip install`, `pip3 install`, `python3 -m pip install`, or `python3 -m venv`. Always `uv run --with <pkg> python3 …` or `uv venv`.

If `uv` isn't installed on the user's machine, install it first:

```sh
# macOS
brew install uv

# Linux / generic
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Cursor

- The importer commands print a lot. Run with default 30s timeout; if the takeout is large (> 1000 posts) the first-ever run may need `block_until_ms: 120000`.
- Use `Await` to poll if backgrounded.
- For the `--auto-publish --dry-run` preview, capture the last ~30 lines and summarise for the user — don't just paste the full log.

## Claude Code

- `Bash` with the full `uv run --with …` command. Claude handles long-running commands cleanly.
- After the import, use `Glob` to list new bundles: `content/archive/<platform>/**/index.md`.

## ChatGPT (browsing / code interpreter)

- The code interpreter has `uv` and Python; run importers directly.
- The `takeouts/` folder may need to be uploaded as a zip first. Use `shutil` to move it into place.
- Hugo is **not** available in the code interpreter. After importing, tell the user which bundles were created and ask them to run `hugo server` locally.

## Aider

- `/run uv run --with pyyaml python3 themes/hugo-techie-personal/scripts/import_twitter.py …`
- Edit `takeouts/auto-publish.yml` or `takeouts/exclude.yml` with normal Aider diffs.

## All assistants

### Before running

- Confirm with the user: "This will write N bundles to `content/archive/<platform>/`. Continue?" for first-time imports.
- If `takeouts/` isn't in `.gitignore`, add it: takeouts contain emails, private DMs, metadata — not for public repos.

### After running

- Run `hugo server -D` and visit `/archive/` — the theme has a browse page that lists all imported posts.
- Spot-check one bundle per platform for correct URL mirroring.
- If the user sees a LinkedIn URN URL "not found", the 404 handler at `layouts/404.html` should redirect; verify it's present.

### Re-running safely

- Re-runs are cheap (hash-based skip). Encourage the user to re-run monthly with a fresh takeout to pick up new posts.
- A post edited on-platform after export will NOT sync until the next takeout is downloaded.

### Sidecar file format

- `instagram-shortcode-map.json`, `facebook-url-map.json`, `linkedin-reshare-map.json` — see SKILL.md.
- `auto-publish.yml` — YAML; see SKILL.md for full schema.
- `exclude.yml` — YAML; any list format works (flat list or per-platform dict). Importer collects all string IDs.

### Policy tuning iteration

A typical tuning loop:

1. `--auto-publish --dry-run` → scan counts (`auto_publish=X/Y`).
2. Ratio too high (publishing noise)? Bump `min_longform_chars` to 320, `min_caption_chars` to 60.
3. Ratio too low (hiding real content)? Lower the thresholds or add more `own_domains` / `own_github_orgs`.
4. Re-dry-run. Iterate.
5. When satisfied, run without `--dry-run`.

Typical final ratios on real takeouts: 5–15% auto-published from X, 30–60% from LinkedIn (more long-form), 20–40% from Instagram (captioned photos).
