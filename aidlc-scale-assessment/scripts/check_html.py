#!/usr/bin/env python3
"""자기완결 HTML 문서의 구조 점검. 표준 라이브러리만 쓴다.

사람이 눈으로 못 잡는 네 가지를 잡는다.

  1. 태그 균형 — 긴 표를 손으로 넣다 보면 </td> 하나가 빠지고, 브라우저는
     조용히 복구해 버려서 화면으로는 안 보인다. 인쇄에서만 레이아웃이 깨진다.
  2. 중복 id — 목차 링크가 첫 번째 것으로만 가고 나머지는 죽는다.
  3. 깨진 앵커 — 절을 지웠는데 목차 줄을 안 지우면 클릭이 아무 일도 안 한다.
  4. 폰트에 없는 글자 — Pretendard·Geist Mono 둘 다에 없는 글자는 PDF에서
     시스템 폰트를 끌어온다. 화면에서는 정상으로 보이므로 여기서 잡아야 한다.

사용법:
    python3 check_html.py <file.html> [<file2.html> ...]

종료 코드 0 = 통과, 1 = 문제 있음. CI 없이도 그냥 돌리면 된다.
"""
import re
import sys
import collections

# Pretendard·Geist Mono 어디에도 없어 시스템 폰트로 대체되는 글자.
# 실제로 PDF를 뽑아 pdffonts 로 확인해 모은 목록이다. 새로 발견하면 추가한다.
MISSING_GLYPHS = {
    "⇄": "⇄ (U+21C4) → ⇔ 로 바꾼다",
    "⇕": "⇕ (U+21D5) → ↕ 로 바꾼다",
    "▸": "▸ (U+25B8) → · 나 → 로 바꾼다",
    # 실측: 집합 연산 기호를 서술에 쓴 산출물의 PDF 가 Menlo 로 대체됐다. 이 검사는
    # 통과했고 to_pdf.py 의 폰트 이탈 경고만 잡았다 — 두 검사의 축을 맞춘다.
    "∪": "∪ (U+222A) → 「합집합」·「합친 고유 개수」로 풀어 쓴다",
    "∩": "∩ (U+2229) → 「교집합」·「양쪽에 다 있는 것」으로 풀어 쓴다",
    "⊆": "⊆ (U+2286) → 「포함된다」로 풀어 쓴다",
    "∖": "∖ (U+2216) → 「차집합」·「빼면 남는 것」으로 풀어 쓴다",
}
VOID = {"meta", "link", "br", "hr", "img", "input", "col",
        "source", "area", "base", "wbr", "embed", "track", "param"}

# 머리글 행을 빼고 열 줄이 넘으면 한 페이지를 넘길 만큼 두껍다. 실측에서 빈 페이지를 만든
# 표는 14행이었고, 정상 통과해야 하는 골격 스텁 표는 전부 이보다 짧다.
LONG_TABLE_ROWS = 12

COMMENT = re.compile(r"<!--.*?-->", re.S)

# 골격 스텁 주석에만 나오는 문구. 본문(주석 밖)에서 발견되면 주석이 깨진 것이다.
# 실측에서 새어 나온 문장을 그대로 쓴다 — 새 스텁 주석을 넣으면 여기에도 한 조각 넣는다.
SKELETON_PHRASES = (
    "적지 않는다 --",
    "열 구성 —",
    "**미결 전량에 하나씩 배정한다.**",
    "공수(인일·인월)나",
    "표본으로 고르지 않는다.",
)


