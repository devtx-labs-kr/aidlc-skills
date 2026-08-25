# Slide Patterns

Nine archetypes that cover an AI-DLC deck. The classes they use —
`.wrap` `.grid` `.card` `.chip` `.kv` `.tbl` `.band` `.foot` — all ship in
`assets/deck-base.html`, so copy the `<section>` and nothing else.

They exist for one reason: **the default failure mode of a generated deck is
title-plus-bullets, repeated forty times.** If a slide does not fit one of these
patterns, that is a signal to reconsider what the slide is for — not a signal to
invent a tenth pattern.

> **`data-step` is not part of the default.** The snippets below show it in a few
> places to document the mechanism, but a normal slide ships with none: it
> renders whole and one arrow-press moves to the next slide. Use steps only when
> the order of arrival is itself the lesson — see pattern 6, which is the only
> place in this repo that earns it. Strip `data-step` from any pattern you copy
> unless you can say what the sequence teaches.

---

## Shared scaffolding

Nothing to copy — the skeleton already defines it. What matters is the shape of
a section in the flow model: everything lives in normal document flow inside one
`.wrap`, and vertical rhythm comes from `margin-top`, never from an absolute
`top:` coordinate.

```html
<section class="sec" data-notes="발표자가 읽을 산문.">
  <div class="wrap">
    <div class="tag"><b>1.1</b> 섹션 이름</div>      <!-- or .eyebrow on a divider -->
    <h1 class="c-title" style="margin-top:15px;">슬라이드 제목</h1>
    <p class="sub">한 줄 부제.</p>

    <!-- content: .grid / .card / .kv / .tbl / .band -->
  </div>
  <div class="foot"><span>그룹 이름</span><span class="pg"></span></div>
</section>
```

Three things the index rail depends on, so they are not optional:

| | Why |
|---|---|
| every section has an `<h1>` | it becomes the rail's label |
| the footer's **first** span is the group name | it becomes the rail's category header, so keep it identical across a run of sections |
| `.pg` stays empty | the runtime stamps `n / total` into it |

Title sizes: `.cover-title` for a deck cover, `.s-title` for section dividers and
statements, `.c-title` for content sections. `.nodiv` on a section suppresses the
hairline rule above it — use it on covers and dividers.

---

## 1 · Cover

The only slide allowed to be mostly empty. One claim, one date, no bullets.

```html
<section class="sec nodiv" data-notes="인사와 오늘 다룰 범위를 한 문장으로.">
  <div class="wrap">
    <div class="eyebrow" style="color:var(--agent-ink);">AI-DLC Workflows v2</div>
    <h1 style="font-size:76px;font-weight:800;letter-spacing:-.04em;line-height:1.08;margin-top:22px;">
      하네스가 무엇을<br>바꾸는가
    </h1>
    <p class="sub" style="font-size:21px;max-width:760px;margin-top:26px;">
      32단계 워크플로를 14개 에이전트가 나눠 수행할 때, 사람은 어디에서 결정하는가.
    </p>
  </div>
  <div class="foot"><span>DevTX · 2026-08</span><span class="pg"></span></div>
</section>
```

---

## 2 · Section divider

A large number is the one place decoration is allowed, because it gives the
audience a position in the deck.

> **Gradient-filling it is fine now.** `-webkit-background-clip:text` broke only
> in the PDF (Chrome 151: the glyph clip partially failed and the raw gradient
> rectangle leaked through the bottom of a `2`). PDF was retired on 2026-08-22, so
> a gradient numeral is available again — `aidlc-master-draft-20260817.html` uses
> exactly that for its `.sd-num` part numbers. A solid `--agent-solid` numeral is
> still the safe default when the divider sits on a tinted background.

```html
<section class="sec" data-notes="여기서 큰 흐름이 한 번 끊긴다.">
  <div class="wrap" style="display:flex;align-items:center;gap:44px;">
    <div style="font-family:var(--mono);font-size:132px;font-weight:800;line-height:.85;
                letter-spacing:-.04em;color:var(--agent-solid);">02</div>
    <div>
      <div class="eyebrow">Section</div>
      <h1 style="font-size:52px;font-weight:800;letter-spacing:-.03em;margin-top:12px;">
        컨스트럭션 루프
      </h1>
      <p class="sub" style="max-width:620px;">계획 → 구현 → 검증이 한 바퀴 도는 구간.</p>
    </div>
  </div>
  <div class="foot"><span>AI-DLC v2</span><span class="pg"></span></div>
</section>
```

---

## 3 · Statement

One sentence at 64–88px. Use where a bulleted slide would bury the point. At most
three of these in a deck, or they stop landing.

```html
<section class="sec" data-notes="여기서 한 번 멈춘다. 이 문장이 이 장의 전부다.">
  <div class="wrap" style="bottom:0;display:grid;align-content:center;">
    <div class="eyebrow" data-step="1">The actual constraint</div>
    <p style="font-size:72px;font-weight:800;letter-spacing:-.035em;line-height:1.2;max-width:1000px;margin-top:20px;">
      병목은 코드 생성이 아니라<br><span style="color:var(--agent-ink);">검증</span>이다.
    </p>
  </div>
  <div class="foot"><span>AI-DLC v2</span><span class="pg"></span></div>
</section>
```

