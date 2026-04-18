---
name: hugo-techie-write-bio-page
description: Create or update the bio page (content/bio.md) using the theme's `layout: bio` — short_bio, long_bio, and a photos gallery with multi-size downloads. Use when the user asks to write / update / regenerate their bio, generate a speaker bio, or add headshots. Photos must go under assets/ (not static/) because the layout uses resources.Get.
---

# write-bio-page

Create or update the bio page (`content/bio.md`) using the theme's `bio` layout — a structured biography with short/long variants, a photos gallery, and one-click copy to clipboard in three formats (rendered, markdown, plain text).

## When to use

- *"Write my bio page."*
- *"Update my bio — here's the new short version."*
- *"Generate a bio I can use for conference submissions."*

## Filename

Always `content/bio.md` (single page, not a bundle).

## Frontmatter

```yaml
---
title: "Biography"
layout: bio
subtitle: "Your Professional Title"
short_bio: |
  One-paragraph biography suitable for conference programs and speaker
  introductions. Supports **Markdown**. Third person usually reads better
  for speaker bios.
long_bio: |
  Multi-paragraph narrative covering career arc, expertise, and
  achievements.

  Second paragraph with more detail.

  Third paragraph covering current focus.
photos:
  - file: "images/bio/headshot-formal.jpg"
    label: "Formal headshot"
  - file: "images/bio/headshot-casual.jpg"
    label: "Casual photo"
---

Optional additional prose rendered below both bio blocks (e.g. "Book me as a speaker via …").
```

## Photos

- Place files under `assets/images/bio/` (note: `assets/`, not `static/`). Hugo's `resources.Get` uses this to resize into Thumb / Medium / Large / Original download links at build time.
- Supported formats: JPG, PNG, WebP.
- `file:` paths are relative to `assets/`.

## Procedure

1. Ask the user for a short bio (1 paragraph, ≤ 100 words) and a long bio (3–5 paragraphs). Write in third person unless the user insists on first person.
2. If `bootstrap-portfolio` already produced `person.bio_short` / `person.bio_long` in `discoveries.yaml`, use those as the first draft and ask the user to confirm/edit.
3. Ask the user for at least one headshot. If they have no photo, offer to generate a placeholder SVG and skip the `photos:` block.
4. Write `content/bio.md`.
5. Verify `http://localhost:1313/bio/`: the page shows tabs (Rendered / Markdown / Plain text), a copy button, and the photos section with download links for each resized variant.

## When the user wants a bio for a specific venue

Speaker bios for different audiences differ. The `bio.md` page is the *canonical* source — venue-specific bios belong in the user's notes or submission system. If they ask for a variant:

1. Edit `short_bio:` if it's a global tweak.
2. For one-off submission blurbs, just produce the text in chat without writing it to the site.

## Helper files

- [`tool-specific-tips.md`](tool-specific-tips.md)

## Common pitfalls

- **Photos under `static/` don't work** — the bio layout uses `resources.Get`, which only reads from `assets/`. If the user dropped a photo into `static/images/`, `cp` it (or `ln -s`) into `assets/images/bio/`.
- **First person vs third.** Default to third for speaker contexts. Ask if unsure.
- **Writing the bio from thin air.** Never generate a résumé-style bio without source material. Paraphrase from LinkedIn / about page / user-provided text only.
