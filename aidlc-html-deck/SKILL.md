---
name: aidlc-html-deck
description: Author AI-DLC presentation decks as a single self-contained HTML file, presented from a browser with arrow keys. Use whenever the work involves an HTML deck, web slides, or a browser-presented deck in this repo — "HTML 로 발표자료", "슬라이드 HTML", "덱을 HTML 로", "single-file HTML presentation" — and whenever an existing `*.html` deck in this repo is being edited or restyled. Covers the design tokens, the nine slide patterns, the animation model, and the headless-Chrome screen-verification pipeline. There is no PDF path (retired 2026-08-22). For `.pptx` decks use the pptx skill instead; the two paths do not mix.
---

# AI-DLC HTML Deck

This repo's second deck channel. The pptx decks are generated from python build
scripts; an HTML deck is different in one important way:

> **The `.html` file is the source, and it is committed.**

There is no build script and no generated artifact to gitignore. You edit the
deck directly, which is the whole reason this channel exists — a click-stepped
reveal is one `data-step` attribute here, versus the 1,628-line hand-authored
`<p:timing>` XML the pptx decks needed for a single animated slide
(`aidlc-v2/anim_stage_major_timing.xml`, injected by
`harness_common.py:458-476`).

**There is no PDF.** Retired 2026-08-22 by user decision — "PDF 에 대한 고려가
오히려 창의성을 방해한다". Both authoring and presenting happen in the browser, so
anything that only works on a screen (click-driven explorers, `<details>`,
ambient motion) is fair game: nothing has to survive a print.

What that buys, concretely: a single section can hold a 33-item board whose
detail pane swaps on click, so a list that used to need three slides needs one.
`../../../aidlc-master-draft-20260817.html` is the reference for those devices.

---

## Files in this skill

| File | Read it when |
|---|---|
| `assets/deck-base.html` | Starting a new deck — copy this, it is the working skeleton |
| `references/design-tokens.md` | Choosing any colour, size, or font |
| `references/slide-patterns.md` | Laying out any slide — nine copy-paste archetypes |
| `scripts/deck_screens.py` | Verifying — section count, per-section `<h1>`, screenshots, text dump |
| `scripts/inline_deck_images.py` | Handing the `.html` to someone outside the repo |

---

## Non-negotiables

1. **One self-contained `.html` file.** All CSS and JS inline. The only external
   requests are the two font CDNs in the token block. No frameworks, no build
   step, vanilla CSS and vanilla JS.
   Images may be authored as sibling files with a relative `src` — that resolves
   for presenting. But a relative `src` **fails silently** once the `.html`
   travels alone, so run `inline_deck_images.py` (base64, verified against an
   empty directory) before handing the file to anyone outside the repo.
2. **Flow on screen. One arrow press should still land on one screenful.** A
   section is `min-height:100vh` and grows with its content in normal document
   flow — short sections centre in the viewport (so there is no dead band under
   the last card), long ones get taller and the arrow key pages down inside them
   before advancing. Nothing is scaled to a fixed canvas, so any projector aspect
   gets a full-bleed page.
   With print gone there is **no hard height budget** — a section may exceed the
   viewport and nothing is clipped or lost. But a section taller than the screen
   costs the presenter an extra keypress inside that section, which breaks the
   "one press = one slide" rhythm. So keep a section to one screenful unless the
   content genuinely earns the scroll, and judge it from the screenshot
   (`deck_screens.py`), not from an arithmetic budget.
   Size type with `clamp()` and check both a 1440 laptop and a 1920 projector —
   `vw` differs between them.
   A precisely-plotted diagram whose grid coordinates are absolute is the one
   thing that may want a fixed canvas — but prefer making its columns fluid
   (`minmax(0,1fr)`) so it survives a narrow window, which is what section 41 of
   `aidlc-v2/aidlc-v2.html` does.
3. **Korean is the default output language.** An English edition only on explicit
   request.
