---
name: hugo-techie-create-gadget
description: Add a device / gadget review page under content/gadget/ on a hugo-techie-personal site. Uses the theme's capital-T Title frontmatter quirk, handles status markers (planned, archived, discontinued), and follows the standard Commentary / Technical specs / Useful applications / Tips / References body structure. Use when the user asks to add a gadget, device review, hardware notes, or tool kit page.
---

# create-gadget

Add a gadget / device review page under `content/gadget/`.

## When to use

- *"Add my Flipper Zero."*
- *"Review my new device."*
- *"Document this Raspberry Pi setup."*

## Filename

Lowercase, hyphens: `flipper-zero.md`, `raspberry-pi-5.md`, `yubikey.md`.

Write to `content/gadget/<slug>.md`.

## Frontmatter — note the capital `T` in `Title`

Unlike every other content type, gadget frontmatter uses **`Title`** (capital T) and **`Gadget`** (capital G). This quirk is intentional (historical). Use the theme's convention exactly:

```yaml
---
Title: "Device Name"
Type: gadget
Gadget: "Device Name"
draft: false
status: discontinued   # optional: discontinued | archived | planned
---
```

### Status values

| Status         | Meaning |
|----------------|---------|
| (no status)    | Currently in use. |
| `planned`      | Owned but not yet in active use. Renders with a `📋 Planned Device` banner. |
| `archived`     | Kept for archival, no longer in use. Renders with a `⚠️ Archived Device` banner. |
| `discontinued` | Same as archived semantically; appears in "Discontinued" sections. |

## Body structure

```markdown
This page is for "Device Name"

# Commentary

Personal notes, first-impressions, day-to-day experience.

# Technical specs

- **Display:** ...
- **Processor:** ...
- **Storage:** ...
- **Connectivity:** ...
- **Power:** ...

# Useful applications

## Category 1
- App 1
- App 2

## Category 2
- App 3

# Tips and tricks

- Tip 1
- Tip 2

# Reference material

- [Official site](https://...)
- [Community wiki](https://...)
```

## Procedure

1. Confirm device name + status with the user.
2. Write `content/gadget/<slug>.md` with the frontmatter + body skeleton. Leave sections empty if the user hasn't filled them — they'll add content over time. Hugo renders empty sections fine.
3. `hugo server -D`, verify `/gadget/<slug>/`.

## Helper files

- [`tool-specific-tips.md`](tool-specific-tips.md)

## Common pitfalls

- **Wrong case on `Title:`.** Must be capital-T — the gadget layout template reads this specific key. `title:` (lowercase) will render blank.
- **Forgetting `Type: gadget`.** Required for the listing page to include it.
