#!/usr/bin/env python3
"""헤드리스 Chrome 으로 PDF 를 뽑고 세 가지를 확인한다.

읽는 문서는 화면과 인쇄가 다르게 깨진다. 특히 이 셋이 문제가 된다.

  1. 폰트 임베드 — Pretendard·Geist Mono 외의 이름이 뜨면 어딘가에 그 폰트에
     없는 글자가 있다는 뜻이다. 고객 화면에서 글자 모양이 달라진다.
  2. 인쇄 공백 — 행이 많고 두꺼운 표는 `table{page-break-inside:avoid}` 때문에
     통째로 다음 페이지로 밀리면서 앞 페이지를 절반 이상 비운다. 화면에서는
     절대 안 보이고 PDF 로 뽑아 봐야 안다. 그 표의 래퍼에 `.tw.split` 을 붙여
     행 사이에서 갈리게 하면 해소된다.
  3. 페이지 수 — 고객 메일에 "A4 N페이지" 를 적을 때 필요하다.

사용법:
    python3 to_pdf.py <file.html> [-o out.pdf]

pdfinfo·pdffonts·pdftotext(poppler)가 있으면 함께 점검한다. 없으면 렌더까지만
하고 그 사실을 알린다 — 렌더 자체는 Chrome 만 있으면 된다.
"""
import argparse
import os
import shutil
import subprocess
import sys

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome",
    "chromium",
    "chromium-browser",
]
# 이 두 계열만 임베드돼야 정상이다. 문서가 다른 폰트를 쓰기로 했다면 여기를 바꾼다.
EXPECTED_FONTS = ("Pretendard", "GeistMono")
# 파트 구분자 페이지와 절 끝 페이지는 원래 글자가 적다. 그 아래로 내려가면
# 표가 통째로 밀린 흔적일 가능성이 크다.
THIN_PAGE_CHARS = 420


def find_chrome() -> str | None:
    for candidate in CHROME_CANDIDATES:
        if candidate.startswith("/"):
            if os.path.exists(candidate):
                return candidate
        elif shutil.which(candidate):
            return candidate
    return None


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("-o", "--out")
    args = ap.parse_args()

    html = os.path.abspath(args.html)
    if not os.path.exists(html):
        print(f"✗ 없는 파일: {html}")
        return 1
    out = os.path.abspath(args.out or os.path.splitext(html)[0] + ".pdf")

    chrome = find_chrome()
    if not chrome:
        print("✗ Chrome/Chromium 을 찾을 수 없다. CHROME_CANDIDATES 에 경로를 추가한다")
        return 1

    # --virtual-time-budget 은 웹폰트가 CDN 에서 내려올 시간을 준다. 짧으면
    # 폰트가 적용되기 전에 인쇄돼 레이아웃이 다르게 나온다.
    render = run([
        chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
        "--virtual-time-budget=45000", f"--print-to-pdf={out}", f"file://{html}",
    ])
    if not os.path.exists(out):
        print(f"✗ 렌더 실패\n{render.stderr[-2000:]}")
        return 1
    print(f"✓ {out} ({os.path.getsize(out) / 1_000_000:.1f}MB)")

    failed = False

    if shutil.which("pdfinfo"):
        info = run(["pdfinfo", out]).stdout
        pages = next((l.split()[-1] for l in info.splitlines()
                      if l.startswith("Pages:")), "?")
        size = next((l.split(":", 1)[1].strip() for l in info.splitlines()
                     if l.startswith("Page size:")), "?")
        print(f"  페이지 {pages} · {size}")
    else:
        print("  (pdfinfo 없음 — 페이지 수 미확인)")

    if shutil.which("pdffonts"):
        lines = run(["pdffonts", out]).stdout.splitlines()[2:]
        families = sorted({l.split()[0].split("+")[-1] for l in lines if l.strip()})
        unexpected = [f for f in families
                      if not any(f.startswith(e) for e in EXPECTED_FONTS)]
        if unexpected:
            failed = True
            print(f"  ✗ 예상 밖 폰트: {', '.join(unexpected)}")
            print("     → 그 폰트에 없는 글자가 문서에 있다. check_html.py 로 찾는다")
        else:
            print(f"  ✓ 폰트 {len(families)}종, 전부 예상 계열")
    else:
        print("  (pdffonts 없음 — 폰트 임베드 미확인)")

    if shutil.which("pdftotext"):
        text = run(["pdftotext", out, "-"]).stdout
        pages_text = [p.strip() for p in text.split("\f")][:-1]
        thin = [(i + 1, len(p), (p.splitlines() or [""])[0][:32])
                for i, p in enumerate(pages_text) if len(p) < THIN_PAGE_CHARS]
        if thin:
            print(f"  · 글자 적은 페이지 {len(thin)}곳 — 파트 구분자·절 끝이면 정상이다")
            for page, count, first in thin:
                print(f"      p{page}: {count}자 · \"{first}\"")
        else:
            print("  ✓ 글자 적은 페이지 없음")
        if not any("가" <= c <= "힣" for c in text):
            failed = True
            print("  ✗ 한글이 추출되지 않는다 — 고객이 검색할 수 없다")
    else:
        print("  (pdftotext 없음 — 인쇄 공백 미확인)")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
