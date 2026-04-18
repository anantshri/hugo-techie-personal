# tool-specific-tips — configure-site

## Editing `config.toml` safely

TOML is strict about types and section order. A few guardrails regardless of assistant:

- Always do a targeted `StrReplace` / `Edit` on a single `[section]` at a time rather than rewriting the whole file.
- After edits, run `hugo --printPathWarnings --quiet` and check exit code. A TOML syntax error exits non-zero.
- If you need to rewrite large chunks, copy `themes/hugo-techie-personal/exampleSite/config.toml` over the current file, then port the user's previous values in — saves many nested-section mistakes.

## Cursor

- Prefer `StrReplace` on specific parameters. Use `replace_all` only for renames that are definitely unambiguous (e.g. `"https://oldsite.com"` → `"https://newsite.com"`).
- When the user asks "add a menu item", show them the resulting `[[menu.main]]` block for confirmation before writing.

## Claude Code

- `Edit` / `MultiEdit` with anchored `old_string` works well for TOML since section headers are unique.
- For structural changes (add a whole new block), read the section with `Read` first; then `Edit` to insert after a known anchor line (e.g. after `[params]`).

## ChatGPT

- `python` tool + the `tomllib` module (3.11+) for read-only introspection. For writes, prefer text manipulation — `tomli_w` is fine but can reorder keys which creates noisy diffs.

## Aider

- Aider's diff flow handles TOML edits naturally.

## All assistants: verifying

After any config change, run:

```sh
hugo --quiet 2>&1 | head -30
```

A clean run produces no output. Any error points to the offending line.