4. **No italics.** Emphasis is bold, colour, or size. (Repo rule.)
5. **Every slide carries a visual element, or you state why it does not.**
   Title-plus-bullets is the failure mode of generated decks.
6. **Speaker notes are prose for the presenter**, in `data-notes` on the
   `<section>`. Write them with the same care as the slide body — they are what
   the presenter actually reads.
7. **Never claim a deck is done without a screenshot you actually looked at.**
   `deck_screens.py` produces them; reading the PNG is the part that counts.

---

## Workflow

### 1 · Establish the brief

Before writing markup, pin down: audience, duration, source material, and whether
this replaces or accompanies an existing pptx deck. If the user gave a document to
adapt, read it first.

Slide budget — roughly one slide per 40 seconds of speaking:

| Duration | Slides |
|---|---|
| 10 min | 14–18 |
| 20 min | 26–32 |
| 30 min | 38–46 |
| 60 min | 70–85 |

### 2 · Outline, then stop

Produce a numbered outline: slide number, which pattern from
`references/slide-patterns.md`, the title, and one line of content. Present it and
**wait for approval.** Do not generate 40 slides of markup against an unconfirmed
structure — that is the expensive mistake in this workflow.

### 3 · Build

Copy `assets/deck-base.html` to the deck's directory, then replace its three
sample sections with your own `<section class="sec">` elements. The skeleton
already carries the tokens, the flow layout, the index rail and the presenter
runtime — you add sections and nothing else.

- Read `references/design-tokens.md` before picking any value. Every colour goes
  through a token; the `--human-*` / `--agent-*` / `--engine-*` / `--warn-*`
  families encode **who acts** and must never be used decoratively.
- Read `references/slide-patterns.md` and use the patterns. If a slide fits none
  of the nine, that is a signal the slide's purpose is unclear.
- **The left index rail ships in the skeleton — keep it.** Arrow keys cannot
  cross a long deck, and hunting for section 46 by pressing right forty times is
  not navigation. `i` toggles it; fullscreen drops it automatically via
  the `--navw` variable, which also offsets `#deck` and the progress bar. Delete
  it only for a deck of a handful of sections.
  The index is **derived from the DOM, never from a hand-kept array**: the group
  name comes from each section's `.foot > span:first-child` and the label from
  its `<h1>`, so it cannot drift out of sync as sections are added or reordered.
  Two consequences for authoring: keep the footer's first span **identical
  across a run of sections** (it is what groups them), and give every section an
  `<h1>`.
- **Animation is off by default. A slide shows whole, at once.** Do not add
  `data-step` to reveal a slide's own components one arrow-press at a time — one
  press means one slide. Drip-feeding cards and bullets is a tic, not a
  technique: it makes the presenter click through their own layout and buys the
  audience nothing they would not get from seeing the finished slide.
- Reach for `data-step` only when **the sequence itself is the content** and you
  have shown that a static picture cannot say it. **No slide in this repo uses it
  today.** The Construction stage-major grid was the one holdout, and it lost the
  argument: at step 0 the grid was empty, so before the first press the slide said
  nothing at all. It now carries the same order statically — a pass number per
  row, arrows that are always drawn, a gate badge at the end of each row. Try that
  first; the harness is still here if you genuinely need it, but "the order is the
  content" is a claim to be tested against a numbered static diagram, not a
  licence. When in doubt, no steps.

### 4 · Verify on screen

```bash
uv run .claude/skills/aidlc-html-deck/scripts/deck_screens.py <deck>.html --expect <N> --text-only
uv run .claude/skills/aidlc-html-deck/scripts/deck_screens.py <deck>.html --only 20,21,22
uv run .claude/skills/aidlc-html-deck/scripts/deck_screens.py <deck>.html --expect <N>
```

Pick the line by what you need. `--text-only` skips the screenshots and returns in
about four seconds — use it for the structural checks after any edit. `--only` for
the sections you actually intend to look at. The bare form shoots every section: it
runs several Chromes at once (`--jobs`, default = half the CPUs, max 6) but a
67-section deck still takes about **two minutes**, so give the call a generous
timeout. Serially it used to exceed four minutes and get killed.

