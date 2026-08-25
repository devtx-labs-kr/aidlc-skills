#!/usr/bin/env python3
"""deck_screens.py — HTML 덱을 화면 그대로 찍고 검사한다.

    uv run .claude/skills/aidlc-html-deck/scripts/deck_screens.py deck.html --text-only
    uv run .claude/skills/aidlc-html-deck/scripts/deck_screens.py deck.html --only 20,21,22
    uv run .claude/skills/aidlc-html-deck/scripts/deck_screens.py deck.html --expect 67
    uv run .claude/skills/aidlc-html-deck/scripts/deck_screens.py deck.html --jobs 9

**2026-08-22 부로 이 채널의 검증 하니스다.** 앞선 `deck_to_pdf.py`(페이지 수 ·
960×540pt · 폰트 임베드 · 장별 h1)를 대체한다 — PDF 를 영구히 접었기 때문이다
("PDF 에 대한 고려가 오히려 창의성을 방해한다"). 덱은 브라우저에서 방향키로
발표하고, 그래서 검증도 화면에서 한다.

하는 일

  1. **섹션 수** — `--expect` 와 대조. 장을 넣고 빼는 작업에서 제일 먼저 틀어진다.
  2. **장별 `<h1>`** — 없는 장을 잡는다. 왼쪽 인덱스 레일과 이 검사가 둘 다 h1 에
     의존하므로, h1 없는 장은 레일에서 이름이 사라진다.
  3. **장별 스크린샷** — `#N` 으로 이동해 뷰포트를 찍는다. 겹침·잘림·빈 카드는
     HTML 에서 안 보이고 렌더에서 보인다. **찍은 이미지는 사람이 본다** — 한 장이
     한 화면을 넘는지도 여기서 판단한다(방향키 1회 = 1장 감각의 기준).
  4. **추출 텍스트 덤프** — 태그를 걷어낸 장별 텍스트를 `.txt` 로 남긴다. 편집
     전후로 이 파일을 diff 하면 "형식만 바꿨다 / 내용도 바뀌었다"가 갈린다.
     🔴 **덤프는 렌더된 DOM 에서 뜬다**(`--dump-dom`, Chrome 1회 ≈ 3초). 소스에서
     뜨면 JS 가 그린 장이 통째로 빠지고, 이 덱은 사실을 배열 하나에 모으는 쪽으로
     가고 있어서 그 구멍이 커진다 — stage 이름을 `SC_STAGES` 로 모으자 소스 덤프가
     51줄을 잃었고, DOM 으로 바꾸니 그동안 안 보이던 267줄(scope 보드 · agent
     로스터 등)이 함께 잡혔다. 소스 기준이 필요하면 `--no-browser`.
     🔴 태그를 걷을 때 `<[^>]+>` 를 쓰면 **속성값 안의 `>` 에서 잘려** 나머지가
     본문으로 샌다(`data-notes="… phases/<phase>.md …"`). 이 덱에서 세 장이 실제로
     그랬다. 아래 `TAG` 가 인용 구간을 건너뛰므로 그 자리로 되돌리지 말 것.

왜 스크립트인가 — 하나가 조용히 틀어진다. `--virtual-time-budget` 없이 찍으면
webfont 가 내려오기 전에 캡처돼 한글이 시스템 폰트로 대체된 그림이 나온다(Chrome
151 실측). 이 스크립트는 항상 그 플래그를 준다.

장당 약 3.6초이고 Chrome 을 장마다 새로 띄운다. `--user-data-dir` 로 프로필을
재사용해 폰트 캐시를 살리려 해 봤지만 headless 가 그대로 멈춰 버려서(2026-08-22
실측) 쓰지 않는다. 대신 **여러 장을 동시에 찍는다**(`--jobs`, 기본 = CPU 절반 · 최대
6) — 직렬이던 때는 67장이 4분을 넘겨 호출 쪽 타임아웃에 걸려 죽었다. 로그는 병렬로
돌아도 장 번호 순으로 나오므로 그대로 diff 해도 된다.

⭐ 실측 (67장 · 11코어 macOS · 2026-08-22). **다시 벤치마크하지 말 것**:

    직렬        240초 초과 (죽었다)
    동시 5개    112초  · 장당 1.7초   ← 기본값
    동시 9개     98초  · 장당 1.5초

9개는 13% 만 빨라지는데 메모리는 장당 200~400MB 씩 더 쓴다 — 병목이 CPU 가 아니라
Chrome 기동과 폰트 로드라서 더 겹쳐도 수확이 줄어든다. 그래서 기본을 6 에서 올리지
않았다. **전장은 어차피 2분 가까이 걸리니 호출하는 쪽이 타임아웃을 넉넉히 줘야 한다.**
눈으로 몇 장만 볼 때는 `--only` 가 가장 빠르고, 구조만 볼 때는 `--text-only` 로
브라우저를 아예 건너뛴다(1초 미만).

`--budget` 은 줄이지 말 것 — 병렬로 돌리면 각 Chrome 이 더 느려지므로 폰트 대기를
깎으면 한글이 시스템 폰트로 대체된 그림이 나올 여지가 오히려 커진다.

stdlib 만 쓴다. Google Chrome 이 필요하다(poppler 는 이제 불필요).
"""
from __future__ import annotations

