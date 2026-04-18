---
name: hugo-techie-create-interest
description: Add a personal interest page under content/interests/ on a hugo-techie-personal site. Minimal frontmatter, free-form body. Use when the user wants to document a hobby, personal interest, or any topic that doesn't fit the timeline/project/gadget schema.
---

# create-interest

Add a personal interest page under `content/interests/`.

## When to use

- *"Add an interest page about fediverse / coins / anime / whatever."*
- *"I want a short page about this hobby."*

## Filename

Lowercase hyphens: `fediverse.md`, `coin-collection.md`, `anime.md`. Write to `content/interests/<slug>.md`.

## Frontmatter

```yaml
---
title: "Interest Name"
draft: false
activity: ""
event: ""
media: ""
featured_image: ""
focus: ""
---
```

Most fields are empty because interests don't fit the activity/event schema used elsewhere. They're present for layout consistency.

## Body structure

```markdown
Brief introduction to why this matters to you.

# Section 1

Content.

# Section 2

More content.

# References

- [Link 1](https://...)
- [Link 2](https://...)
```

## Procedure

1. Ask the user for a brief intro paragraph (their voice, not yours).
2. Write the file. Minimal body is fine; interests evolve over time.
3. `hugo server -D` and verify.

## Helper files

- [`tool-specific-tips.md`](tool-specific-tips.md)

## Common pitfalls

- **Writing the intro paragraph yourself.** Interests are personal — quote or ask. Don't paraphrase generic encyclopedia text.
