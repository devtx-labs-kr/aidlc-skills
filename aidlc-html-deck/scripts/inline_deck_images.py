#!/usr/bin/env python3
"""inline_deck_images.py — fold local <img src> files into base64 data URIs.

    uv run .claude/skills/aidlc-html-deck/scripts/inline_deck_images.py deck.html
    uv run .claude/skills/aidlc-html-deck/scripts/inline_deck_images.py deck.html --out deck-standalone.html

A deck authored in this repo can reference sibling images (QR codes, diagrams)
with a relative `src`. That is fine for presenting from the repo and fine for
`deck_to_pdf.py`, because Chrome resolves `file://` relatives. It is NOT fine
when the `.html` is handed to someone on its own — the images silently vanish.

This inlines them so the file keeps the skill's self-contained promise. Fonts
stay on their CDNs; those are the one documented exception.

Default behaviour rewrites in place. Pass --out to keep the authoring copy with
readable `src` paths and ship the inlined one.

Stdlib only.
"""
from __future__ import annotations

import argparse
import base64
import mimetypes
import re
import sys
from pathlib import Path

SRC = re.compile(r'src\s*=\s*"(?!data:|https?:)([^"]+)"')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("html", type=Path)
    ap.add_argument("--out", type=Path, help="기본값: 제자리 수정")
    a = ap.parse_args()

    html = a.html.resolve()
    if not html.exists():
        sys.exit(f"없는 파일: {html}")
    text = html.read_text(encoding="utf-8")
    base = html.parent

    inlined, missing, saved_bytes = [], [], 0

    def sub(m: re.Match[str]) -> str:
        nonlocal saved_bytes
        rel = m.group(1)
        p = (base / rel).resolve()
        if not p.exists():
            missing.append(rel)
            return m.group(0)
        mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        data = base64.b64encode(p.read_bytes()).decode("ascii")
        inlined.append((rel, p.stat().st_size))
        saved_bytes += len(data)
        return f'src="data:{mime};base64,{data}"'

    out_text = SRC.sub(sub, text)

    for rel, size in inlined:
        print(f"  ✓ {rel}  ({size / 1024:.1f} KB)")
    for rel in missing:
        print(f"  ✗ 못 찾음: {rel}")

    if not inlined:
        print("인라인할 로컬 이미지가 없다 — 이미 자기완결이다.")
        return 1 if missing else 0

    dest = (a.out or html).resolve()
    dest.write_text(out_text, encoding="utf-8")
    print(f"▸ {len(inlined)}개 인라인 → {dest.name} "
          f"(+{saved_bytes / 1024:.0f} KB base64)")
    if missing:
        print("✗ 못 찾은 이미지가 있다 — 배포 전에 해결하라.")
        return 1
    print("✓ 완료 — 이제 .html 단독으로 배포 가능하다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