import argparse
import html as html_mod
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

COMMENT = re.compile(r"<!--.*?-->", re.S)

# 🔴 순진한 `<[^>]+>` 를 쓰면 안 된다. `>` 는 **인용된 속성값 안에도** 들어가고
# (`data-notes="… phases/<phase>.md …"`), 그러면 그 `>` 에서 태그가 끝난 줄 알고
# 속성값의 나머지를 본문 텍스트로 흘린다. 이 덱에서 실제로 세 장이 그랬다 —
# aidlc/ 레이아웃 · knowledge 쓰는 순서 · memory 티어. 렌더는 정상인데 덤프만
# 오염되므로, 덤프를 믿고 "본문에 이상한 문자열이 있다"고 판단하면 오진한다.
# 그래서 태그 이름 뒤부터는 `비인용 구간`과 `완전히 인용된 문자열`을 번갈아 먹는다.
TAG = re.compile(r"""<[a-zA-Z!/?][^>"']*(?:(?:"[^"]*"|'[^']*')[^>"']*)*>""")

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome",
    "chromium",
]


def find_chrome() -> str:
    for c in CHROME_CANDIDATES:
        if Path(c).exists() or shutil.which(c):
            return c
    sys.exit("Chrome 을 찾지 못했다. CHROME 환경변수로 경로를 지정하라.")


