"""파일 단위 변환 — 웹 UI를 띄우기 애매할 때 쓴다.

    python cli.py 글.md                         → 글.blogger.html (붙여넣기용)
    python cli.py 글.md --preview               → 글.preview.html 도 함께 (브라우저 확인용)
    python cli.py 글.md --base-url https://...  → 상대경로 이미지를 절대 URL로

app.py와 같은 `converter` 패키지를 쓴다 — 웹 UI와 결과가 다를 일이 없다.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from converter import convert
from converter.snippet import THEME_SNIPPET

_PREVIEW_DOC = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{title}</title>
<style>body{{margin:0;padding:40px 24px;background:#fff;}}
main{{max-width:780px;margin:0 auto;}}</style>
{snippet}
</head>
<body><main>{body}</main></body>
</html>
"""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="마크다운을 Blogger용 HTML로 변환한다.")
    parser.add_argument("source", type=Path, help="변환할 .md 파일")
    parser.add_argument("--base-url", default="", help="상대경로 이미지/링크에 붙일 기준 URL")
    parser.add_argument("--preview", action="store_true",
                        help="브라우저로 열어볼 수 있는 완전한 HTML 문서도 함께 저장")
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="저장 위치 (기본: 원본과 같은 폴더)")
    parser.add_argument("--keep-newlines", action="store_true",
                        help="줄바꿈 안전 모드를 끈다 (Blogger 외 용도)")
    args = parser.parse_args(argv)

    if not args.source.is_file():
        print(f"파일을 찾을 수 없습니다: {args.source}", file=sys.stderr)
        return 1

    text = args.source.read_text(encoding="utf-8")
    result = convert(
        text,
        image_base_url=args.base_url,
        safe_linebreaks=not args.keep_newlines,
    )

    out_dir = args.out_dir or args.source.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = args.source.stem

    paste_path = out_dir / f"{stem}.blogger.html"
    paste_path.write_text(result.html, encoding="utf-8")
    written = [paste_path]

    if args.preview:
        preview_path = out_dir / f"{stem}.preview.html"
        preview_path.write_text(
            _PREVIEW_DOC.format(title=stem, snippet=THEME_SNIPPET, body=result.html),
            encoding="utf-8",
        )
        written.append(preview_path)

    stats = result.stats
    print(f"변환 완료 — {stats['characters']:,}자 · 코드블록 {stats['code_blocks']}개 · "
          f"이미지 {stats['images']}개 · 다이어그램 {stats['mermaid']}개 · "
          f"개행 {stats['newlines']}개")
    for path in written:
        print(f"  저장: {path}")
    for warning in result.warnings:
        print(f"  [확인] {warning}")
    for note in result.notes:
        print(f"  [안내] {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