def check(path: str) -> list[str]:
    problems: list[str] = []
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as exc:
        return [f"열 수 없다: {exc}"]

    # ── 1. 태그 균형 ───────────────────────────────────────────────────────
    stack: list[tuple[str, int]] = []
    for m in re.finditer(r"<(/?)([a-zA-Z][\w-]*)([^>]*?)(/?)>", text):
        closing, name, selfclose = m.group(1), m.group(2), m.group(4)
        name = name.lower()
        if name in VOID or selfclose == "/":
            continue
        line = text.count("\n", 0, m.start()) + 1
        if not closing:
            stack.append((name, line))
        elif not stack:
            problems.append(f"{line}행: 짝 없는 </{name}>")
        elif stack[-1][0] != name:
            open_name, open_line = stack[-1]
            problems.append(
                f"{line}행: </{name}> 가 닫으려는 것이 <{open_name}> ({open_line}행)"
            )
        else:
            stack.pop()
    for name, line in stack[:5]:
        problems.append(f"{line}행: <{name}> 가 닫히지 않았다")

    # ── 2. 중복 id ─────────────────────────────────────────────────────────
    ids = re.findall(r'\sid="([^"]+)"', text)
    for key, count in collections.Counter(ids).items():
        if count > 1:
            problems.append(f'id="{key}" 가 {count}번 나온다')

    # ── 3. 깨진 앵커 ───────────────────────────────────────────────────────
    for target in sorted(set(re.findall(r'href="#([^"]+)"', text)) - set(ids)):
        problems.append(f'href="#{target}" 의 대상이 없다')

    # ── 4. 폰트에 없는 글자 ────────────────────────────────────────────────
    for char, advice in MISSING_GLYPHS.items():
        if char in text:
            problems.append(f"폰트에 없는 글자 {advice}")
    hanja = {c for c in text if "一" <= c <= "鿿"}
    if hanja:
        problems.append(f"한자 {''.join(sorted(hanja))} — 폰트에 없다. 한글로 바꾼다")

    # 개별 목록은 매번 새 글자에 뚫린다. 실측(it.12)에서 `✅`(U+2705)가 인용에 들어와 PDF 가
    # AppleColorEmoji 를 끌어왔는데 이 검사는 통과했고 `to_pdf.py` 만 잡았다 → 범위로 넓힌다.
    #
    # 단 **넓게 잡으면 원문 인용을 거른다.** 처음 U+2600~U+27BF 를 통째로 걸었더니 어떤
    # 산출물의 인용 안 `★`(U+2605)가 걸렸는데, 그 집합 PDF 는 폰트 이탈이 0 이었다 —
    # Pretendard 가 커버하는 기호다. 인용은 원문 그대로여야 하므로 **컬러 이모지로 렌더되는
    # 대역과 알려진 개별 글자만** 잡고, 최종 판정은 `to_pdf.py` 의 폰트 이탈 검사에 맡긴다.
    KNOWN_EMOJI = {0x2705, 0x274C, 0x2714, 0x2716, 0x2757, 0x2B50, 0x26A0, 0x2B55,
                   0x2795, 0x2796, 0x27A1, 0x2764}
    emoji = {c for c in text
             if 0x1F000 <= ord(c) <= 0x1FAFF or ord(c) in (0xFE0F, 0x200D)
             or ord(c) in KNOWN_EMOJI}
    if emoji:
        codes = " ".join(f"{c}(U+{ord(c):04X})" for c in sorted(emoji))
        problems.append(f"이모지·딩뱃 {codes} — 폰트에 없어 PDF 가 다른 폰트를 끌어온다."
                        " 낱말로 바꾸거나 생략 표시로 줄인다")

    # ── 5. 골격 주석이 본문에 새어 나온 자리 ───────────────────────────────
    # 실측: 골격 스텁 주석을 편집하다 여는 `<!--` 가 지워져 지시문이 **고객 문서 본문에
    # 그대로 렌더링**됐다(마크다운 `**` 까지). 화면에서도 보이지만 조립하는 쪽은 자기가 쓴
    # 문장 사이에 섞여 있어 못 알아본다. `-->` 는 태그 균형 검사에 걸리지 않는다.
    # 여러 줄 주석을 통째로 지운 뒤 남은 기호만 본다 — 줄 단위로 보면 정상 주석의
    # 중간 줄이 전부 걸린다.
    outside = COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    for m in re.finditer(r"<!--|-->", outside):
        line = outside[:m.start()].count("\n") + 1
        frag = outside.splitlines()[line - 1].strip()[:60] if line - 1 < len(
            outside.splitlines()) else ""
        problems.append(f"{line}행 — 주석 기호가 짝 없이 남았다: {frag}")
    if any("짝 없이" in p for p in problems):
        problems.append("골격 주석의 여는 `<!--` 가 지워지면 지시문이 본문에 찍힌다."
                        " 그 블록을 지우거나 주석을 온전히 복구한다")

    # 여는 기호까지 함께 지워진 경우 위 검사가 못 잡는다. 골격 문구를 직접 찾는다.
    for mark in SKELETON_PHRASES:
        if mark in outside:
            problems.append(f"골격 지시문이 본문에 있다: \"{mark}\" — 그 문단을 지운다")

    # ── 6. 긴 표에 .tw.split 이 없다 ────────────────────────────────────────
    # 기본값 table{page-break-inside:avoid} 때문에 행이 많은 표는 통째로 다음 페이지로
    # 밀리고 앞 페이지가 절반 이상 빈다. 실측에서 두 산출물의 PDF 가 같은 자리(p34)에
    # 100자 내외인 페이지를 만들었고, 둘 다 14행 표가 밀린 것이었다. 규칙과 안내는
    # html-conventions.md ③ 에 이미 있었는데 지시로는 안 걸렸다 → 기계 검사로 만든다.
    for m in re.finditer(r"<table\b.*?</table>", text, re.S):
        rows = len(re.findall(r"<tr\b", m.group(0)))
        if rows < LONG_TABLE_ROWS:
            continue
        head = text[:m.start()]
        # 이 표를 감싸는 가장 가까운 여는 div 의 class 를 본다
        wrappers = re.findall(r'<div[^>]*class="([^"]*)"[^>]*>', head)
        if wrappers and "split" in wrappers[-1]:
            continue
        line = head.count("\n") + 1
        # 통과 여부는 바꾸지 않는다 — 긴 표 전부가 페이지 경계에 걸리는 것은 아니다.
        # 실측에서 여덟 자리가 걸렸고 실제로 빈 페이지를 만든 것은 하나였다. 실패로 세면
        # 주석 누출 같은 진짜 결함이 목록에 묻힌다.
        problems.append(
            f"⚠ {line}행 — {rows}행 표에 `.tw.split` 이 없다."
            " 인쇄에서 통째로 밀리면 앞 페이지가 빈다(`<div class=\"tw split\">`)")

    return problems


def main() -> int:
    paths = sys.argv[1:]
    if not paths:
        print(__doc__)
        return 1
    failed = False
    for path in paths:
        found = check(path)
        hard = [p for p in found if not p.startswith("⚠")]
        warn = [p for p in found if p.startswith("⚠")]
        if hard:
            failed = True
            print(f"✗ {path} — {len(hard)}건")
            for p in hard:
                print(f"    {p}")
        else:
            print(f"✓ {path} — 태그 균형 · id · 앵커 · 폰트 글자 모두 통과")
        if warn:
            print(f"  경고 {len(warn)}건 — 통과 여부는 바꾸지 않는다. 인쇄에서 확인한다")
            for p in warn:
                print(f"    {p}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