---

## 4 · Split — text beside a visual

The workhorse. Left column carries the argument, right column carries the thing
being argued about. Never two text columns; that is one slide pretending to be two.

```html
<section class="sec" data-notes="왼쪽을 먼저 말하고, 오른쪽 그림으로 확인시킨다.">
  <div class="wrap">
    <div class="eyebrow">INCEPTION</div>
    <h1 class="s-title" style="margin-top:14px;">사람이 남는 자리</h1>
    <div class="grid" style="margin-top:clamp(26px,2.8vw,40px);">
      <div style="grid-column:span 5;align-self:center;">
        <p style="font-size:19px;color:var(--ink-2);line-height:1.65;">
          에이전트가 초안을 내고, 사람은 <b style="color:var(--ink);">받아들일지</b>를 결정한다.
        </p>
        <div style="margin-top:22px;display:flex;flex-direction:column;gap:11px;">
          <div class="chip h">Human · 승인</div>
          <div class="chip a">Agent · 초안</div>
          <div class="chip e">Engine · 상태</div>
        </div>
      </div>
      <div style="grid-column:span 7;" class="card">
        <!-- 그림·차트·표·코드 중 하나. 빈 박스로 두지 말 것. -->
      </div>
    </div>
  </div>
  <div class="foot"><span>AI-DLC v2</span><span class="pg"></span></div>
</section>
```

---

## 5 · Semantic card row

Three or four cards, each coloured by **who acts**. This is where the audience
learns the colour mapping, so put it early.

> Cards take their natural height and sit centred in the band
> (`align-content:center`). If the copy is short the slide reads airy — that is
> correct. **Do not** reach for `grid-auto-rows:1fr` to fill the band: it was
> tried and rendered three tall cards with two-thirds of each interior empty,
> which looks broken rather than spacious. If a card row feels thin, the fix is
> more content or fewer cards, not taller boxes.

```html
<section class="sec" data-notes="색이 곧 주체다. 여기서 한 번 명시하면 이후엔 설명이 필요 없다.">
  <div class="wrap">
    <div class="eyebrow">Who acts</div>
    <h1 class="s-title" style="margin-top:14px;">세 주체의 역할</h1>
    <div class="grid" style="margin-top:clamp(26px,2.8vw,40px);">
      <div class="card" style="grid-column:span 4;border-color:var(--human-line);background:var(--human-fill);">
        <div class="chip h" data-step="1">Human</div>
        <h3 style="font-size:22px;font-weight:700;margin-top:14px;">결정한다</h3>
        <p style="font-size:16px;color:var(--ink-2);margin-top:9px;line-height:1.6;">
          의도를 정하고 결과를 받아들인다.
        </p>
      </div>
      <div class="card" style="grid-column:span 4;border-color:var(--agent-line);background:var(--agent-fill);">
        <div class="chip a" data-step="2">Agent</div>
        <h3 style="font-size:22px;font-weight:700;margin-top:14px;">수행한다</h3>
        <p style="font-size:16px;color:var(--ink-2);margin-top:9px;line-height:1.6;">
          14개 에이전트가 단계를 나눠 맡는다.
        </p>
      </div>
      <div class="card" style="grid-column:span 4;border-color:var(--engine-line);background:var(--engine-fill);">
        <div class="chip e" data-step="3">Engine</div>
        <h3 style="font-size:22px;font-weight:700;margin-top:14px;">기억한다</h3>
        <p style="font-size:16px;color:var(--ink-2);margin-top:9px;line-height:1.6;">
          상태와 산출물을 단계 사이에 보존한다.
        </p>
      </div>
    </div>
  </div>
  <div class="foot"><span>AI-DLC v2</span><span class="pg"></span></div>
</section>
```

---

## 6 · Pipeline / stage flow

Stages as a chain. `data-step` walks the audience along it one hop at a time —
this is the pattern that cost 1,628 lines of hand-authored `<p:timing>` XML in the
pptx decks and costs one attribute here.

```html
<section class="sec" data-notes="한 단계씩 눌러 가며 설명한다.">
  <div class="wrap">
    <div class="eyebrow">Construction loop</div>
    <h1 class="s-title" style="margin-top:14px;">한 바퀴</h1>
  </div>
  <div class="wrap" style="display:flex;align-items:center;gap:0;">
    <!-- 노드 4개 + 화살표 3개. n번째 노드는 data-step="n". -->
    <div class="card" data-step="1" style="flex:1;text-align:center;padding:20px 14px;">
      <div style="font-family:var(--mono);font-size:11px;font-weight:700;color:var(--agent-ink);">01</div>
      <div style="font-size:18px;font-weight:700;margin-top:7px;">계획</div>
    </div>
    <div data-step="2" style="width:38px;height:1px;background:var(--rule);position:relative;flex:none;">
      <span style="position:absolute;right:-1px;top:-3px;border-left:7px solid var(--ink-4);
                   border-top:3.5px solid transparent;border-bottom:3.5px solid transparent;"></span>
    </div>
    <div class="card" data-step="2" style="flex:1;text-align:center;padding:20px 14px;">
      <div style="font-family:var(--mono);font-size:11px;font-weight:700;color:var(--agent-ink);">02</div>
      <div style="font-size:18px;font-weight:700;margin-top:7px;">구현</div>
    </div>
    <!-- … 반복 … -->
  </div>
  <div class="foot"><span>AI-DLC v2</span><span class="pg"></span></div>
</section>
```