Four things, in order of how quietly they fail:

- **section count** vs `--expect` — the first thing that drifts when sections are
  added or removed.
- **every section has an `<h1>`** — the index rail is derived from it, so a
  section without one loses its name in the rail.
- **a screenshot per section** (`<deck>-png/s-NN.png`, gitignored). Chrome is
  always given `--virtual-time-budget`; without it the capture happens before the
  webfont lands and the PNG shows a system Korean face (Chrome 151, measured).
  Do not call Chrome by hand.
- **a text dump** (`<deck>-png/text.txt`) — per-section, tags stripped, taken from
  the **rendered DOM**. Diff it across an edit and "I only changed the form"
  becomes a checkable claim instead of an assertion. This is the single most useful
  check when restyling.
  It has to be the DOM, not the source: whenever a slide is painted from a data
  array — and this deck keeps moving that way, since one array is how a fact stops
  drifting across slides — a source-level dump simply does not contain it. Pulling
  stage names into `SC_STAGES` cost the source dump 51 lines; switching to the DOM
  recovered those and picked up 267 more that had never been visible. Use
  `--no-browser` only when you specifically want the source view.
  One caveat worth knowing: stripping tags with a naive `<[^>]+>` cuts at the
  first `>` **inside a quoted attribute** and spills the rest of the attribute
  into the body — `data-notes="… phases/<phase>.md …"` did exactly that on three
  sections of `aidlc-v2.html`. The script's `TAG` pattern skips quoted runs, so a
  dump that looks like it contains stray speaker-note prose now means a real
  problem rather than a known artefact. Do not simplify that pattern.

Iterate with `--only`, and run the whole deck before committing.

### 5 · Look at the renders

**Read the PNGs.** Overflowing text, collided elements, a card that turned out
empty, and a section that runs past one screenful are invisible in the HTML and
obvious in the screenshot. There is no automated height check — the picture is
the check.

Do not spawn visual-QA subagents by reflex — read the images yourself. Delegate
only when the user asks or the section count genuinely warrants it.

### 6 · Report and commit

State the slide count, the verification result, and anything you left out. The
endpoint of the task is a local commit on `main`; never push without approval.

---

## Editing an existing HTML deck

Same discipline as the pptx decks, adapted:

1. Run `deck_screens.py` **before** the change and keep the run (`text.txt` plus
   the PNGs of the sections you are about to touch).
2. Make the surgical change — only what was asked.
3. Re-run and diff: the section count moved by exactly the intended amount, the
   `text.txt` diff is exactly the intended segments, and the PNGs of untouched
   sections are byte-identical (`md5`).
   ⚠️ If the section **count** changed, every footer stamp (`n / total`) changed
   with it, so no PNG is byte-identical. Compare the body region only — crop off
   the bottom ~9% before hashing.
4. Read the screenshot of any section you grew. Nothing gets clipped now that
   print is gone, but a section that outgrew the screen costs the presenter an
   extra keypress inside it.

Match the deck's existing style even where you would have done it differently.
Flag cross-deck drift when you find it; do not fix it silently.

---

## What this skill will not do

- ❌ Convert an HTML deck to `.pptx`. The screenshot-into-pptx bridge exists in
  the wild, but it produces a deck of flat images with no editable text, which is
  worse than either honest format. If pptx is required, build it with the pptx
  skill from a python script.
- ❌ Port the pptx palette (`DEEP`, `GOLD`, `MIDNIGHT`, Calibri) into an HTML
  deck, or these tokens back into a build script. The two systems are
  deliberately separate — see `references/design-tokens.md` §1.
- ❌ Reintroduce a print path. `@page`, `@media print`, a 16:9 page and a fixed
  body budget were all retired on 2026-08-22 — the reason was that designing
  around the print page was suppressing what the screen can do. Do not add them
  back "just in case"; ask first.
- ❌ Touch any `__backup/` folder.
