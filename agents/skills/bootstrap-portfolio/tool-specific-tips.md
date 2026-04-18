# tool-specific-tips — bootstrap-portfolio

Notes for different AI assistants. Read the section that matches yours.

## Cursor

- **Web search:** use the `WebSearch` tool for queries like `site:defcon.org "Jane Doe"`. It returns summarised results with URLs.
- **Web fetch:** use `WebFetch` to pull a specific URL as Markdown. Cheaper than browsing when you already have the URL.
- **Live browser (when needed):** the `cursor-ide-browser` MCP can navigate pages that need JS execution (LinkedIn public views, some conference SPAs). Prefer `WebFetch` first; escalate to the browser only when the page is JS-only.
- **Shell:** `Shell` tool with `required_permissions: ["full_network"]` when running `curl` against the GitHub API.
- **Parallel:** multiple `WebFetch` calls can run in a single tool-call batch — do this for research to reduce latency.
- **Plan file:** write `plans/discoveries.yaml` with the `Write` tool. Keep it under git ignore? Check `.gitignore` first; if not, offer to add `plans/discoveries*.yaml` to `.gitignore` since it may contain email/social handles the user hasn't decided to publish yet.

## Claude Code

- **Web search:** use the `WebSearch` tool. Queries are plain English or `site:` operators.
- **Web fetch:** use `WebFetch` with the URL and a short extraction prompt.
- **Shell:** use `Bash` to run `curl https://api.github.com/...` and pipe through `jq`. Install `jq` with `brew install jq` if missing.
- **File writes:** use `Write` for new files, `Edit` (or `MultiEdit`) for targeted changes to existing config.
- **Parallelism:** batch tool calls in a single assistant turn when fetching multiple sources.

## ChatGPT (browsing / GPT-5 with tools)

- **Web:** the `browser.search` / `browser.open_url` tools. Results feed back as snippets — expand with `browser.open_url` when you need the full page.
- **Shell:** `python` tool is your only executor. Use `subprocess.run(["curl", "-sSL", url])` for HTTP that's friendlier than `requests` for sites that sniff user-agents, or use `requests` with a browser-like UA.
- **File writes:** through the `python` tool — `open(path, "w").write(...)`. No direct file-writing tool.
- **Rate limits:** the browse tool has a lower ceiling than Cursor's. Favor GitHub API (returns dense JSON in one call) over scraping HTML pages.

## Aider

- **Web search:** `/web <query>` if configured; otherwise `/run curl -sSL 'https://duckduckgo.com/html/?q=…'` and parse.
- **Web fetch:** `/web <url>` or `/run curl -sSL <url>`.
- **Shell:** `/run` with any command. `/run` + `curl` + `jq` handle most research.
- **Prompt discipline:** Aider sessions tend to be short — write `plans/discoveries.yaml` *first*, then do one bootstrap step per turn. Don't try to do everything in one chat turn.

## Any agent with only chat (no tools)

- Tell the user you cannot reach the web.
- Follow the **paste-URLs mode** described in `SKILL.md` Step 2.
- For each URL the user pastes, ask them to paste a specific snippet (GitHub JSON, talk abstract, speaker page HTML).
- Proceed through Block 1–8 of `interview-questions.md` using only user-provided data.
- Mark every derived entry with `_source: "user-pasted"` in `discoveries.yaml` so later runs can upgrade those entries.

## Agents with a sandboxed shell but no internet

- You can run `hugo`, `git`, and local scripts but not `curl`.
- Ask the user to paste the JSON / HTML you'd otherwise fetch. They can do this in <60 seconds per source — GitHub's public API responses are small and readable.
- Everything else in the skill works unchanged.

## Cross-cutting tips

- **Respect robots / terms:** don't attempt to log in, bypass captchas, or scrape rate-limited endpoints aggressively.
- **Attribution:** every finding in `discoveries.yaml` gets a `source_url`. Reproducibility matters — the user needs to verify what you wrote.
- **Caching:** if your agent supports it, cache the GitHub API response for 10 minutes. Re-running the skill during the same session shouldn't re-hit `api.github.com`.
- **Rate limits:** unauthenticated GitHub API = 60 requests/hour/IP. If the user has a `GITHUB_TOKEN` in their environment, use it (adds `Authorization: Bearer $GITHUB_TOKEN` header, bumps limit to 5000/hour).
