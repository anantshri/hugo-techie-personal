# tool-specific-tips — set-up-badges

## Secret handling for Badgr

The Badgr API token is the only secret this theme handles. Offer the user three options:

### Option 1 — env var + private config (recommended)

```toml
# config.toml (committed)
[params]
  badgr_username = "your-handle"
  badgr_api_token = ""
  badgr_image_dir = "images/BadgrBadges"
```

```toml
# config.private.toml (gitignored)
[params]
  badgr_api_token = "xxxxxxxxx"
```

```sh
# run Hugo with both configs merged
hugo --config config.toml,config.private.toml
```

Add `config.private.toml` to `.gitignore`:

```sh
echo "config.private.toml" >> .gitignore
```

### Option 2 — env var only, wired via build script

```sh
# Don't write the token to any tracked file.
export BADGR_TOKEN=xxxxxxxx
hugo --cleanDestinationDir -e production
```

…and use a `deploy.sh` / CI workflow that reads `$BADGR_TOKEN` and injects it into the config at build time.

### Option 3 — plain text in config.toml (private repo only)

Fine if the repo is private and never made public. Warn the user clearly.

## First-build latency

Each platform's shortcode fetches the API on first build. Typical times:

- Credly: 2–5 s per user (one call returns all badges).
- Accredible: 2–5 s.
- Bugcrowd / HackerOne: 1–2 s (single profile call).
- Badgr: varies; bulk fetch.

Subsequent builds use `data/` cache — sub-second. If the user complains about build time, check whether `static/<*_image_dir>/` is committed; if not, every CI build re-fetches.

## Cursor / Claude Code / ChatGPT / Aider

All assistants: the flow is identical. Edit `config.toml` → create `content/badges.md` → run `hugo server -D` → verify. Nothing tool-specific.

For local testing of the Credly API without a Hugo build:

```sh
curl -sSL "https://www.credly.com/users/<handle>/badges.json" | jq '.data | length'
```

If the response is `0`, the user either has no public badges or the username is wrong. Check by visiting `https://www.credly.com/users/<handle>` in a browser.
