#!/usr/bin/env python3
"""문서에 흩어진 불일치 후보를 기계로 좁힌다 — 용어 · 수치 · 식별자 형식 세 축.

채점에서 이 유형을 반복해 놓쳤다. `contract-sweep.md` 가 위험한 낱말을 예시로 적어 두었는데도
놓쳤으므로 **지시만으로는 잡히지 않는다.** 봐야 할 자리를 목록으로 강제한다.

이 스크립트는 판정하지 않는다. **대조할 후보를 좁혀 줄 뿐이다.**

    python3 term_sweep.py <입력 디렉터리|파일…> [--axis all|term|number|format] [--top N] [--json]

세 축이 겨냥하는 것.

| 축 | 찾는 것 | 실패 예 |
|---|---|---|
| `term` | 같은 낱말이 다른 대상을 가리킨다 (문서 3개 이하에서만) | '대시보드' 가 분석 대시보드 / 모니터링 그리드 |
| `number` | 같은 단위에 다른 값이 붙어 있다 | 상태가 8단계 / 9단계 / 7개 · 10,000행 / 300행 |
| `format` | 같은 접두의 식별자 형식이 다르다 | `TC-YYYYMMDD-NNN` / `TC-202606-031` |

PDF 는 읽지 못한다 — 본문을 직접 읽어서 같은 축으로 대조한다.
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

SECTION = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$")

# 범위 제외 절. 여기 나온 낱말이 다른 문서 본문에도 나오면 같은 말이 다른 것을 가리킬
# 위험이 가장 크다 — 한쪽은 "빼는 것", 다른 쪽은 "만드는 것" 을 그 낱말로 부른다.
# 실측에서 '대시보드' 가 이 모양이었다(제외 목록의 분석 대시보드 vs 본문의 모니터링 그리드).
EXCLUDE_HINT = re.compile(
    r"제외|미포함|범위\s*밖|범위에서\s*빠|보류|다음\s*차수|이번에는\s*하지|"
    r"won'?t|out\s*of\s*scope|not\s*in\s*scope|non-?goal", re.I)

# ── term 축 ────────────────────────────────────────────────────────────────
WORD = re.compile(r"[가-힣]{2,12}")
JOSA = (
    "으로써", "으로서", "이라는", "라는", "에서는", "에서의", "에서", "으로", "로서", "로써",
    "까지", "부터", "에게", "한테", "이라", "라고", "이고", "하고", "와의", "과의",
    "만을", "만이", "만은", "들의", "들을", "들이", "들은",
    "은", "는", "이", "가", "을", "를", "의", "에", "도", "과", "와", "로", "만", "며",
)
VERBAL = ("한다", "된다", "있다", "없다", "이다", "하다", "받는", "하는", "되는", "이며", "하며")

# 문서에 흔하고 경계와 무관한 말. UI 부품 이름이 특히 노이즈다.
STOP = {
    # 접속·지시
    "그리고", "그러나", "하지만", "또는", "때문", "경우", "위해", "통해", "대한", "대해",
    "다음", "이하", "이상", "미만", "초과", "동일", "각각", "모든", "해당", "관련", "포함",
    "제외", "이때", "여기", "전체", "일부", "기타", "이번", "현재", "기존", "신규", "최근",
    # 동작·서술
    "저장", "확인", "사용", "제공", "가능", "필요", "표시", "입력", "출력", "선택", "변경",
    "추가", "삭제", "수정", "생성", "조회", "등록", "관리", "처리", "실행", "적용", "구현",
    "개발", "작업", "완료", "시작", "종료", "이동", "복사", "검색", "정렬", "설정", "지정",
    # 문서 메타
    "요구", "사항", "요구사항", "문서", "절차", "과정", "결과", "내용", "방식", "형태",
    "구조", "단위", "기준", "정의", "설명", "예시", "참고", "비고", "목적", "범위", "대상",
    "조건", "규칙", "항목", "기능", "이름", "번호", "목록", "우선", "순위", "우선순위",
    # UI 부품 — 화면 설계서에서 폭발한다
    "버튼", "제목", "필터", "컬럼", "그리드", "레이아웃", "패널", "툴바", "헤더", "푸터",
    "메뉴", "탭", "모달", "팝업", "다이얼로그", "체크박스", "드롭다운", "링크", "아이콘",
    "카드", "배지", "토스트", "스크롤", "페이지", "화면", "영역", "패널", "필드", "라벨",
    "텍스트", "이미지", "파일", "폴더", "트리", "차트", "그래프", "테이블", "행", "열",
    # 역할·조직
    "사용자", "관리자", "고객", "담당자", "사람", "팀", "부서", "회사",
    # 범용 도메인
    "데이터", "정보", "시스템", "서비스", "상태", "값", "코드", "타입", "종류", "속성",
}


def strip_josa(w: str) -> str:
    for j in JOSA:
        if len(w) > len(j) + 1 and w.endswith(j):
            return w[: -len(j)]
    return w


# ── number 축 ──────────────────────────────────────────────────────────────
UNITS = ("단계", "시간", "분", "초", "일", "주", "개월", "년", "행", "건", "개", "명",
         "배", "자", "회", "차", "층", "%", "px", "ms", "MB", "KB", "GB", "TB")
NUM_UNIT = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(" + "|".join(UNITS) + r")(?![가-힣A-Za-z])")

# ── format 축 ──────────────────────────────────────────────────────────────
IDFMT = re.compile(r"\b([A-Z]{2,6})-([A-Za-z0-9]{1,12}(?:-[A-Za-z0-9]{1,12}){0,3})\b")


def shape(s: str) -> str:
    """식별자 본체를 형태로 정규화한다 — 숫자는 N, 대문자는 A, 소문자는 a."""
    out = []
    for ch in s:
        out.append("N" if ch.isdigit() else "A" if ch.isupper() else "a" if ch.isalpha() else ch)
    # 같은 문자 반복을 길이로 접는다 — NNNNNNNN 과 NNNNNN 은 다른 형태로 남긴다
    return "".join(out)


def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"  건너뜀 — {p.name}: {e}", file=sys.stderr)
        return ""


def collect(targets):
    files = []
    for t in targets:
        p = Path(t)
        if p.is_dir():
            files += sorted(q for q in p.rglob("*.md") if q.is_file())
        elif p.is_file():
            files.append(p)
        else:
            print(f"경로를 찾을 수 없다 — {t}", file=sys.stderr)
    if any(Path(t).is_dir() and list(Path(t).rglob("*.pdf")) for t in targets):
        print("주의 — PDF 가 있다. 이 스크립트는 읽지 못하므로 본문을 직접 대조한다.",
              file=sys.stderr)
    return files


def scan(files, exclude_docs=()):
    """세 축의 관측을 한 번의 순회로 모은다."""
    # term: {낱말: {문서: {절: [수식어…]}}}
    term = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    # 그 낱말이 범위 제외 절에서 쓰였는가 — {낱말: {"문서 §절"}}
    excluded = defaultdict(set)
    # number: {단위: {값: [(문서, 절, 문맥)…]}}
    number = defaultdict(lambda: defaultdict(list))
    # format: {접두: {형태: [(문서, 절, 실례)…]}}
    fmt = defaultdict(lambda: defaultdict(list))

    for f in files:
        section = "(제목 없음)"
        in_exclude = False
        exclude_depth = 0
        for line in read_text(f).splitlines():
            m = SECTION.match(line)
            if m:
                depth = len(m.group(1))
                section = m.group(2).strip()[:56]
                # 제외는 **하위 절로 물려받는다.** `## 제외 기능` 아래 `### 1. 결제 관련` 은
                # 제목에 제외라는 말이 없어도 제외다. 깊이를 보지 않고 절마다 다시 판정하면
                # 제외 목록 본문이 통째로 제외에서 빠진다 — 실측에서 `결제`·`대시보드` 가
                # 하나도 제외로 잡히지 않았고, 그 탓에 제외 항목이 두 판 연속 충돌로 올랐다.
                if EXCLUDE_HINT.search(section):
                    in_exclude, exclude_depth = True, depth
                elif in_exclude and depth <= exclude_depth:
                    in_exclude, exclude_depth = False, 0
                continue
            if not line.strip():
                continue

            words = WORD.findall(line)
            for i, raw in enumerate(words):
                w = strip_josa(raw)
                if len(w) < 2 or w in STOP or w.endswith(VERBAL):
                    continue
                mod = strip_josa(words[i - 1]) if i else ""
                if mod in STOP or len(mod) < 2:
                    mod = ""
                term[w][f.name][section].append(mod)
                if in_exclude or f.name in exclude_docs:
                    excluded[w].add(f"{f.name} §{section}")

            for val, unit in NUM_UNIT.findall(line):
                ctx = line.strip()
                if len(ctx) > 78:
                    j = ctx.find(val)
                    ctx = ("…" if j > 30 else "") + ctx[max(0, j - 30): j + 48] + "…"
                number[unit][val.replace(",", "")].append((f.name, section, ctx))

            for pre, body in IDFMT.findall(line):
                fmt[pre][shape(body)].append((f.name, section, f"{pre}-{body}"))

    return term, number, fmt, excluded


def rank_term(term, min_docs, min_sections, excluded):
    rows = []
    for w, docs in term.items():
        nsec = sum(len(s) for s in docs.values())
        if len(docs) < min_docs or nsec < min_sections:
            continue
        mods = {m for d in docs.values() for ms in d.values() for m in ms if m}
        # 1순위 신호 — **범위 제외 절에 나오면서 다른 절에도 나오는 낱말.**
        # 한쪽은 "빼는 것" 을 그 낱말로 부르고 다른 쪽은 "만드는 것" 을 그렇게 부른다.
        # 실측에서 놓쳤던 '대시보드' 가 정확히 이 모양이었다.
        ex = excluded.get(w, set())
        risky = bool(ex) and nsec > len(ex)
        # 2순위 — 수식어 다양성. 문서 수로 정렬하면 UI 공통어가 위로 온다
        rows.append((risky, len(mods), len(docs), nsec, w, docs, sorted(mods), sorted(ex)))
    rows.sort(key=lambda r: (not r[0], -r[1], -r[2], -r[3], r[4]))
    return rows


def rank_number(number, max_values):
    rows = []
    for unit, vals in number.items():
        if not 2 <= len(vals) <= max_values:
            continue
        rows.append((len(vals), unit, vals))
    rows.sort(key=lambda r: (r[0], r[1]))
    return rows


def rank_format(fmt):
    rows = []
    for pre, shapes in fmt.items():
        if len(shapes) < 2:
            continue
        rows.append((len(shapes), pre, shapes))
    rows.sort(key=lambda r: (-r[0], r[1]))
    return rows


def main():
    ap = argparse.ArgumentParser(description="용어·수치·식별자 형식의 불일치 후보를 좁힌다")
    ap.add_argument("targets", nargs="+", help="입력 디렉터리 또는 .md 파일")
    # 기본은 number·format 만이다. term 축은 문서가 늘면 노이즈가 지배한다 —
    # 실측에서 2문서 집합은 후보 9개 중 1개가 진짜였고, 5문서 집합은 25개 전부 거짓이었다
    # (전부 폴리세미거나 같은 대상의 다른 측면). 소형 집합에서만 --axis all 로 켠다.
    ap.add_argument("--axis", choices=("all", "term", "number", "format", "ids"),
                    default="ids",
                    help="기본 ids = number+format. term 은 문서 3개 이하에서만 값어치가 있다")
    ap.add_argument("--min-docs", type=int, default=1,
                    help="term — 이 개수 이상의 문서에 나오는 낱말만 (기본 1: 한 문서 안의 혼용도 본다)")
    ap.add_argument("--min-sections", type=int, default=3,
                    help="term — 이 개수 이상의 절에 나오는 낱말만 (기본 3)")
    ap.add_argument("--exclude-doc", nargs="*", default=[],
                    help="범위 제외 목록 문서의 파일명. 그 문서에 나온 낱말이 다른 문서 "
                         "본문에도 나오면 term 축에서 맨 위로 올린다 — 한쪽이 빼기로 한 것과 "
                         "다른 쪽이 만들 것을 같은 말로 부르는 자리다")
    ap.add_argument("--max-values", type=int, default=8,
                    help="number — 값이 이 개수를 넘는 단위는 노이즈로 보고 뺀다 (기본 8)")
    ap.add_argument("--top", type=int, default=25, help="term 축 출력 개수 (기본 25)")
    ap.add_argument("--json", action="store_true", help="JSON 으로 낸다")
    a = ap.parse_args()

    files = collect(a.targets)
    if not files:
        print("읽을 .md 파일이 없다.", file=sys.stderr)
        return 1

    term, number, fmt, excluded = scan(files, set(a.exclude_doc))
    t_rows = rank_term(term, a.min_docs, a.min_sections, excluded)[: a.top]
    n_rows = rank_number(number, a.max_values)
    f_rows = rank_format(fmt)

    if a.json:
        print(json.dumps({
            "files": [f.name for f in files],
            "term": [{"term": w, "modifiers": mods, "docs": nd, "sections": ns,
                      "in_exclusion_section": ex, "priority": "high" if risky else "normal",
                      "where": {d: list(s) for d, s in docs.items()}}
                     for risky, _, nd, ns, w, docs, mods, ex in t_rows],
            "number": [{"unit": u, "values": sorted(v, key=lambda x: float(x)),
                        "where": {k: [(d, s) for d, s, _ in w] for k, w in v.items()}}
                       for _, u, v in n_rows],
            "format": [{"prefix": p,
                        "shapes": {k: {"examples": [x[2] for x in w][:3],
                                       "where": [(d, s) for d, s, _ in w][:3]}
                                   for k, w in sh.items()}}
                       for _, p, sh in f_rows],
        }, ensure_ascii=False, indent=1))
        return 0

    print(f"# 불일치 후보 — 파일 {len(files)}개\n")
    print("**판정이 아니라 대조할 자리다.** 후보마다 원문 절을 열어 같은 대상인지 직접 읽는다.")
    print("정의·값이 다르면 Contract 이고 상태는 **충돌**이다. 참여 표기에 절 번호까지 적는다.\n")

    if a.axis in ("all", "ids", "number"):
        print(f"## 같은 단위, 다른 값 — {len(n_rows)}건\n")
        if not n_rows:
            print("없다.\n")
        for nv, unit, vals in n_rows:
            order = sorted(vals, key=lambda x: float(x))
            print(f"### `{unit}` — 값 {nv}개: {' / '.join(order)}\n")
            for v in order:
                for d, s, ctx in vals[v][:2]:
                    print(f"- **{v}{unit}** `{d}` §{s} — {ctx}")
            print()

    if a.axis in ("all", "ids", "format"):
        print(f"## 같은 접두, 다른 식별자 형식 — {len(f_rows)}건\n")
        if not f_rows:
            print("없다.\n")
        for ns_, pre, shapes in f_rows:
            print(f"### `{pre}-` — 형태 {ns_}개\n")
            for sh, where in sorted(shapes.items(), key=lambda kv: -len(kv[1])):
                ex = where[0]
                others = {d for d, _, _ in where}
                print(f"- `{sh}` ({len(where)}회, 문서 {len(others)}개) 예 `{ex[2]}` "
                      f"— `{ex[0]}` §{ex[1]}")
            print()

    if a.axis in ("all", "term"):
        print(f"## 같은 낱말, 다른 대상 — 후보 {len(t_rows)}개\n")
        print("수식어가 여럿인 낱말이 위에 온다. 문서 수로 정렬하면 UI 공통어가 올라와 못 쓴다.\n")
        if len(files) > 3:
            print(f"> **경고 — 문서가 {len(files)}개다. 이 축은 대형 집합에서 무력하다.**")
            print("> 실측에서 5문서 집합의 후보 25개가 **전부 거짓**이었다(폴리세미이거나 같은")
            print("> 대상의 다른 측면). 2문서 집합에서는 9개 중 1개가 진짜였다.")
            print("> 아래를 훑되 시간을 쓰지 않는다 — `number`·`format` 축이 수확이 높다.\n")
        nrisky = sum(1 for r in t_rows if r[0])
        if nrisky:
            print(f"**제외 절에도 나오는 낱말 {nrisky}개를 맨 위에 뒀다 — 여기를 먼저 본다.**")
            print("한쪽이 빼기로 한 것과 다른 쪽이 만들 것을 같은 말로 부르는 자리다.\n")
        print("| | 낱말 | 수식어 | 문서 | 절 | 제외 절 | 어디에 |")
        print("|---|---|---|---|---|---|---|")
        for risky, _, nd, ns, w, docs, mods, ex in t_rows:
            where = " · ".join(
                f"`{d}`: " + ", ".join(list(s)[:2]) + ("…" if len(s) > 2 else "")
                for d, s in sorted(docs.items(), key=lambda kv: -len(kv[1]))[:2]
            )
            print(f"| {'**주의**' if risky else ''} | **{w}** "
                  f"| {', '.join(mods[:4])}{'…' if len(mods) > 4 else ''} "
                  f"| {nd} | {ns} | {', '.join(ex[:2]) or '—'} | {where} |")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
