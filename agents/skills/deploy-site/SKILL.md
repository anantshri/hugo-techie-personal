---
name: hugo-techie-deploy-site
description: Deploy a hugo-techie-personal site to GitHub Pages (via Actions workflow or gh-pages branch), Netlify, Cloudflare Pages, or a plain VPS with nginx. Covers the baseURL-must-match gotcha, submodule checkout requirements, and an optional nginx rewrite for LinkedIn-URN URL flattening. Use when the user asks to publish, deploy, go live, or hook up hosting.
---

# deploy-site

Deploy a `hugo-techie-personal` site to a hosting target. Three common targets: GitHub Pages, Netlify / Cloudflare Pages, and a plain VPS with nginx.

## When to use

- *"Deploy this to GitHub Pages."*
- *"Set up Netlify."*
- *"Push to my VPS."*
- *"How do I publish this?"*

## Common first step — set `baseURL`

```toml
# config.toml
baseURL = "https://yourdomain.com"
```

If the oembed of self-hosted slides is to work in production, this **must** match the production URL. For local dev, override with `hugo server -b http://localhost:1313`.

## Target 1 — GitHub Pages

Three patterns; pick based on what the user wants:

### 1a. Deploy from `main` via GitHub Actions

Write `.github/workflows/deploy.yml`:

```yaml
name: Deploy Hugo site to Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive
          fetch-depth: 0
      - uses: peaceiris/actions-hugo@v3
        with:
          hugo-version: 'latest'
          extended: true
      - run: hugo --minify --gc
      - uses: actions/upload-pages-artifact@v3
        with:
          path: ./public

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

Enable in repo Settings → Pages → Source: GitHub Actions.

If on a custom domain, add a `static/CNAME` file with the domain on a single line.

### 1b. Deploy from `gh-pages` branch

Simpler but older:

```sh
hugo --minify
cd public && git init && git checkout -b gh-pages
git add -A && git commit -m "deploy"
git push -f git@github.com:<user>/<repo>.git gh-pages
```

Point Pages at the `gh-pages` branch.

### 1c. Project site (non-root URL)

If deploying to `https://<user>.github.io/<repo>/` instead of a custom domain, set `baseURL = "https://<user>.github.io/<repo>/"` (trailing slash matters).

## Target 2 — Netlify / Cloudflare Pages

Both work with the same config. Connect the repo via their UI, then:

- **Build command:** `hugo --minify`
- **Publish directory:** `public`
- **Environment variables:** `HUGO_VERSION=0.158.0` (or newer, ≥ 0.158.0)

For Cloudflare Pages, additionally set `HUGO_ENABLEGITINFO=true` if the theme uses git info.

For Netlify, optionally write `netlify.toml` at the site root:

```toml
[build]
  publish = "public"
  command = "hugo --minify"

[build.environment]
  HUGO_VERSION = "0.158.0"
```

## Target 3 — Plain VPS with nginx

Follow the pattern in the repo's `deploy.sh` (if present). Typical shape:

```sh
#!/usr/bin/env bash
set -euo pipefail

# Build
hugo --minify --gc --cleanDestinationDir

# Deploy
rsync -az --delete \
  --exclude '.DS_Store' \
  public/ user@yourserver.example.com:/var/www/yourdomain/

# Optional: invalidate any cache / reload nginx
ssh user@yourserver.example.com 'sudo systemctl reload nginx'
```

Recommended nginx server block:

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    root /var/www/yourdomain;
    index index.html;

    # Optional: pretty-URL flattening for LinkedIn / Facebook archive mirrors.
    # See AGENTS.md social-archive notes — the theme ships a JS-side fallback
    # in layouts/404.html, so this is optional.
    location ~ ^(/www\.linkedin\.com/.+):.+$ {
        rewrite ^(.*):(.*)$ $1/$2 permanent;
    }

    location / {
        try_files $uri $uri/ $uri.html =404;
    }

    # Cache-busting for versioned assets
    location ~* \.(css|js|woff2?|ttf|otf|png|jpg|jpeg|webp|svg|ico)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

## Procedure

1. Ask the user which target they want.
2. Fix `baseURL` in `config.toml` first — every target needs this.
3. Write the platform-specific file (workflow / netlify.toml / deploy.sh) per the target section above.
4. Build locally first to confirm the minified output is clean:
   ```sh
   hugo --minify
   ```
   Check exit code and look at `hugo --printPathWarnings` for any warnings.
5. Push / deploy.
6. Verify the public URL loads and at least one deep link works (e.g. `/timeline/`, `/slides/<slug>/`).

## Helper files

- [`tool-specific-tips.md`](tool-specific-tips.md)

## Common pitfalls

- **`baseURL` mismatch.** Self-hosted slide oembeds fetch `https://<baseURL>/slides/<slug>/oembed.json` at build time. If `baseURL` is wrong, Hugo fails with a GetRemote error.
- **Missing submodules on CI.** For GitHub Actions, `submodules: recursive` on the checkout step is required — otherwise the theme isn't cloned and the build fails.
- **`hugo` without `extended`.** Some asset processing needs extended. Always install the extended binary.
- **Large images in `static/`.** The theme resizes `assets/` files but copies `static/` verbatim. Optimise hero images before committing (e.g. WebP at ~80% quality).
- **CNAME clobbered by Pages deploys.** The `static/CNAME` approach survives `hugo --cleanDestinationDir`; putting the CNAME anywhere else may not.
