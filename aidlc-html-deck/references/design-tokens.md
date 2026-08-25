# Design Tokens — AI-DLC HTML Deck

Every value here is already in `assets/deck-base.html`. This file explains **why**
each one is what it is, so a later session does not "improve" a token that was
chosen for a reason.

---

## 1. Where this system comes from

Two design systems exist in this repo, and they are not the same:

| | pptx decks | HTML decks + master reference |
|---|---|---|
| Source | `*/harness_common.py` · `in-action/aidlc_common.py` | `aidlc-master-draft-20260817.html` |
| Sans | Calibri (`harness_common.py:67`) | **Pretendard** (`:23`) |
| Mono | Consolas (`:69`) | **Geist Mono** (`:24`) |
| Ink | `MIDNIGHT #21295C` / `INK #1A1F36` (`:40,45`) | `--ink #191A1C` (`:17`) |
| Accent | `DEEP #065A82` / `GOLD #E8B14F` (`:38,42`) | semantic triad, below |

**This skill follows the HTML column.** The reasoning is that the master
reference document already established a considered HTML identity — semantic
color families, dark mode, a mono label face — and a deck that shares its
identity reads as one body of work. Calibri also has no hangul, so the pptx decks
already render Korean through an OS fallback; Pretendard makes the HTML path
deterministic instead.

Do **not** port the pptx palette into an HTML deck, and do not port these tokens
back into a pptx build script. The drift is intentional and documented here.

---

## 2. Fonts

```css
--sans:'Pretendard',system-ui,-apple-system,'Segoe UI',sans-serif;
--mono:'Geist Mono','SF Mono',ui-monospace,monospace;
```

Pretendard was chosen over Wanted Sans, SUIT, IBM Plex Sans KR and Noto Sans KR
on a rendered specimen at both 42px and 88px. Findings worth keeping:

- **Wanted Sans** is nearly indistinguishable from Pretendard in Korean at any
  size — not worth a swap.
- **SUIT Variable** does not pick up `font-weight:800` through its CDN CSS; titles
  come out visibly thin. Avoid unless you set `font-variation-settings` yourself.
- **IBM Plex Sans KR** is the only genuinely different option — wider, squarer
  counters, heavier strokes. If a deck ever needs to look distinct, change the
  **display** face to Plex and pair `--mono` with IBM Plex Mono. Its width costs
  you line breaks on long Korean titles.
- **Noto Sans KR** is the Korean equivalent of a purple gradient. Do not.

`--mono` is a **label face, not a code face.** Eyebrows, tags, page numbers,
axis labels, stat sources, and stage numbers are mono + uppercase +
`letter-spacing:.06–.14em`. This is the deck's typographic signature and it is
what keeps a slide from looking like a generated bullet list. Code blocks also
use it, but that is the minority use.

> **Geist Mono has no hangul and no `→`.** Text set in `--mono` containing either
> silently falls back to a system face. **The fix is in the token, not in each
> call site** — Pretendard sits inside the mono chain:
>
> ```css
> --mono:'Geist Mono','SF Mono','Pretendard',ui-monospace,monospace;
> ```
>
> A mono label then renders Latin and digits in Geist Mono and hangul in
> Pretendard, which is the mix we want, on two families only. This
> replaced a round of per-element patching: on the primer deck the chips, section
> labels and footer had all fallen back to `AppleSDGothicNeo`, and one `→` in an
> eyebrow reached `Menlo-Bold`.
>
> `.eyebrow.ko` (sans, 13px/700, no tracking) survives as a **style** choice, not
> a correctness one — uppercase and wide tracking read badly on hangul. Labels
> stay Latin by default. For a row label mixing both, split it:
> `<span class="sn">3.1</span> 설계`, only the number in mono.
>
> Still absent from **both** families: `▸` (U+25B8) falls to `.SFNS`. The original
> pptx decks use it as a lead-in marker, so draw it in CSS instead:
>
> ```css
> .tri{display:inline-block;width:0;height:0;border-left:5px solid currentColor;
>   border-top:3.5px solid transparent;border-bottom:3.5px solid transparent;}
> ```
>
> Verified present in Pretendard: `→ ↓ ↑ · ① ②` and the box-drawing set
> `├ └ ─` used for directory trees. Circled numerals are legible at body size but
> mush at 9.5px chip size — use plain digits there.
>
> **Pretendard has no hanja.** A single `有` in a label pulled
> `AppleSDGothicNeo-SemiBold` into the render. The pptx decks use hanja shorthand
> (`有` / `無`) freely; spell it in hangul instead when porting.

AWS's brand face (Amazon Ember) has effectively no hangul coverage, so it is not
a candidate for a Korean deck.

---

## 3. Color

### Surfaces and ink

| Token | Hex | Use |
|---|---|---|
| `--paper` | `#FBFBF9` | slide background |
| `--sheet` | `#FFFFFF` | a card lifted off the paper |
| `--sunk` | `#F5F4F1` | a recessed well — table headers, chips |
| `--rule` | `#E7E5E0` | 1px dividers |
| `--ink` | `#191A1C` | titles, primary text |
| `--ink-2` | `#4C4E52` | body, subtitles |
| `--ink-3` | `#686A6F` | captions |
| `--ink-4` | `#8A8C91` | labels, footers — the quietest readable level |

### The semantic triad

This is the important part. Four families, each with `fill` / `ink` / `line` /
`solid`, and each **means something** in AI-DLC:

