# tool-specific-tips — write-bio-page

## Source of bio text

Good sources, in priority order:

1. **User-provided text** (pasted into chat, CV PDF, Notion doc).
2. **LinkedIn "About" section** — usually the user's preferred self-description.
3. **Personal site / About page** — second-best canonical source.
4. **GitHub `bio`** — one-liner; seed for `subtitle:` or a first sentence.
5. **Conference speaker pages** — often have a ready-to-use paragraph.

Never synthesise a bio from thin air. If you have nothing, ask the user to paste something.

## Cursor / Claude Code / ChatGPT / Aider

All assistants handle this identically — there's nothing tool-specific:

- Use your web fetch tool on the URL(s) the user gives you.
- Pull the relevant paragraph(s) verbatim.
- Offer the user an edit: shorten, change voice (1st ↔ 3rd person), reorder paragraphs.
- Write `content/bio.md`.

## Placeholder image generation

If the user wants a silhouette placeholder while they find a real headshot:

```sh
# Simple SVG placeholder — no external tools needed.
cat > assets/images/bio/placeholder.svg <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" fill="#ccc">
  <rect width="400" height="400" fill="#e5e7eb"/>
  <circle cx="200" cy="150" r="70" fill="#9ca3af"/>
  <path d="M60 400 Q60 260 200 260 Q340 260 340 400 Z" fill="#9ca3af"/>
</svg>
SVG
```

Reference as `file: "images/bio/placeholder.svg"` in frontmatter.

## Third-person vs first-person

Default to third person for speaker / event-submission bios. Keep the `long_bio:` in the same person as `short_bio:` — mixing reads weird. If the user writes in first person and has no preference, convert only when producing a speaker-specific variant in chat; don't silently change the canonical bio.