def squash(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def sections(src: str) -> list[str]:
    """`<main>` 안의 `<section class="sec …">` 본문을 등장 순서대로."""
    start = src.find("<main")
    body = src[start:] if start >= 0 else src
    out, pos = [], 0
    while True:
        i = body.find('<section class="sec', pos)
        if i < 0:
            return out
        j = body.index("</section>", i)
        out.append(body[i:j])
        pos = j


def title_of(sec: str) -> str:
    m = re.search(r"<h1\b[^>]*>(.*?)</h1>", sec, re.S)
    if not m:
        return ""
    return squash(html_mod.unescape(TAG.sub(" ", m.group(1))))


def text_of(sec: str) -> str:
    t = re.sub(r"<(style|script)\b.*?</\1>", " ", sec, flags=re.S)
    t = COMMENT.sub(" ", t)          # 저작용 주석은 본문이 아니다
    t = TAG.sub("\n", t)
    t = html_mod.unescape(t)
    return "\n".join(ln for ln in (squash(x) for x in t.splitlines()) if ln)


def dump_dom(chrome: str, html: Path, budget: int) -> str | None:
    """렌더된 DOM 을 한 번 떠 온다. 실패하면 None.

    덤프를 소스에서 뜨면 **JS 가 그린 장이 통째로 빠진다.** 이 덱은 사실을 배열
    하나에 모으는 쪽으로 가고 있어서(scope 보드 · agent 로스터 · Operation 4장 ·
    phase 표), 소스만 보는 덤프는 "형식만 바꿨다"를 점점 못 지킨다. 실측으로 stage
    이름을 SC_STAGES 로 모으자 덤프가 51줄을 잃었다 — 그래서 화면 기준으로 뜬다.
    한 번만 부르므로 3초쯤이고, 장마다 띄우는 스크린샷과 달리 곱해지지 않는다.
    """
    try:
        r = subprocess.run([
            chrome, "--headless", "--disable-gpu",
            f"--virtual-time-budget={budget}",
            "--dump-dom", html.as_uri(),
        ], capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return None
    return r.stdout if r.stdout.strip() else None


def shoot(chrome: str, html: Path, n: int, png: Path,
          width: int, height: int, budget: int) -> str | None:
    """한 장을 찍는다. 성공이면 None, 실패면 사람이 읽을 이유 문자열."""
    png.unlink(missing_ok=True)
    try:
        subprocess.run([
            chrome, "--headless", "--disable-gpu", "--hide-scrollbars",
            f"--window-size={width},{height}",
            f"--virtual-time-budget={budget}",
            f"--screenshot={png}", f"{html.as_uri()}#{n}",
        ], capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return "Chrome 이 120초 안에 끝나지 않았다"
    # 4KB 미만은 사실상 빈 프레임이다 — headless 가 캡처 타이밍을 놓쳤거나 장이 정말 비었다.
    if not png.exists() or png.stat().st_size < 4000:
        return f"빈 프레임 ({png.name})"
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("html", type=Path)
    # 기본 출력이 `<stem>-png/` 인 것은 `.gitignore` 의 `*-png/` 규칙에 걸리게 하려는
    # 것이다 — 스크린샷은 산출물이므로 추적하지 않는다.
    ap.add_argument("--out", type=Path, help="기본값: <html>-png/")
    ap.add_argument("--expect", type=int, help="기대 섹션 수 — 불일치면 실패")
    ap.add_argument("--only", help="찍을 장 번호(1-based) 쉼표 목록. 생략하면 전부")
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--budget", type=int, default=8000,
                    help="webfont 대기 ms (기본 8000). 줄이지 말 것.")
    ap.add_argument("--text-only", action="store_true",
                    help="스크린샷을 건너뛰고 검사 + 텍스트 덤프만 (Chrome 1회 ≈ 3초)")
    ap.add_argument("--no-browser", action="store_true",
                    help="Chrome 을 아예 안 쓴다 — 덤프가 소스 기준이라 JS 가 그린 장이 빠진다")
    ap.add_argument("--jobs", type=int, default=0,
                    help="동시에 띄울 Chrome 수 (기본 = CPU 절반, 최대 6)")
    a = ap.parse_args()

    html = a.html.resolve()
    if not html.exists():
        sys.exit(f"없는 파일: {html}")
    src = html.read_text(encoding="utf-8")
    secs = sections(src)
    out = (a.out or html.with_name(html.stem + "-png")).resolve()
    out.mkdir(parents=True, exist_ok=True)

    ok = True

    # ── 1. 섹션 수 ────────────────────────────────────────────────────────────
    print(f"  sections  {len(secs)}" + (f"  (기대 {a.expect})" if a.expect else ""))
    if a.expect and len(secs) != a.expect:
        print(f"            ✗ 기대 {a.expect} 와 다르다")
        ok = False

    # ── 2. 장별 h1 ────────────────────────────────────────────────────────────
    missing = [i + 1 for i, s in enumerate(secs) if not title_of(s)]
    if missing:
        print(f"  titles    ✗ h1 없는 장: {missing}")
        ok = False
    else:
        print(f"  titles    ✓ {len(secs)}장 모두 h1 있음")

    # ── 4. 텍스트 덤프 (편집 전후 diff 용) ────────────────────────────────────
    # 기본은 **렌더된 DOM** 이다. 소스 기준으로 뜨면 JS 가 그린 장이 빠진다.
    dsecs, where = secs, "소스"
    if not a.no_browser:
        dom = dump_dom(find_chrome(), html, a.budget)
        if dom is None:
            print("  text      ⚠️ DOM 을 못 떴다 — 소스 기준으로 뜬다")
        else:
            dsecs, where = sections(dom), "화면"
            if len(dsecs) != len(secs):
                # JS 가 장을 더하거나 지운다는 뜻이다. 이 덱에 그런 코드는 없어야 한다.
                print(f"  text      ✗ DOM 섹션 {len(dsecs)} ≠ 소스 {len(secs)}")
                ok = False

    dump = out / "text.txt"
    with dump.open("w", encoding="utf-8") as f:
        for i, s in enumerate(dsecs, 1):
            f.write(f"=== {i:02d} · {title_of(s) or '(제목 없음)'}\n")
            f.write(text_of(s) + "\n\n")
    rel = dump.relative_to(Path.cwd()) if dump.is_relative_to(Path.cwd()) else dump
    print(f"  text      → {rel}  ({where} 기준)")

    # `--no-browser` 는 이름 그대로 Chrome 을 한 번도 부르지 않는다는 뜻이므로
    # 스크린샷도 건너뛴다. 소스 덤프만 받고 끝내려는 용도다.
    if a.text_only or a.no_browser:
        print("✓ 스크린샷 없이 검사 완료" if ok else "✗ 검증 실패")
        return 0 if ok else 1

    # ── 3. 장별 스크린샷 ──────────────────────────────────────────────────────
    want = (
        [int(x) for x in a.only.split(",") if x.strip()]
        if a.only else list(range(1, len(secs) + 1))
    )
    chrome = find_chrome()
    bad = [n for n in want if not 1 <= n <= len(secs)]
    for n in bad:
        print(f"  shot {n:02d}   ✗ 범위 밖 (1..{len(secs)})", flush=True)
        ok = False
    want = [n for n in want if n not in bad]

    # Chrome 을 장마다 새로 띄우므로 장당 약 3.6초다. 직렬로 돌리면 전장이 4분을 넘겨
    # 호출 쪽 타임아웃에 걸려 죽었다(2026-08-22, 67장 실측). 프로세스가 서로 독립이라
    # 그냥 몇 개씩 겹쳐 띄우면 되고, 하나에 200~400MB 를 쓰니 무한정 늘리지는 않는다.
    jobs = a.jobs or min(6, max(2, (os.cpu_count() or 4) // 2))
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        # 결과는 제출 순서대로 받는다 — 병렬로 돌아도 로그는 장 번호 순이라 diff 된다.
        futures = [
            (n, pool.submit(shoot, chrome, html, n, out / f"s-{n:02d}.png",
                            a.width, a.height, a.budget))
            for n in want
        ]
        for n, fut in futures:
            why = fut.result()
            png = out / f"s-{n:02d}.png"
            if why:
                print(f"  shot {n:02d}   ✗ {why}", flush=True)
                ok = False
            else:
                print(f"  shot {n:02d}   {png.name}  {png.stat().st_size // 1024}KB"
                      f"   {title_of(secs[n - 1])[:44]}", flush=True)

    if want:
        el = time.monotonic() - t0
        print(f"\n{len(want)}장 · {el:.0f}초 (동시 {jobs}개 · 장당 {el / len(want):.1f}초)")
    print(f"찍은 곳 → {out}")
    print("⚠️ 이미지를 직접 볼 것. 한 장이 한 화면을 넘는지·겹침·빈 카드는 여기서만 보인다.")
    print("✓ 통과" if ok else "✗ 검증 실패")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
