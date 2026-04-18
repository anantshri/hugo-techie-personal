# tool-specific-tips — create-slide-deck

## Cursor

- **PDF input:** the user drops the PDF into chat (Cursor handles the upload) or gives you a file path on disk. Read the path with `Read`; for dropped files, Cursor exposes a temp path you can `cp` from.
- **Shell permissions:** `process-slides.sh` runs `pdftoppm`, `cwebp`, `magick`, and `shasum`. Only local binaries — no network access needed, so the default sandbox works. Pass `required_permissions: ["full_network"]` only if `brew install` / `apt-get install` steps need the network.
- **Long-running:** `process-slides.sh` is 5–30 seconds per deck. Run with default `block_until_ms: 30000` and `Await` if it exceeds.
- **Live preview:** keep `hugo server -D` in a background terminal — it picks up new slide pages without a restart.

## Claude Code

- `Bash` to run the scripts. `process-slides.sh` outputs progress lines; let it stream.
- Use `Edit` to tweak frontmatter after scaffolding — the template is close enough that usually you only fill in `title`, `date`, `conference`, `location`, and `timeline_entry`.
- If the user pastes a URL to a PDF (e.g. SpeakerDeck / conference site), download with `curl -fsSL <url> -o assets/slides/pdf_files/<slug>.pdf` before scaffolding.

## ChatGPT (browsing)

- For PDFs, the user uploads via the chat UI. Access via the `python` tool:

  ```python
  import shutil, os
  os.makedirs("assets/slides/pdf_files", exist_ok=True)
  shutil.copy("/mnt/data/<uploaded>.pdf", "assets/slides/pdf_files/<slug>.pdf")
  ```

- `process-slides.sh` needs `pdftoppm` / `cwebp` / `magick`; verify they're installed in the sandbox before running (they usually are in the code interpreter). If not, fall back to a pure-Python path: `pypdf` + `Pillow` + `webp` — but prefer the shipped shell script whenever possible for consistency.
- `hugo` itself is not available in ChatGPT's code interpreter. Tell the user you've generated the files and that they need to run `hugo server` locally (or ask them to paste the server's output for troubleshooting).

## Aider

- `/run ./themes/hugo-techie-personal/scripts/scaffold-slides.sh` then `/run ./themes/hugo-techie-personal/scripts/process-slides.sh`.
- Edit `content/slides/<slug>/index.md` via Aider's normal diff flow.
- If `process-slides.sh` fails with a missing binary, `/run brew install <pkg>` or `/run sudo apt-get install -y <pkg>` as appropriate.

## All assistants

- **Idempotency:** `process-slides.sh` compares the PDF SHA against `metadata.json`. If you replace the PDF, re-running regenerates images. If the script looks like it did nothing, the hash matched — pass no special flag; it's correct behaviour.
- **Dimensions:** the script caps images at 1920px wide. Hugo resizes them at build time to thumb (400px), medium (1024px), full (1920px) via `resources.Get` + `Resize`. Don't pre-generate multi-size WebPs; the theme does it for you.
- **`slides.pdf` in `static/`:** the script copies the PDF to `static/slides/<slug>/slides.pdf`. That's what the download button links to. Don't delete it.
- **Never edit `content/slides/<slug>/slides/metadata.json` by hand.** It's an output; the script owns it.
- **Adding `videos[]` after the fact:** just edit the frontmatter, no reprocessing needed. Same for `resources[]`, `timeline_entry`, `related_presentations`.
