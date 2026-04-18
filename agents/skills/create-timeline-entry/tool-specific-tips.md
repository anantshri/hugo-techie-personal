# tool-specific-tips — create-timeline-entry

## Cursor

- **Fetch Open Graph tags** from a URL the user gave you:

  ```sh
  curl -sSL "<url>" | rg -o '<meta[^>]+property="og:(title|image|description)"[^>]+content="[^"]+"' -r '$0' | head
  ```

  Parse out the title / image / description for `related_links` / `featured_image`.

- **Shell permissions:** `curl` needs `required_permissions: ["full_network"]` when running against external hosts in sandboxed mode.
- **Image download:** save hero images under `static/images/` so they land at the absolute `/images/<name>.jpg` URL the frontmatter expects. Use `curl -o static/images/<name>.<ext> <url>`.
- **Live preview:** keep `hugo server -D` running in a background terminal; Cursor's terminal file will show the URL and reload on save.

## Claude Code

- Use `WebFetch` on the source URL with a prompt like *"extract og:title, og:image, og:description"* — avoids shelling out.
- `Bash` to download images: `curl -fsSL <url> -o static/images/<name>.jpg`.
- `Write` for the new `content/timeline/<name>.md`. `Edit` for tweaking existing entries.
- If the user hands you a file path for the hero image (e.g. already on their disk), `cp` it into `static/images/` rather than re-downloading.

## ChatGPT (browsing)

- `browser.open_url(<url>)` to fetch the page; the rendered text usually contains the title and description inline. For `og:image`, look for `<meta property="og:image"` in the source.
- Use the `python` tool for file writes; no direct file tool.
- Images you can't download directly: describe to the user where to paste / drop the file, then write the frontmatter referencing what they'll save.

## Aider

- `/web <url>` to fetch, or `/run curl -sSL <url>` when `/web` isn't configured.
- `/run hugo server -D` runs in foreground; open a second terminal or background it with `/run hugo server -D &`.
- Aider's diff-edit style works well for timeline files — small, single-file, append-only edits.

## All assistants

- **Never hotlink hero images** — download the file into `static/images/` and reference locally. Hotlinking breaks when the source site rearranges, and leaks referer headers.
- **Image naming:** lowercase, hyphens, descriptive: `blackhat-eu-2025-training.jpg`. Not `IMG_1234.jpg`.
- **Check for duplicates** before writing. If `content/timeline/<slug>.md` exists, ask whether to update or create a sibling entry.
- **After writing,** run `hugo --printPathWarnings` once to catch collisions — duplicate filenames in different cases trip this up on case-insensitive filesystems (macOS).