---

## 7 · Comparison

For v1-vs-v2 style contrasts. The two sides must be visually asymmetric — equal
weight tells the audience the two options are equally good, which is usually not
the claim.

```html
<section class="sec" data-notes="왼쪽은 배경, 오른쪽이 논점이다.">
  <div class="wrap">
    <div class="eyebrow">v1 → v2</div>
    <h1 class="s-title" style="margin-top:14px;">무엇이 달라졌나</h1>
    <div class="grid" style="margin-top:clamp(26px,2.8vw,40px);">
      <div style="grid-column:span 5;padding:24px 26px;border-radius:14px;background:var(--sunk);">
        <div class="chip e">v1</div>
        <ul style="margin-top:16px;padding-left:19px;font-size:16.5px;color:var(--ink-3);line-height:1.85;">
          <li>단계가 암묵적이다</li>
          <li>상태가 대화에만 있다</li>
        </ul>
      </div>
      <div style="grid-column:span 7;" class="card">
        <div class="chip a">v2</div>
        <ul style="margin-top:16px;padding-left:19px;font-size:17.5px;color:var(--ink);line-height:1.85;">
          <li><b>32단계</b>가 명시된다</li>
          <li>상태가 <b>파일</b>로 남는다</li>
        </ul>
      </div>
    </div>
  </div>
  <div class="foot"><span>AI-DLC v2</span><span class="pg"></span></div>
</section>
```

---

## 8 · Stat row

Numbers need a source line, in mono, at 10.5px. A number without a source is a
claim the presenter has to defend from memory.

```html
<section class="sec" data-notes="숫자는 실측 출처를 함께 말한다.">
  <div class="wrap">
    <div class="eyebrow">실측</div>
    <h1 class="s-title" style="margin-top:14px;">규모</h1>
    <div class="grid" style="margin-top:clamp(26px,2.8vw,40px);">
      <div style="grid-column:span 4;">
        <div style="font-size:68px;font-weight:800;letter-spacing:-.035em;line-height:1;">33</div>
        <div style="font-size:16px;color:var(--ink-2);margin-top:8px;">단계</div>
        <div style="font-family:var(--mono);font-size:10.5px;color:var(--ink-4);margin-top:10px;
                    text-transform:uppercase;letter-spacing:.06em;">Engine 2.6.2 · 실측</div>
      </div>
      <!-- 2~3개 더. 4개를 넘기면 아무 숫자도 기억되지 않는다. -->
    </div>
  </div>
  <div class="foot"><span>AI-DLC v2</span><span class="pg"></span></div>
</section>
```

---

## 9 · Stepped list

The one acceptable bulleted slide: each item arrives on a click, so the audience
reads with the presenter instead of ahead of them. Six items maximum.

```html
<section class="sec" data-notes="한 항목씩 눌러 가며 말한다. 미리 다 보여주면 청중이 앞서 읽는다.">
  <div class="wrap">
    <div class="eyebrow">정리</div>
    <h1 class="s-title" style="margin-top:14px;">남는 세 가지</h1>
  </div>
  <div class="wrap" style="display:flex;flex-direction:column;justify-content:center;gap:20px;max-width:940px;">
    <div data-step="1" style="display:flex;gap:18px;align-items:baseline;">
      <span style="font-family:var(--mono);font-size:13px;font-weight:700;color:var(--agent-ink);flex:none;">01</span>
      <span style="font-size:23px;line-height:1.5;">병목은 검증으로 옮겨간다.</span>
    </div>
    <div data-step="2" style="display:flex;gap:18px;align-items:baseline;">
      <span style="font-family:var(--mono);font-size:13px;font-weight:700;color:var(--agent-ink);flex:none;">02</span>
      <span style="font-size:23px;line-height:1.5;">상태를 파일로 남기면 재현된다.</span>
    </div>
  </div>
  <div class="foot"><span>AI-DLC v2</span><span class="pg"></span></div>
</section>
```

---

## Anti-patterns

| Do not | Because |
|---|---|
| Title + 8 bullets, no visual | The failure mode this whole file exists to prevent |
| A colour chosen for looks | The triad encodes who acts; decorative use destroys it |
| Text below 13.5px | Nobody in the room can read it, so it is not content |
| Italics | Repo rule — emphasis is bold, colour, or size |
| Two text columns | One slide pretending to be two |
| More than 4 stats on a slide | None of them get remembered |
| `data-step` on every element | Stepping everything is the same as stepping nothing |
| An empty `.card` placeholder | Ship the visual or drop the slide |
| Korean text in `.eyebrow` | Geist Mono has no hangul — use `.eyebrow.ko`, or keep Pretendard in the `--mono` chain so it does not fall to Menlo |
