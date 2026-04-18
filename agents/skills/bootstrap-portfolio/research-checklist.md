# research-checklist

Sources to query, in priority order, when bootstrapping a portfolio. For each source: what you're looking for, what to extract, and what to do with it.

If you have no web-fetch tool, **skip the source and note that it was skipped** in `discoveries.yaml` so the user knows what to paste manually.

---

## 1. GitHub (almost always the richest starting point)

**Endpoint:** `https://api.github.com/users/<handle>` and `https://api.github.com/users/<handle>/repos?per_page=100&sort=updated`

Use `curl`:

```sh
curl -sSL "https://api.github.com/users/<handle>" | jq .
curl -sSL "https://api.github.com/users/<handle>/repos?per_page=100&sort=updated" | jq .
```

Extract:

| Field (API)             | → `discoveries.yaml`                                  |
|-------------------------|-------------------------------------------------------|
| `name`                  | `person.name`                                         |
| `bio`                   | seed for `person.bio_short`                           |
| `company`               | optional, affiliation                                 |
| `location`              | `person.location`                                     |
| `blog`                  | candidate personal domain                             |
| `email` (public)        | `socials.email`                                       |
| `twitter_username`      | `socials.twitter`                                     |
| repo `name` + `description` + `html_url` + `language` + `topics` + `stargazers_count` + `archived` | one `projects[]` entry each |

**Filter repos**: keep the top ~15 by stars where `fork: false` and (`stargazers_count >= 10` or `archived: false`). Drop personal dotfiles / playground repos unless the user specifies.

For each kept repo, fetch the README for a longer description:

```sh
curl -sSL "https://raw.githubusercontent.com/<handle>/<repo>/HEAD/README.md" | head -c 8000
```

Archived repos → `status: discontinued`, `discontinue_date` from `pushed_at` if available.

## 2. LinkedIn (requires paste from user if no auth)

LinkedIn doesn't allow unauthenticated scraping. Two options:

- Ask the user to paste their public profile HTML or the "About" + "Experience" sections.
- Ask for a copy of their CV / résumé PDF.

Extract: professional headline, current role, `bio_long` narrative, talk invitations in "Experience" (events that list speaker credits).

## 3. Personal domain / blog

If GitHub's `blog` field or the user gave a domain, fetch:

```sh
curl -sSL "https://<domain>/" | head -c 20000
curl -sSL "https://<domain>/about" | head -c 20000 2>/dev/null
curl -sSL "https://<domain>/index.xml" 2>/dev/null   # RSS feed
```

Look for: bio, speaking list, research papers, blog post titles (for `focus_areas`).

## 4. Conference / speaker archives

Many security / tech communities publish speaker and session pages. For each of the user's talks mentioned anywhere, search for:

- `site:defcon.org <name>`
- `site:blackhat.com <name>`
- `site:nullcon.net <name>` / any conference they mention
- `site:cfp.<conference>.<tld> <name>`
- `site:speakerdeck.com <name>` (slides)
- `site:notist.co <name>` (slides)
- `site:youtube.com <name> <event>` (recordings)

Extract per session page:

- Session title → `timeline.title`
- Date → `timeline.date`
- Event / conference name → `timeline.event`
- Abstract → one-paragraph content body
- Video URL (YouTube/Vimeo) → `timeline.video_url`
- Slides URL → `timeline.slides_url`
- Venue city / country → `timeline.location`

Deduplicate by `event + year`. Prefer the canonical conference page over press coverage.

## 5. Google Scholar / research identifiers

For academic-leaning users:

- `https://scholar.google.com/citations?user=<id>` (if user provides Scholar ID)
- Search: `"<name>" site:arxiv.org`
- ORCID: `https://pub.orcid.org/v3.0/<orcid>/works` (if provided)

Each paper becomes a timeline entry with `activity: whitepaper`.

## 6. Mastodon / Bluesky / X

For each handle, pull the profile for:

- Display name, bio (cross-check `person.bio_short`).
- Pinned posts (often announce talks/projects → may enrich timeline).
- Verification links (`rel="me"` on Mastodon — add to `verify_1`, `verify_2` in home page frontmatter).

## 7. Credly / Accredible / Bugcrowd / HackerOne profiles

Only attempt if the user mentions certifications / bug bounty work.

- Credly: `https://www.credly.com/users/<handle>/badges` — grab badge names; the theme pulls the actual images via config.
- Bugcrowd: `https://bugcrowd.com/<handle>`
- HackerOne: `https://hackerone.com/<handle>`

If any platform is found, add `badges.<platform>: <handle>` to `discoveries.yaml`. The `set-up-badges` skill handles the rest.

## 8. Wikipedia / other biographies

Only for unusually public figures. `https://en.wikipedia.org/wiki/<Name>` — extract the lead section for `bio_long`, reference for factual dates.

## 9. Wayback Machine (fallback only)

If a known conference page is dead, try:

```sh
curl -sSL "https://archive.org/wayback/available?url=<url>" | jq .
```

Use the archived snapshot URL in `related_links` when citing a dead page; add the original to `defunk_links` (optional pattern — see AGENTS.md).

---

## Extraction ground rules

1. **Cite every finding.** In `discoveries.yaml`, every entry gets a `source_url` (or multiple `sources:`). The user needs to be able to click through and verify.
2. **Never guess dates.** If a source doesn't give a date, leave it empty and flag the entry `_needs_user: date`.
3. **Never invent quotes / bio text.** Paraphrase only when the source is clearly a machine-readable metadata field (e.g. GitHub `bio`). For prose biographies, quote verbatim or leave empty.
4. **Respect `robots.txt`.** Don't hammer sites — one request per page, max.
5. **Don't follow redirect chains past 3 hops.** Likely a login wall.
6. **Stop at ~30 timeline entries and ~15 projects.** More than that buries the signal; the user can curate up afterwards.

## Deliverable

At the end of research you should have a populated `plans/discoveries.yaml` and — if Mode A — a `plans/discoveries-summary.md` that renders as a short human-readable overview. Sample summary format:

```markdown
# Research summary for Jane Doe

Found: 12 projects, 18 talks, 2 certifications, LinkedIn profile, personal site, active Mastodon.
Confidence: high (most findings triangulated across ≥2 sources).

## Bio (short)
> From GitHub: Security researcher focused on binary analysis...
[+ LinkedIn says she's currently at Acme Corp since 2022.]

## Timeline (18 entries)
| Date       | Activity | Event          | Title                         | Source(s) |
| 2023-08-11 | talk     | DefCon 31      | Hacking the Impossible        | defcon.org, youtube |
| 2022-09-02 | training | Nullcon Goa    | Binary Analysis 101           | nullcon.net |
| ...        |          |                |                               |           |

## Projects (12)
...

## Items needing your input
- 3 talks with missing dates
- 2 projects with no description
- Email visibility: you'd like me to show `jane@example.com`? (from GitHub public email)
```
