#!/usr/bin/env python3
"""HTML 본문의 수치를 `surfaces.json` 과 대조한다. 손으로 옮긴 값은 어긋난다.

`surface_matrix.py` 는 **맞는 값을 계산해 주지만** 그 값이 HTML 에 옮겨 적히는 과정에서
어긋난다. 평가 네 산출물 **전부**에서 이 유형이 나왔다.

    표지·파트1·파트3 은 표면 44 인데 파트4 의 "센 값" 카드만 43
    스크립트가 RE04 12 / RE05 11 을 냈는데 본문은 두 라벨을 맞바꿔 적었다
    스크립트가 000 = 4/34 를 냈는데 막대는 6/34 로 적혔다 — 도구 출력에서 이탈
    "나머지 5건(C7 · C10 · C22 · C27~C29 · C39)" — 괄호 안은 7개다
    갭 9건이 참여 문서 없이 ID 만 적혔다

원인은 하나다 — **표면을 늦게 추가하면 파생 수치 수십 곳을 손으로 다시 갱신해야 한다.**
지시로는 막히지 않는다(스킬 본문에 "수치는 한 곳에서 재계산한다" 가 이미 있다). 그래서
조립이 끝난 뒤 **기계가 대조한다.**

**그런데 이 스크립트는 한 번 거짓 안심을 줬다.** 만들 때 본 실패 다섯 건을 잡는 것을 확인하고
채택했는데, 다음 판 다섯 산출물 **전부에 "0건" 을 내는 동안 채점자들은 26곳을 찾았다.** 못 본
자리가 여섯이었다.

    "강도 중 인 표면 여덟"          한글 수사 — 라벨은 붙었으나 숫자가 아니다
    표 셀의 33 · 17 · 16            라벨이 없다(정본 34 · 18 · 18)
    "합이 88이다"                   서술 문장 안의 맨 숫자(정본 90)
    "9개(C18 · C40 · G6 · G7 …)"    `C` 밖의 ID 접두를 세지 않았다
    "표면 96"                       정본 101 — 차이 5 를 부분합으로 봤다
    카드 본문 · 도해 주석            표·막대만 보고 지나갔다

그래서 축을 넓혔고, **통과 신호의 뜻을 좁혔다** — 출력 끝에 무엇을 검사하지 **않았는지** 항상
찍는다. `0건` 은 *"이 축에서 못 찾았다"* 는 뜻이고 *"본문 수치가 맞다"* 는 뜻이 아니다.

사용법:
    python3 check_numbers.py assessment.html surfaces.json
    python3 check_numbers.py assessment.html surfaces.json --no-strength   # 강도 대조 끄기
    python3 check_numbers.py assessment.html surfaces.json --no-bare       # 라벨 없는 숫자 끄기

나가는 값이 0 이면 **검사한 축에서** 어긋난 곳이 없다. 1 이면 있다.
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

TAG = re.compile(r"<[^>]+>")
BAR = re.compile(r'class="bar"')
BV = re.compile(r'class="bv"[^>]*>\s*([\d,]+)\s*/\s*([\d,]+)')
BL = re.compile(r'class="bl"[^>]*>(.*?)</div>', re.S)
WIDTH = re.compile(r"width:\s*([\d.]+)%")
CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)

STATUS_LABEL = {"con": "충돌", "dup": "중복", "gap": "갭", "ok": "정리됨"}

# 총계 성격 라벨은 부분합일 수 없다 → `--near` 를 적용하지 않고 전부 본다.
# *"표면 96"* 이 정본 101 일 때 차이가 5 라 near 밖으로 빠져나갔다.
TOTAL_LABELS = ("표면", "계약 지점", "경계 지점", "인용", "하한")

# **정본 키 하나에 산출물이 쓰는 낱말을 전부 잇는다.** 골격이 `s31` 제목을
# *"계약 지점 N개의 상태"* 로 주므로 산출물은 그 낱말을 쓴다. `표면` 만 찾다가 한 집합의
# 어긋남 **7건을 전량** 놓쳤고 그 항목이 `fail` 로 내려갔다.
ALIAS = {
    "표면": ("계약 지점", "경계 지점", "계약 표면", "경계 표면", "기반 계약", "결정 기록"),
    "미결": ("미결 안건", "열려 있는 것", "미결 표면", "남은 것"),
    "인용": ("근거 인용", "원문 인용", "근거 원문"),
    "갭": ("고아", "규격 미정"),
}

# 한글 수사. **수량사와 관형사형을 가른다** — 관형사형(`한`·`두`·`세`)은 흔한 글자라
# *"동시 상**한**(2)"* 처럼 엉뚱한 자리에 걸린다. 그래서 관형사형은 단위가 뒤에 올 때만 센다.
HANGUL_CARD = {
    "하나": 1, "둘": 2, "셋": 3, "넷": 4, "다섯": 5, "여섯": 6, "일곱": 7,
    "여덟": 8, "아홉": 9, "열": 10, "열하나": 11, "열둘": 12, "열셋": 13,
    "열넷": 14, "열다섯": 15, "열여섯": 16, "열일곱": 17, "열여덟": 18,
    "열아홉": 19, "스물": 20,
}
HANGUL_DET = {
    "한": 1, "두": 2, "세": 3, "네": 4, "열한": 11, "열두": 12, "열세": 13,
    "열네": 14, "스무": 20,
}
HANGUL_NUM = dict(HANGUL_CARD, **HANGUL_DET)
UNIT = r"(?:개|건|곳|장|벌|쌍|묶음)"
# 긴 것을 먼저 시도해야 *"열둘"* 이 *"열"* 로 잘리지 않는다.
CARD_ALT = "|".join(sorted(HANGUL_CARD, key=len, reverse=True))
DET_ALT = "|".join(sorted(HANGUL_DET, key=len, reverse=True))
# 수량사는 단위 없이 ID 목록이 바로 붙는 자리가 있다 — 실측이 *"표면 여덟(C10 · C11 …)"*
# 이었다. 공백만으로는 인정하지 않는다(*"세 번째"* 가 걸린다).
HANGUL_TAIL = rf"(?:{UNIT}|[(（]|이다|이고|이며|이라)"

# 부분합 서술의 표지. 총계 라벨 앞에 이것이 있으면 전체를 말하는 자리가 아니다 —
# *"경계 표면 7"* · *"1층 표면 12"* 는 정당하다.
PARTIAL_HINT = re.compile(r"(?:경계|층|단계|구간|갈래|쌍|중|내|당|째|그|남|미|추가|공유)"
                          r"[가-힣]{0,3}\s*$")

# 단위가 붙은 숫자는 표면 수와 무관하다 — 라벨 없는 숫자를 훑을 때 걸러 낸다.
UNIT_AFTER = re.compile(r"^\s*(?:%|px|kb|mb|일|주|월|년|시간|분|초|명|원|행|자|배|페이지|p\b)")


def id_pattern(prefixes) -> re.Pattern:
    """표면 ID 정규식. 접두는 `surfaces.json` 에서 실제로 쓰인 것을 모아 만든다.

    `C` 만 박아 두었더니 `G` 계열을 쓰는 산출물에서 *"9개(C18 · C40 · G6 …)"* 를 2개로
    셌다. 접두를 고정하지 않는다.
    """
    alt = "|".join(sorted((re.escape(p) for p in prefixes), key=len, reverse=True))
    return re.compile(rf"\b({alt})(\d{{1,3}})\b")


def strip_tags(line: str) -> str:
    return TAG.sub(" ", line).replace("&middot;", "·").replace("&nbsp;", " ")


def expand_ids(text: str, sid: re.Pattern, rng: re.Pattern) -> set:
    """괄호 안의 ID 를 센다. `C27~C29` 는 3개로 펼친다. 접두는 섞여 있어도 된다."""
    ids = set()
    for m in rng.finditer(text):
        pre, a, b = m.group(1), int(m.group(2)), int(m.group(3))
        if a <= b and b - a < 40:
            ids.update(f"{pre}{n}" for n in range(a, b + 1))
    ids.update(m.group(0) for m in sid.finditer(text))
    return ids


def hangul_scan(text_lines, table):
    """*"강도 최상 넷"* · *"작업 단위가 세 벌"* — 라벨에 한글 수사가 붙은 자리.

    채점자가 두 산출물에서 이 유형을 찾았고 스크립트는 *"강도 낱말이 붙은 수치: 없다"* 를
    냈다. 숫자만 보고 있었다.
    """
    out = []
    for label, want in table.items():
        pat = re.compile(
            rf"(?<![가-힣]){re.escape(label)}(?![가-힣])[^\d\n]{{0,12}}?"
            rf"(?:({CARD_ALT})\s*{HANGUL_TAIL}|({DET_ALT})\s*{UNIT})")
        for i, t in enumerate(text_lines, 1):
            for m in pat.finditer(t):
                word = m.group(1) or m.group(2)
                got = HANGUL_NUM[word]
                if got == want:
                    continue
                if PARTIAL_HINT.search(t[max(0, m.start() - 12):m.start()]):
                    continue
                out.append((label, want, got, word, i,
                            t.strip()[max(0, m.start() - 26):m.start() + 30].strip()))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("surfaces")
    ap.add_argument("--no-strength", action="store_true",
                    help="강도(최상·상) 대조를 끈다. 강도 낱말이 서술에 많이 쓰이면 끈다")
    ap.add_argument("--near", type=int, default=2,
                    help="정본과의 차이가 이 값 안일 때만 어긋남으로 본다(기본 2). "
                         "부분합은 대체로 정본과 멀고, 손으로 옮기다 나는 실패는 가깝다")
    ap.add_argument("--policy", nargs="*", default=[],
                    help="정책 문서 이름. `surface_matrix.py` 와 같은 값을 준다")
    ap.add_argument("--no-bare", action="store_true",
                    help="라벨 없는 숫자 훑기를 끈다. 후보가 많으면 끈다")
    args = ap.parse_args()

    surfaces = json.load(open(args.surfaces, encoding="utf-8"))
    lines = Path(args.html).read_text(encoding="utf-8").splitlines()
    text_lines = [strip_tags(x) for x in lines]

    # 표면 ID 의 접두를 `surfaces.json` 에서 모은다 — `C` 로 고정하면 다른 계열을 놓친다.
    prefixes = set()
    for s in surfaces:
        m = re.match(r"([A-Za-z]{1,3})\d{1,3}$", str(s.get("id", "")).strip())
        if m:
            prefixes.add(m.group(1))
    if not prefixes:
        prefixes = {"C"}
    sid = id_pattern(prefixes)
    palt = "|".join(sorted((re.escape(p) for p in prefixes), key=len, reverse=True))
    rng = re.compile(rf"({palt})(\d{{1,3}})\s*[~\-–]\s*(?:{palt})?(\d{{1,3}})")
    # "5건(C7 · C10 · C27~C29)" — 앞의 개수와 괄호 안 ID 수가 맞는가
    paren = re.compile(r"(\d{1,3})\s*(?:건|개)\s*[(（]([^)）]{0,400})[)）]")

    policy = set(args.policy)
    tally = Counter(s.get("status", "?") for s in surfaces)
    strength = Counter(s.get("strength", "?") for s in surfaces)
    involve = Counter()
    for s in surfaces:
        involve.update(sorted(set(s.get("parties", [])) - policy))
    total = len(surfaces)
    undecided = sum(tally.get(k, 0) for k in ("con", "dup", "gap"))
    cites_total = sum(len([c for c in s.get("cites", []) if str(c).strip()])
                      for s in surfaces)
    floor = sum({"con": 2}.get(s.get("status", ""), 1) for s in surfaces)

    print("# 수치 대조 — `surfaces.json` 이 정본이다\n")
    print(f"표면 **{total}** · 충돌 {tally.get('con', 0)} · 중복 {tally.get('dup', 0)}"
          f" · 갭 {tally.get('gap', 0)} · 정리됨 {tally.get('ok', 0)}"
          f" · 미결 {undecided} · 인용 {cites_total} / 하한 {floor}"
          f" · ID 접두 {'·'.join(sorted(prefixes))}\n")

    problems = 0

    # ── ① 표면 ID 집합 ────────────────────────────────────────────────────
    declared = []
    for s in surfaces:
        m = sid.match(str(s.get("id", "")).strip())
        declared.append(m.group(0) if m else None)
    dup_ids = [k for k, v in Counter(i for i in declared if i).items() if v > 1]
    in_html = set()
    for t in text_lines:
        in_html.update(m.group(0) for m in sid.finditer(t))
    known = set(i for i in declared if i)

    def id_key(x):
        m = sid.match(x)
        return (m.group(1), int(m.group(2))) if m else (x, 0)

    missing = sorted(known - in_html, key=id_key)
    unknown = sorted(in_html - known, key=id_key)

    print("## 표면 ID\n")
    if dup_ids:
        print(f"- **`surfaces.json` 에 중복 ID: {', '.join(sorted(dup_ids, key=id_key))}**")
        problems += 1
    if missing:
        print(f"- **HTML 에 없는 표면: {', '.join(missing)}**"
              " — 분석에는 있고 본문에 안 실렸다")
        problems += 1
    if unknown:
        print(f"- **HTML 에만 있는 ID: {', '.join(unknown)}**"
              " — `surfaces.json` 에 없다. 오타이거나 지운 표면의 잔재다")
        problems += 1
    if not (dup_ids or missing or unknown):
        print(f"ID {total}개가 양쪽에 그대로 있다.")

    # ── ② 라벨 붙은 수치 ──────────────────────────────────────────────────
    # "표면 44" · "충돌 15" 처럼 라벨과 붙은 숫자를 전부 뽑아 기대값과 맞춘다.
    expect = {
        "표면": total,
        "충돌": tally.get("con", 0),
        "중복": tally.get("dup", 0),
        "갭": tally.get("gap", 0),
        "정리됨": tally.get("ok", 0),
        "미결": undecided,
        "인용": cites_total,
        "하한": floor,
    }
    # 별칭을 같은 값으로 펼친다. 긴 낱말이 먼저 매칭돼야 *"계약 지점 27"* 이 `지점` 이 아니라
    # 통째로 걸린다 — `scan` 이 `expect` 를 순회하므로 삽입 순서를 길이 역순으로 둔다.
    for key, names in ALIAS.items():
        if key in expect:
            for alt in sorted(names, key=len, reverse=True):
                expect[alt] = expect[key]
    soft = {}
    if not args.no_strength:
        soft["최상"] = strength.get("최상", 0)
        soft["상"] = strength.get("상", 0)
    print("\n## 라벨 붙은 수치\n")
    print(f"상태별 라벨은 정본에서 **±{args.near} 안**으로 어긋난 것만 본다 —"
          " *\"1층 표면 11개\"* 처럼 부분합은 정당하다. 그러나"
          f" **{' · '.join(TOTAL_LABELS)}** 는 총계라 부분합일 수 없으므로 **차이가 얼마든"
          " 전부 본다** — 정본 101 을 96 으로 적은 자리가 차이 5 로 빠져나간 적이 있다.\n")

    def scan(table, near_only=True):
        out = []
        for label, want in table.items():
            exact = label in TOTAL_LABELS
            # *"표면 수(88)"* 처럼 라벨과 숫자 사이에 `수` 와 괄호가 끼는 자리가 있다.
            pat = re.compile(rf"(?<![가-힣]){re.escape(label)}(?![가-힣])\s*수?\s*(?:이|가|은|는)?\s*"
                             rf"[(（]?\s*(\d[\d,]*)\s*(?:개|건|곳|장)?")
            for i, t in enumerate(text_lines, 1):
                for m in pat.finditer(t):
                    got = int(m.group(1).replace(",", ""))
                    if got == want:
                        continue
                    if not exact and near_only and abs(got - want) > args.near:
                        continue
                    # 총계 라벨을 near 없이 보는 대신, 부분합 표지가 앞에 있으면 뺀다 —
                    # *"경계 표면 7 · 이력 ↔ 뷰어"* 를 전부 어긋남으로 세면 진짜가 묻힌다.
                    if exact and abs(got - want) > args.near and PARTIAL_HINT.search(
                            t[max(0, m.start() - 12):m.start()]):
                        continue
                    frag = t.strip()[max(0, m.start() - 30):m.start() + 40].strip()
                    out.append((label, want, got, i, frag))
        # 차이가 작은 것부터 — 손으로 옮기다 나는 실패가 위에 온다
        return sorted(out, key=lambda r: abs(r[2] - r[1]))

    bad = scan(expect)
    if bad:
        print("| 라벨 | 정본 | 본문 | 차이 | 행 | 자리 |")
        print("|---|---|---|---|---|---|")
        for label, want, got, i, frag in bad[:40]:
            print(f"| {label} | {want} | **{got}** | {got - want:+d} | {i} | {frag[:60]} |")
        if len(bad) > 40:
            print(f"\n… 그 밖 {len(bad) - 40}건")
        print("\n**어긋난 자리를 정본으로 고친다.** 다만 라벨이 다른 뜻으로 쓰인 문장"
              "(예 *\"충돌 24건 중 12건\"*)도 걸린다 — 한 줄씩 눈으로 가른다.")
        problems += 1
    else:
        print("라벨 붙은 수치가 전부 정본과 같다.")

    # ── ②-c 숫자가 라벨 앞에 붙은 형태 — *"58표면"* ─────────────────────────
    # 실측(it.13): 파생 수치 7건이 전부 이 스크립트 밖의 형태였고 한 채점자가 셋으로 갈랐다 —
    # **숫자 뒤 라벨**(*"58표면"*) · 정본 키가 아닌 라벨 · 이중 계상. 위 ② 는 `라벨 + 수` 만
    # 보므로 순서가 뒤집힌 자리를 지나간다.
    #
    # 처음 `\d+\s*라벨` 로 넓게 걸었더니 오탐이 지배했다 — *"02 충돌"*(문서명) · *"C23 미결"*(ID) ·
    # *"층 1 미결 15"*(다른 축의 수식). **숫자와 라벨이 붙어 있고 앞이 ID·문서명·다른 축이
    # 아닌 것**만 본다(검증: 과녁 1건 검출 · 다른 네 집합 오탐 0).
    print("\n## 숫자가 라벨 앞에 붙은 자리\n")
    rev = re.compile(r"(?<![A-Za-z0-9§\-])(\d{1,4})("
                     + "|".join(re.escape(k) for k in expect) + r")(?![가-힣])")
    rev_bad = []
    for i, t in enumerate(text_lines, 1):
        for m in rev.finditer(t):
            got, label = int(m.group(1)), m.group(2)
            want = expect.get(label)
            if want is None or got == want:
                continue
            pre = t[max(0, m.start() - 12):m.start()]
            if re.search(r"(층|단계|일차|묶음|배치)\s*\d?\s*$", pre):
                continue                      # 다른 축이 수식하는 자리
            rev_bad.append((i, label, want, got,
                            t.strip()[max(0, m.start() - 16):m.start() + 30].strip()))
    if rev_bad:
        print("| 행 | 라벨 | 정본 | 본문 | 자리 |")
        print("|---|---|---|---|---|")
        for i, label, want, got, frag in rev_bad[:20]:
            print(f"| {i} | {label} | {want} | **{got}** | {frag[:44]} |")
        print("\n**부분합이면 범위를 밝히고, 총계 자리면 정본 값으로 고친다.** 같은 문구가"
              " 여럿이면 한 번 판정해 전부 처리한다.")
        problems += 1
    else:
        print("숫자가 라벨 앞에 붙은 자리가 전부 정본과 같다(또는 없다).")

    # ── ②-b 라벨 + 한글 수사 ──────────────────────────────────────────────
    print("\n## 라벨에 한글 수사가 붙은 자리\n")
    hb = hangul_scan(text_lines, dict(expect, **{k: v for k, v in strength.items()
                                                if k in ("최상", "상", "중")}))
    if hb:
        print("| 라벨 | 정본 | 본문 | 낱말 | 행 | 자리 |")
        print("|---|---|---|---|---|---|")
        for label, want, got, word, i, frag in hb[:25]:
            print(f"| {label} | {want} | **{got}** | {word} | {i} | {frag[:52]} |")
        print("\n**부분합 서술이면 그대로 두고, 전체를 말하는 자리면 고친다.** 숫자로 쓴 자리는"
              " 위 표가 보고 이 표는 *\"여덟\"* · *\"세 벌\"* 처럼 낱말로 쓴 자리를 본다.")
        problems += 1
    else:
        print("라벨에 붙은 한글 수사가 정본과 어긋나는 자리가 없다.")

    # 강도 낱말은 부분합 서술에 자주 쓰인다(*"충돌 17건 중 최상 10건"*). 어긋남으로 세지
    # 않고 목록만 낸다 — 평가에서 이 축의 참 판정과 거짓 판정이 반반이었다.
    if soft:
        rows = scan(soft)
        print("\n### 참고 — 강도 낱말이 붙은 수치 (부분합일 수 있다)\n")
        if rows:
            print("| 라벨 | 전체 | 본문 | 행 | 자리 |")
            print("|---|---|---|---|---|")
            for label, want, got, i, frag in rows[:20]:
                print(f"| {label} | {want} | {got} | {i} | {frag[:60]} |")
            print("\n부분합이면 그대로 두고, 전체를 말하는 자리면 고친다.")
        else:
            print("없다.")

    # ── ③ 괄호 안 ID 개수 ────────────────────────────────────────────────
    print("\n## \"N건(ID · ID …)\" 대조\n")
    status_of = {}
    for s, num in zip(surfaces, declared):
        if num:
            status_of[num] = s.get("status", "?")
    paren_bad, status_bad = [], []
    for i, t in enumerate(text_lines, 1):
        for m in paren.finditer(t):
            want = int(m.group(1))
            inner = m.group(2)
            if "+" in inner:      # *"16건(1층 12 + 순환에 걸린 C10 …)"* 는 합산 서술이다
                continue
            ids = expand_ids(inner, sid, rng)
            if not ids:
                continue
            if want != len(ids):
                paren_bad.append((i, want, len(ids), m.group(0)[:70]))
            # 상태 낱말을 붙여 센 목록에 다른 상태가 섞이는 실패가 있었다 —
            # *"충돌 12건"* 으로 센 목록에 갭 하나가 들어 있었다.
            before = t[max(0, m.start() - 40):m.start()]
            for key, word in STATUS_LABEL.items():
                if word in before:
                    odd = sorted(f"{n}({STATUS_LABEL.get(status_of[n], '?')})"
                                 for n in ids
                                 if n in status_of and status_of[n] != key)
                    if odd:
                        status_bad.append((i, word, ", ".join(odd), m.group(0)[:60]))
                    break
    if paren_bad:
        print("| 행 | 적힌 수 | 괄호 안 ID | 자리 |")
        print("|---|---|---|---|")
        for i, want, got, frag in paren_bad:
            print(f"| {i} | {want} | **{got}** | {frag} |")
        problems += 1
    else:
        print("괄호 안 ID 개수가 앞의 수와 전부 맞는다.")
    if status_bad:
        print("\n**상태 낱말과 목록이 어긋난다.**\n")
        print("| 행 | 적힌 상태 | 다른 상태인 ID | 자리 |")
        print("|---|---|---|---|")
        for i, word, odd, frag in status_bad[:20]:
            print(f"| {i} | {word} | **{odd}** | {frag} |")
        problems += 1

    # ── ④ 막대 라벨과 값 ─────────────────────────────────────────────────
    # 라벨을 맞바꿔 적는 실패가 있었다 — 값은 스크립트 것이고 이름만 뒤집혔다.
    print("\n## 막대 — 라벨과 값\n")
    bar_bad, bar_seen = [], 0
    for i, raw in enumerate(lines, 1):
        if not BAR.search(raw):
            continue
        # 막대는 한 줄로 쓰기도 하고 여러 줄로 쪼개 쓰기도 한다. 뒤 여섯 줄까지 묶어 본다.
        block = "\n".join(lines[i - 1:i + 6])
        bv, bl = BV.search(block), BL.search(block)
        if not (bv and bl):
            continue
        label = strip_tags(bl.group(1))
        got, denom = int(bv.group(1).replace(",", "")), int(bv.group(2).replace(",", ""))
        hits = [p for p in involve if p and p in label]
        if not hits:
            continue
        bar_seen += 1
        party = max(hits, key=len)
        want = involve[party]
        wm = WIDTH.search(block)
        want_w = want / total * 100 if total else 0
        if got != want or denom != total or (
                wm and abs(float(wm.group(1)) - want_w) > 0.6):
            bar_bad.append((i, label.strip()[:34], party, want, got, denom,
                            wm.group(1) if wm else "—", f"{want_w:.1f}"))
    if bar_bad:
        print("| 행 | 라벨 | 걸린 갈래 | 정본 | 본문 | 분모 | width | 정본 width |")
        print("|---|---|---|---|---|---|---|---|")
        for row in bar_bad:
            print(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | **{row[4]}** |"
                  f" {row[5]} | {row[6]}% | {row[7]}% |")
        print("\n**라벨과 값이 맞는지 본다.** 값은 맞고 이름만 뒤바뀐 경우가 있었다.")
        problems += 1
    elif bar_seen:
        print(f"갈래 막대 {bar_seen}개의 값·분모·width 가 정본과 같다.")
    else:
        print("갈래 이름이 걸리는 막대가 없다 — `class=\"bar\"` 와 `bl`·`bv` 를 확인한다.")

    # ── ⑤ 표면마다 참여 문서가 본문에 있는가 ──────────────────────────────
    # 갭·정리됨의 참여 표기 누락이 네 판에 걸쳐 반복됐다. 카드에는 적고 표에는 잊는다.
    print("\n## 참여 문서 표기\n")
    where = defaultdict(list)
    for i, t in enumerate(text_lines):
        for m in sid.finditer(t):
            where[m.group(0)].append(i)
    no_party = []
    for s, num in zip(surfaces, declared):
        parties = [p for p in s.get("parties", []) if p]
        if num is None or not parties:
            continue
        # 참여를 갈래 코드로 적는 산출물도 있고 문서 라벨로 적는 산출물도 있다. `cites` 의
        # 앞머리(*"REQ §3.2.1"* 의 `REQ`)도 같은 자리를 가리키므로 함께 인정한다.
        tokens = set(parties)
        for c in s.get("cites", []):
            head = re.split(r"[\s§:·—]", str(c).strip(), maxsplit=1)[0]
            if len(head) >= 2:
                tokens.add(head)
        found = False
        for i in where.get(num, []):
            window = " ".join(text_lines[max(0, i - 1):i + 3])
            if any(p in window for p in tokens):
                found = True
                break
        if not found:
            no_party.append((s.get("id"), s.get("status", "?"), ", ".join(parties)))
    if no_party:
        print("**아래 표면은 ID 가 본문에 있으나 참여 문서가 그 근처에 없다.**")
        print("상태와 무관하게 참여를 적는다 — 갭·정리됨에서 빠지는 것이 가장 자주 나는 실패다.\n")
        print("| 표면 | 상태 | 참여 (`surfaces.json`) |")
        print("|---|---|---|")
        for sid, st, parties in no_party:
            print(f"| {sid} | {STATUS_LABEL.get(st, st)} | {parties} |")
        problems += 1
    else:
        print("표면 전부가 참여 문서와 함께 본문에 있다.")

    # ── ④-b "A N개 중 M개" — 앞의 N 이 정본과 맞는가 ──────────────────────
    # *"갭 48개 중 19개"* 처럼 부분합 서술로 보이면 위 라벨 검사가 통과시킨다. 그런데
    # **앞의 N 은 총계**이므로 정본과 맞아야 한다. 실측에서 그 자리 둘이 어긋났다.
    print("\n## \"A N개 중 M개\" — 앞의 수\n")
    OFN = re.compile(rf"(?<![가-힣])({'|'.join(re.escape(k) for k in expect)})"
                     rf"\s*수?\s*(\d{{1,4}})\s*(?:개|건|곳)?\s*중\s*(\d{{1,4}})")
    ofn_bad = []
    for i, t in enumerate(text_lines, 1):
        for m in OFN.finditer(t):
            label, whole, part = m.group(1), int(m.group(2)), int(m.group(3))
            want = expect.get(label)
            if want is None or whole == want:
                continue
            ofn_bad.append((i, label, want, whole, part,
                            t.strip()[max(0, m.start() - 20):m.start() + 44].strip()))
    if ofn_bad:
        print("| 행 | 라벨 | 정본 | 적힌 전체 | 부분 | 자리 |")
        print("|---|---|---|---|---|---|")
        for i, label, want, whole, part, frag in ofn_bad[:20]:
            print(f"| {i} | {label} | {want} | **{whole}** | {part} | {frag[:50]} |")
        print("\n**부분(중 M)은 정당해도 전체(N)는 정본과 같아야 한다.**")
        problems += 1
    else:
        print("`A N개 중 M개` 형 서술의 앞 수가 전부 정본과 같다.")

    # ── ④-c 층·단계별 개수 — *"층 3 의 15개"* ─────────────────────────────
    # 실측(it.11): 남은 전파 누락 10건이 **전부** 「표·정본은 재계산했고 그 수를 인용하는
    # 서술 문장을 안 따라간 것」이었고, 이 스크립트가 하나도 잡지 못했다. 원인은 라벨 패턴이
    # 아니라 **그 축의 정본이 없던 것**이다 — 다섯 집합 중 `layer` 를 `surfaces.json` 에 둔
    # 것은 하나뿐이고 나머지는 작업 파일이나 본문에만 있었다. 정본에 자리가 있으면 기계적으로
    # 잡힌다(검증: 한 산출물의 *"층 3 의 15개"* ↔ 정본 18).
    print("\n## 층·단계별 개수\n")
    layer_axes = []
    for field, word in (("layer", "층"), ("aidlc", None)):
        vals = [s.get(field) for s in surfaces if s.get(field) not in (None, "")]
        if vals:
            layer_axes.append((field, word, Counter(str(v).strip() for v in vals)))
    if not layer_axes:
        print("`surfaces.json` 에 `layer`·`aidlc` 가 없다 — **이 축을 검사하지 못했다.**"
              " 층과 단계 배정은 판정의 근거이고 서술 문장이 그 수를 인용한다."
              " 정본에 두면 이 검사가 켜진다(스키마: `layer` 는 층 번호나 층 이름,"
              " `aidlc` 는 `ideation`·`inception`·`prep`).")
        unchecked_extra = True
    else:
        unchecked_extra = False
        lay_bad = []
        for field, word, cnt in layer_axes:
            for key, want in cnt.items():
                # 층은 **반드시 「층 N」 형태로만** 찾는다. 번호만 쓰면 *"충돌 39개"* 의 `3` 을
                # 층 3 으로 읽어 거짓 양성이 쏟아진다(실측에서 과녁 1건에 오탐 11건).
                # 단계(`aidlc`)는 `ideation`·`inception` 같은 낱말이라 그대로 쓴다.
                if word == "층":
                    m = re.match(r"(\d{1,2})", key)
                    keys = [f"층 {m.group(1)}"] if m else []
                else:
                    keys = [key]
                for k in keys:
                    pat = re.compile(rf"{re.escape(k)}\s*(?:의|은|는|에)?\s*(\d{{1,4}})\s*(?:개|건|곳)")
                    for i, t in enumerate(text_lines, 1):
                        for mm in pat.finditer(t):
                            got = int(mm.group(1))
                            if got == want:
                                continue
                            # `--near` 를 여기서는 쓰지 않는다. 층·단계별 개수는 부분합이
                            # 아니라 정본에서 정확히 세어지는 값이므로 차이가 커도 어긋남이다.
                            # 실측의 그 자리가 정본 18 ↔ 본문 15 로 차이 3 이었다.
                            lay_bad.append((i, k, want, got,
                                            t.strip()[max(0, mm.start() - 18):
                                                      mm.start() + 40].strip()))
        seen_lay = set()
        lay_bad = [x for x in lay_bad
                   if not (x[:4] in seen_lay or seen_lay.add(x[:4]))]
        if lay_bad:
            print("| 행 | 축 | 정본 | 본문 | 자리 |")
            print("|---|---|---|---|---|")
            for i, k, want, got, frag in lay_bad[:20]:
                print(f"| {i} | {k} | {want} | **{got}** | {frag[:48]} |")
            print("\n**정본의 층·단계 배정에서 센 값과 다르다.** 표를 고치고 서술 문장을"
                  " 안 고친 자리가 이 모양이다.")
            problems += 1
        else:
            axes = " · ".join(f"`{f}`" for f, _, _ in layer_axes)
            print(f"{axes} 로 센 층·단계별 개수가 본문 서술과 같다.")

    # ── ④-d 축 라벨 혼용 — *"층 1 합의 25건"* 인데 25 는 단계 수 ─────────────
    # 실측(it.12): 정본에 `layer`·`aidlc` 를 두어 수치 대조는 닫혔는데, 세 채점자가 독립적으로
    # 같은 유형을 지적했다 — **수는 맞고 그 수에 붙은 축 라벨이 틀렸다.** 한 산출물의 부록
    # 트리가 `ideation/` 에 *"층 1 합의 25건"* 을 붙였고 정본 층 1 은 20, ideation 이 25 다.
    # 위 ④-c 는 「층 N」 바로 뒤 숫자만 보므로 사이에 낱말이 끼면 지나간다.
    # **다른 축의 값과 정확히 일치할 때만** 보고한다 — 그래서 오탐이 없다(검증: 과녁 2건 검출,
    # 오탐 0. 같은 검사의 다른 형태였던 「ID 열거의 축 일관성」은 오탐이 5/7 이라 채택하지 않고
    # 아래 "검사하지 않은 축" 에 남겼다).
    print("\n## 축 라벨 혼용 — 층 자리에 단계 수, 단계 자리에 층 수\n")
    mix_bad = []
    if layer_axes:
        lay_cnt = next((c for f, _w, c in layer_axes if f == "layer"), None)
        stg_cnt = next((c for f, _w, c in layer_axes if f == "aidlc"), None)
        if lay_cnt and stg_cnt:
            # 층 이름이 "1 · 사전 준비" 처럼 길 수 있으므로 앞 번호로 정본을 찾는다
            by_num = {}
            for k, v in lay_cnt.items():
                mm = re.match(r"(\d{1,2})", k)
                if mm:
                    by_num[mm.group(1)] = v
            for i, t in enumerate(text_lines, 1):
                for m in re.finditer(r"층\s*(\d{1,2})[^0-9]{0,12}?(\d{1,4})\s*(?:개|건|곳)", t):
                    key, got = m.group(1), int(m.group(2))
                    want = by_num.get(key)
                    if want is None or got == want:
                        continue
                    alt = [k for k, v in stg_cnt.items() if v == got]
                    if alt:
                        mix_bad.append((i, key, want, got, alt[0],
                                        t.strip()[max(0, m.start() - 14):
                                                  m.start() + 40].strip()))
    if mix_bad:
        print("| 행 | 축 | 그 층의 정본 | 본문 | 실은 이 값 | 자리 |")
        print("|---|---|---|---|---|---|")
        for i, key, want, got, alt, frag in mix_bad[:20]:
            print(f"| {i} | 층 {key} | {want} | **{got}** | 단계 `{alt}` | {frag[:44]} |")
        print("\n**층 라벨에 단계 수가 붙었다.** 수치는 맞고 라벨이 틀린 유형이라 수 대조로는"
              " 통과한다 — 라벨을 고치거나 그 층의 값으로 바꾼다.")
        problems += 1
    elif layer_axes:
        print("층 라벨에 붙은 수가 전부 그 층의 정본 값이다.")
    else:
        print("`layer`·`aidlc` 가 없어 검사하지 못했다.")

    # ── ⑤-b 인접 쌍 — *"01 ↔ RE06 10개"* ─────────────────────────────────
    # 표면을 늦게 추가하면 쌍별 수가 전부 흔들린다. 한 산출물이 손으로 추가한 다섯 표면
    # **이전 값으로 19쌍이 굳었고** `matrix.md` 에는 옳은 값이 있었다. 도구가 옳고 본문이 틀렸다.
    print("\n## 인접 쌍 — 갈래 A ↔ B 의 개수\n")
    pair_want = Counter()
    for s in surfaces:
        ps = sorted(set(p for p in s.get("parties", []) if p) - policy)
        for i in range(len(ps)):
            for j in range(i + 1, len(ps)):
                pair_want[(ps[i], ps[j])] += 1
    known_party = set(involve)
    ADJ = re.compile(r"([A-Za-z0-9가-힣_·\-]{1,20})\s*↔\s*([A-Za-z0-9가-힣_·\-]{1,20})"
                     r"\s*(?:의|가|는|은)?\s*(\d{1,3})\s*개")
    adj_bad, adj_seen = [], 0
    for i, t in enumerate(text_lines, 1):
        for m in ADJ.finditer(t):
            a, b, got = m.group(1).strip(), m.group(2).strip(), int(m.group(3))
            if a not in known_party or b not in known_party:
                continue
            adj_seen += 1
            want = pair_want.get(tuple(sorted((a, b))), 0)
            if got != want:
                adj_bad.append((i, f"{a} ↔ {b}", want, got))
    if adj_bad:
        print("| 행 | 쌍 | 정본 | 본문 |")
        print("|---|---|---|---|")
        for i, pair, want, got in adj_bad[:25]:
            print(f"| {i} | {pair} | {want} | **{got}** |")
        print("\n**`surfaces.json` 의 `parties` 로 다시 센 값이 정본이다.**"
              " `matrix.md` 에 옳은 값이 있는데 본문만 옛 값인 자리가 있었다.")
        problems += 1
    elif adj_seen:
        print(f"서술형 인접 쌍 {adj_seen}개가 정본과 같다.")
    else:
        print("`A ↔ B N개` 형태의 서술이 없다 — 표 안의 행렬은 이 축이 보지 못한다"
              "(아래 \"검사하지 않은 축\").")

    # ── ⑤-c 정본 근거의 **식별자**가 본문에 있는가 ─────────────────────────
    # 정본은 고쳤고 HTML 이 안 받은 자리가 두 산출물에서 났고, 한 건은 **검토자 발견이 그대로
    # 되돌려졌다**(정본 cites 넷 중 하나가 본문에 없어 표면의 대상이 좁아졌다).
    # 인용 문장 전체로 대조하면 마크다운 표기 차이로 거의 다 걸린다 — **식별자만** 본다.
    # 코드 토큰·요건 ID 는 표기가 바뀌지 않으므로 없으면 진짜 누락이다.
    print("\n## 정본 근거의 식별자가 본문에 있는가\n")
    TOKEN = re.compile(r"`([A-Za-z_][\w.\-/]{5,40})`"          # 백틱 안의 코드
                       r"|\b([A-Z]{2,}[-_][A-Z0-9]{2,}(?:[-_][A-Z0-9]+)*)\b"  # FR-M5-04 계열
                       r"|\b([a-z][a-zA-Z]{4,}[A-Z][a-zA-Z]{2,})\b")          # camelCase
    body = " ".join(text_lines)
    tok_missing = []
    for s_ in surfaces:
        seen = set()
        for c in s_.get("cites", []):
            for m in TOKEN.finditer(str(c)):
                tok = next(g for g in m.groups() if g)
                if tok in seen or tok in body:
                    continue
                seen.add(tok)
                tok_missing.append((s_.get("id"), tok))
    if tok_missing:
        print("**아래 식별자가 `surfaces.json` 의 근거에는 있고 본문에는 없다.**"
              " 정본만 고치고 HTML 을 안 고친 자리다 — 검토 반영에서 가장 자주 난다.\n")
        print("| 표면 | 본문에 없는 식별자 |")
        print("|---|---|")
        for sid_, tok in tok_missing[:25]:
            print(f"| {sid_} | `{tok}` |")
        if len(tok_missing) > 25:
            print(f"\n… 그 밖 {len(tok_missing) - 25}건")
        print("\n**표면의 대상이 좁아졌는지 본다.** 근거에 있는 식별자가 본문에 없으면 그"
              " 표면이 원래 담던 것보다 적게 말하고 있다.")
        problems += 1
    else:
        print("정본 근거의 식별자가 전부 본문에서 확인된다.")

    # ── ⑥ 라벨 없는 숫자 ─────────────────────────────────────────────────
    # 표 셀의 맨 숫자와 *"합이 88이다"* 는 라벨이 없어 위 축에 걸리지 않는다. 한 산출물이
    # 표면 62개 시절 값(33·17·16·8·6)을 쌍별 표에 남겼고 스크립트는 "0건" 을 냈다.
    bare = []
    if not args.no_bare:
        # 갈래별 관여 수는 넣지 않는다 — 값이 많아 거의 모든 숫자가 후보로 걸린다(실측
        # 106건). 늦게 추가한 표면이 어긋나게 만드는 것은 **총계와 상태별 개수**다.
        canon = defaultdict(list)
        for k, v in list(expect.items()) + list(strength.items()):
            if v:
                canon[v].append(str(k))
        for i, raw in enumerate(lines, 1):
            for m in CELL.finditer(raw):
                inner = strip_tags(m.group(1)).strip()
                if not re.fullmatch(r"\d{1,4}", inner):
                    continue
                got = int(inner)
                for v, labels in canon.items():
                    if got != v and abs(got - v) <= args.near:
                        bare.append((i, got, v, " / ".join(labels[:3]), "표 셀"))
        loose = re.compile(r"(?:합|총|모두|전체)\s*(?:이|가|은|는)?\s*(\d{1,3})")
        for i, t in enumerate(text_lines, 1):
            for m in loose.finditer(t):
                got = int(m.group(1))
                after = t[m.end():m.end() + 6]
                if UNIT_AFTER.match(after):
                    continue
                for v, labels in canon.items():
                    if got != v and abs(got - v) <= args.near:
                        bare.append((i, got, v, " / ".join(labels[:3]), "합계 서술"))

    print("\n## 라벨 없는 숫자 — 눈으로 가릴 후보\n")
    if args.no_bare:
        print("`--no-bare` 로 껐다.")
    elif bare:
        print(f"정본 값과 **±{args.near} 안**에서 다른 숫자다. **정당한 값이 많이 섞인다**"
              " — 표 셀은 다른 축의 수일 수 있다. 다만 표면을 늦게 추가했다면 여기부터 본다.\n")
        print("| 행 | 본문 | 정본 후보 | 그 값의 뜻 | 자리 |")
        print("|---|---|---|---|---|")
        # 차이가 작은 것부터 — 늦게 추가한 표면 때문에 어긋난 값이 위에 온다
        for i, got, v, labels, kind in sorted(set(bare),
                                              key=lambda r: (abs(r[1] - r[2]), r[0]))[:40]:
            print(f"| {i} | **{got}** | {v} | {labels} | {kind} |")
        if len(set(bare)) > 40:
            print(f"\n… 그 밖 {len(set(bare)) - 40}건")
    else:
        print("표 셀·합계 서술에 정본 근처의 다른 숫자가 없다.")

    # ── 마무리 — 통과 신호의 뜻을 좁힌다 ──────────────────────────────────
    # 이 스크립트가 다섯 산출물에 "0건" 을 내는 동안 채점자들은 26곳을 찾았다. 그때 런들은
    # 통과 신호를 받고 눈으로 다시 보지 않았다. 그래서 **검사하지 않은 축을 항상 찍는다.**
    unchecked = [
        "카드 본문·도해 주석 안의 수치 (*\"A 경계 통과 40\"* — 라벨이 표와 다르다)",
        "**표 안의 인접 행렬**(행·열 라벨이 붙은 격자). 서술형 `A ↔ B N개` 는 위에서 봤지만"
        " 격자 셀은 못 본다 — 한 산출물이 **19쌍을 옛 값으로 굳혔다**",
        "손으로 센 부분합 중 **정본 키가 아닌 라벨**을 쓴 것 (*\"종이 21\"* · *\"Must 13\"*)",
        "구간 배분·경계 통과처럼 `surfaces.json` 에서 파생되지 않는 계산값",
        "ID 목록의 구성 (개수는 맞고 **다른 ID 가 섞인** 자리)",
        "서술의 논리 — 같은 사실을 두 곳에서 반대로 적은 것",
        "**ID 열거의 축 일관성** — *\"층 1 … (C1 · C62 · C67)\"* 에서 그 ID 들이 정말 같은 층인가."
        " 채점에서 이 축이 다섯 건을 냈고 자리가 일정하다 — **카드 · 부록 트리 · 층 도해**."
        " **기계로 두 번 만들어 두 번 기각했다**: 행 단위로 보면 문장 경계를 못 지켜"
        " (*\"C12·C52 는 층 1·2 뒤에 와야\"* 같은 순서 표현, *\"①…층 1 안에서 닫히고 ②이력 이동"
        "(C10·C25)\"* 처럼 다른 항목의 ID) 오탐이 6/7 이다. 표를 빼고 ID 2개 이상 창으로 좁혀도"
        " 그렇다 → **카드·목록·트리를 단위로 손으로 훑는다.** 각 카드의 라벨(*\"최상 · 층 1\"*)과"
        " 그 카드가 담은 ID 의 정본 층을 대 보는 일이다",
        "층·단계의 **교차 부분합**(*\"사전 준비 13\"* ↔ 정본 12). 단일 축은 위에서 봤다",
    ]
    if unchecked_extra:
        unchecked.insert(0, "**층·단계별 개수** — `surfaces.json` 에 `layer`·`aidlc` 가 없어"
                            " 이번엔 껐다. 실측에서 남은 전파 누락이 **전부** 이 축이었다")
    print("\n---\n")
    print(f"**어긋난 묶음 {problems}개**"
          + (f" · 눈으로 가릴 후보 {len(set(bare))}건" if bare else "")
          + ".\n")
    print("**이 스크립트가 검사하지 않은 축이다 — 0건은 통과가 아니다.**\n")
    for u in unchecked:
        print(f"- {u}")
    print("\n표면을 늦게 추가했다면 위 축을 **직접 훑는다.** 실측에서 이 스크립트가 다섯"
          " 산출물에 `0건` 을 내는 동안 채점자들이 **26곳**을 찾았고, 그 대부분이 위 목록이다.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
