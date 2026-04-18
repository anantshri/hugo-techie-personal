# interview-questions (Mode C — interactive interview)

Use this after the research phase, when the user has chosen **Mode C** and you're walking them through findings. Ask in this order. Skip any section that turned up nothing in `discoveries.yaml`.

Keep turns short. Quote what you found and ask yes / edit / skip. Don't dump all findings in one message.

---

## Block 1 — Identity (≤ 3 turns)

1. "I'll show you what I have. First, your display name and tagline — I have:
   > **Jane Doe** — *Security Researcher & Trainer*
   OK as-is, or would you like to change either?"

2. "Profile picture — I don't have one. Options:
   (a) paste a URL or drop a file, (b) I generate a placeholder SVG, (c) skip for now.
   Which?"

3. "Social links — include which of these?
   - GitHub: https://github.com/janedoe
   - LinkedIn: https://linkedin.com/in/janedoe
   - Mastodon: https://infosec.exchange/@janedoe
   - Email: jane@example.com (public on GitHub — want me to hide it?)"

Write `content/_index.md` and any profile-pic setting after this block.

## Block 2 — Bio (1–2 turns)

4. "Here's a **short bio** I drafted from your GitHub bio and LinkedIn headline:
   > <quote>
   Approve as-is? Edit? Replace?"

5. "And a **long bio** assembled from <N> sources:
   > <quote>
   Approve? Edit? I can also regenerate from specific sources if you'd rather."

Write `content/bio.md` after this block.

## Block 3 — Focus areas (1 turn)

6. "Based on your top projects and talks, your primary focus areas look like:
   `appsec`, `fuzzing`, `cloud-security`.
   Keep all? Add? Drop?"

These become the default `focus:` tags used when creating subsequent entries and the labels in `[taxonomies]`.

## Block 4 — Projects (one turn per project, batched)

7. "I found **12 projects**. I'll show them in batches of 4. Reply with any mix of:
   - `1:include`
   - `2:drop`
   - `3:edit desc=...`
   - `4:mark-discontinued`

   **Batch 1 of 3**:
   1. **CoolProject** — <desc> — 214★ — `go`, `security`
      https://github.com/janedoe/coolproject
   2. **Fuzzkit** — ...
   3. ...
   4. ..."

After each batch: write the included projects to `content/projects/<slug>.md` via `../create-project/SKILL.md`.

## Block 5 — Timeline (batches of 5)

8. "I found **18 timeline entries** — talks, trainings, panels. Batches of 5.
   Reply `N:ok`, `N:drop`, `N:edit field=value`, or `N:needs date=YYYY-MM-DD` for entries missing a date.

   **Batch 1 of 4**:
   1. [talk] 2023-08-11 — *Hacking the Impossible* @ DefCon 31 (Las Vegas, USA)
      Video: https://youtube.com/...
      Slides: https://speakerdeck.com/...
   2. [training] 2022-09-02 — *Binary Analysis 101* @ Nullcon Goa (India)
      ...
   ..."

After each batch: write via `../create-timeline-entry/SKILL.md`. If a `slides_url` is a downloadable PDF, offer to host it locally via `../create-slide-deck/SKILL.md` (ask per entry).

## Block 6 — Badges (1 turn)

9. "I found a Credly profile at `credly.com/users/janedoe` with 7 badges.
   - Hook up the `{{< credly-badges >}}` shortcode + add a `/badges/` page? (y/n)
   - Any other platforms (Accredible, Bugcrowd, HackerOne, Badgr)?"

If yes, run `../set-up-badges/SKILL.md`.

## Block 7 — Home page polish (1 turn)

10. "Home page — I'll show what I'm about to write:
    ```
    <preview of content/_index.md>
    ```
    Good? Edit the intro paragraph? Change `home_layout`?"

## Block 8 — Deploy preference (1 turn, optional)

11. "Where do you want to deploy this? (a) GitHub Pages, (b) Netlify, (c) Cloudflare Pages, (d) a VPS, (e) I'll decide later.
    If (a)–(c) I can scaffold the config now; (d) I can write a `deploy.sh`."

If answered, run `../deploy-site/SKILL.md`.

## Wrap-up

12. Run `hugo server -D`, report the URL, summarise what was created + what's still `draft: true`, and give the user the three-sentence cheat sheet from `SKILL.md` Step 6.