| Family | Meaning | fill · ink · line · solid |
|---|---|---|
| `--human-*` | a human decides or reviews | `#D7FBE5` · `#12813C` · `#96E4B4` · `#17B457` |
| `--agent-*` | an AI agent does the work | `#E2ECFF` · `#1E4FD8` · `#AEC7FB` · `#2F6BF6` |
| `--engine-*` | the harness / engine itself | `#ECEBF4` · `#575569` · `#D2CFE0` · `#837FA0` |
| `--warn-*` | a risk, limit, or "cannot" | `#FFEAD3` · `#C2410C` · `#FBCB98` · `#F97316` |

**Never use these decoratively.** A card is blue because an agent owns that step,
not because blue looked good there. Once the audience learns the mapping on slide
3 it carries them through the whole deck for free — and that is worth more than
any palette variety. `--violet` / `--pink` / `--teal` exist for accents on filled
shapes and section numbering only.

Contrast: `ink` on `fill` clears WCAG AA for body text in all four families.
`solid` is for filled shapes with white text, not for text on paper.

---

## 4. Type scale

Slide type is not document type. These sizes assume a 1280×720 canvas viewed at
distance.

| Role | Size / weight | Notes |
|---|---|---|
| Section number | 96–132px / 800 | `line-height:.85`, `letter-spacing:-.04em` |
| Statement | 64–88px / 800 | one sentence per slide, `-.035em` |
| Slide title | 44px / 800 | `-.03em`, `line-height:1.15` |
| Big stat | 56–72px / 800 | mono or sans; pair with a small mono source line |
| Card title | 22px / 700 | |
| Subtitle | 19px / 400 | `--ink-2`, `line-height:1.55` |
| Body | 17px / 400 | floor for anything the audience must read |
| Caption | 13.5px / 400 | `--ink-3` |
| Label (mono) | 12px / 600 | uppercase, `.14em` |
| Micro (mono) | 10.5px / 600 | uppercase, `.06em` — footers, sources |

**13.5px is the floor.** Anything smaller is decoration that survives only
because nobody in the room can read it, which means it should be cut instead.

Korean text always gets `word-break:keep-all` — it is set globally on `body` and
must not be overridden. Without it Korean breaks mid-word and the layout looks
broken to a Korean reader in a way that is invisible to a Latin-only check.

---

## 5. Geometry

숫자로 고정된 캔버스는 없다(인쇄 폐지). 아래 값은 **1280px 폭 화면에서의 기준선**이고,
`clamp()` 로 1440·1920 까지 함께 커지게 쓴다. 1280 × 720 은 pptx 덱(`harness_common.py`
의 `SW`/`SH`)과 같은 비율이라, 두 채널을 한 세션에서 섞어도 스케일이 튀지 않는다.

| Zone | Value |
|---|---|
| Side padding | `--pad` 64px |
| Title zone top | `--top` 56px |
| Content region | y 176 → 640 |
| Footer baseline | 26px from the bottom |
| Grid | `repeat(12, 1fr)` with `gap: 24px` inside the 1152px content width |
| Card radius | 14px · pill `9999px` · chip 8px |
| Hairline | `1px solid var(--rule)` or the family's `line` |

Shadows come from `--shadow`, which is a three-layer stack. Use it or use
nothing; a single flat `box-shadow` looks cheap next to it.

`--ease: cubic-bezier(.32,.72,0,1)` is the only easing curve in the deck. It
decelerates hard, which reads as deliberate rather than bouncy.

---

## 6. Dark mode

The master reference document ships a full `[data-theme='dark']` token set
(`aidlc-master-draft-20260817.html:29-38`). The deck base **does not** wire it up,
because a deck is presented once under known conditions. If a dark deck is ever
needed, copy that block verbatim rather than inventing new dark values — and note
the two places it is not enough: `.band` sets its background to `var(--ink)` (so
dark flips it to light-on-light) and `.chip.v` hardcodes a lavender fill.

---

## 7. 화면이 기준이다 (2026-08-22)

PDF 는 폐지됐다. 배포와 발표가 모두 브라우저이므로 **"브라우저에서 맞으면 맞다"** 가
이제 기준이다. 인쇄에서만 깨지던 항목들(gradient text clip, print block 이 강제하던
`[data-step]` opacity)은 더 이상 제약이 아니다 — 그래서 `-webkit-background-clip:text`
그라데이션 숫자를 마음껏 쓸 수 있고, 실제로 `.secdiv`·`.hn` 이 그렇게 쓴다.

남은 실측 주의사항은 하나다. `deck_screens.py` 로 찍을 때 Chrome 은
`--virtual-time-budget` 없이는 **webfont 가 내려오기 전에 캡처**해서 한글이 시스템
폰트로 대체된 그림을 낸다(Chrome 151 실측). 스크립트가 항상 그 플래그를 주므로
Chrome 을 손으로 부르지 말 것.

| Effect | 상태 | 메모 |
|---|---|---|
| Korean text in `--mono` | 여전히 주의 | Geist Mono 에 한글이 없다 — `--mono` 체인에 Pretendard 가 들어 있어야 Menlo 로 안 떨어진다 |
| `box-shadow` | 문제 없음 | `--shadow` 3단 스택을 그대로 쓸 것 |
| gradient `background-clip:text` | 문제 없음 | 인쇄에서만 깨졌던 것이라 이제 자유롭게 쓴다 |

Anything else new and clever gets a render check before it ships. The rule is not
"avoid effects", it is "look at the page you are handing over".
