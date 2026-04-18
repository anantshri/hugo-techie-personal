# tool-specific-tips — deploy-site

## Cursor

- To deploy to a VPS, the agent needs SSH credentials. `Shell` with `required_permissions: ["full_network"]` plus whatever credential the user has configured in `~/.ssh/`.
- For first-time GitHub Actions setup, prefer generating the workflow YAML and committing it — avoid the GitHub web UI flow where possible since the user wants zero CLI (committing the file is CLI-y but happens via `git add` which the agent runs).
- Use `gh pr create` (GitHub CLI) only if the user has `gh` authenticated.

## Claude Code

- Same patterns. Claude's `Bash` handles `rsync`, `ssh`, `git push` cleanly.
- For Netlify / Cloudflare, usually the only task is writing the config file + asking the user to click "Connect repo" in the UI. There's no CLI-first path short of Netlify CLI (`netlify deploy`); offer that as an option if the user wants full automation.

## ChatGPT (browsing / code interpreter)

- No `ssh` / `rsync` in the sandbox. Can't deploy from inside ChatGPT.
- Produce the workflow / config files and tell the user to paste them into their repo.
- For GitHub Pages, optionally use `gh` via the user's terminal — describe the steps.

## Aider

- `/run hugo --minify`, `/run git push`, etc. Handles end-to-end deploy locally.
- Aider's `/run` is synchronous — long uploads block the session. Use `nohup … &` or a background terminal.

## All assistants

### DNS / custom domains

Before deploying, ask the user: "Do you have a domain? What's the DNS provider?"

- **Custom domain + GitHub Pages:** write `static/CNAME` with the domain; user adds an `ALIAS`/`ANAME`/`A` record at the DNS provider pointing at GitHub Pages IPs.
- **Custom domain + Netlify / CF Pages:** add custom domain in platform UI; user adds CNAME to platform hostname.
- **Custom domain + VPS:** `A` record to the VPS IP; make sure the nginx server block has `server_name <domain>` and a cert (Let's Encrypt via `certbot`).

Don't set up DNS automatically — wait for the user to confirm the records are in place, then test.

### HTTPS certificates (VPS only)

```sh
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

Certbot runs interactively. If the agent is in zero-CLI mode, walk the user through the three prompts verbally (email, TOS, redirect HTTP→HTTPS — always say yes).

### Post-deploy smoke test

After every deploy, fetch:

```sh
curl -sI https://yourdomain.com/ | head -1        # expect 200
curl -sI https://yourdomain.com/timeline/ | head -1   # expect 200
curl -sI https://yourdomain.com/slides/ | head -1     # expect 200 (if slides exist)
```

Report results to the user. Any 404 means `public/` didn't ship that section — usually a `draft: true` that shouldn't be, or a missing `_index.md`.
