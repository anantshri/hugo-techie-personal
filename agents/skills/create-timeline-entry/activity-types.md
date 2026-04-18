# activity-types

These are the exact `activity:` values recognised by the theme. **Use the value in the left column verbatim.** Do not invent new ones.

| `activity:`     | What it's for                                                                          | Typical examples |
|-----------------|----------------------------------------------------------------------------------------|------------------|
| `talk`          | Conference presentation, keynote, meetup talk                                          | DefCon talk, Null meetup, lightning talk |
| `training`      | Training workshop, multi-day course, bootcamp                                          | BlackHat training, corporate workshop |
| `tool`          | Tool demo / launch                                                                     | Arsenal demo, tool release session |
| `panel`         | Panel discussion (participant or moderator)                                            | Conference panel, industry roundtable |
| `discussion`    | One-on-one discussion, podcast episode, interview                                      | Podcast guest, AMA, fireside chat |
| `whitepaper`    | Published research paper / whitepaper                                                  | Arxiv paper, CTF writeup with formal paper |
| `article`       | Article written for an external publication                                            | Guest blog post, magazine article, Medium contribution |
| `quote`         | User was quoted or referenced in someone else's article                                | Press mention, analyst report citation |
| `recognition`   | Award, honor, recognition received                                                     | Industry award, best-paper award, community recognition |
| `ctf`           | CTF participation or placement                                                         | Team placement, CTF win, challenge authored |
| `curator`       | Event curation / organising / track-chairing                                           | Conference track lead, program committee, CFP reviewer |

## How to pick when it's ambiguous

- **Talk vs training:** training has hands-on labs and lasts hours-to-days; talk is a session (30–60 min). If it's billed as "workshop" but you couldn't touch anything and it was 60 min, call it `talk`.
- **Discussion vs article:** if the user *spoke* (podcast, video interview, recorded chat), it's `discussion`. If they *wrote* something published elsewhere, it's `article`.
- **Article vs quote:** `article` = user is the author. `quote` = someone else's article mentions the user.
- **Recognition vs curator:** recognition = award received. Curator = organisational role.
- **Tool vs talk:** demo sessions at conferences (e.g. BlackHat Arsenal) are `tool` even though they look like a talk; they're categorised separately on listing pages.

## When none fit

Ask the user. Don't shove it into `talk` as a catch-all.

Adding a new activity type to the theme is a code change — the templates check activity icons and list-layout groupings by these exact strings. Out of scope for this skill.
