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
<style>body{{margin:0;padding:40px 24px;{surface}}}
main{{max-width:780px;margin:0 auto;}}</style>
{snippet}
</head>
<body><main>{body}</main></body>
</html>
"""

# 미리보기 배경 — 팔레트가 가정하는 Blogger 테마를 흉내 낸다.
# inherit은 글자색을 지정하지 않으므로, 어두운 테마에 얹은 모습으로 보여준다.
_PREVIEW_SURFACE = {
    "light": "background:#fff;",
    "dark": "background:#0C1018;",
    "inherit": "background:#0C1018;color:#D7DEEC;",
}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="마크다운을 Blogger용 HTML로 변환한다 (--reverse면 그 반대).")
    parser.add_argument("source", type=Path, help="변환할 .md 파일 (--reverse면 .html)")
    parser.add_argument("--reverse", action="store_true",
                        help="HTML → 마크다운. Blogger에 올린 글을 되찾아올 때 쓴다. "
                             "--palette·--output·--preview는 이때 의미가 없다")
    parser.add_argument("--base-url", default="", help="상대경로 이미지/링크에 붙일 기준 URL")
    parser.add_argument("--preview", action="store_true",
                        help="브라우저로 열어볼 수 있는 완전한 HTML 문서도 함께 저장")
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="저장 위치 (기본: 원본과 같은 폴더)")
    parser.add_argument("--keep-newlines", action="store_true",
                        help="줄바꿈 안전 모드를 끈다 (Blogger 외 용도)")
    parser.add_argument("--output", choices=["inline", "css"], default="inline",
                        help="inline: 스타일을 style= 속성에 박는다(기본). "
                             "css: 맨 앞에 <style> 블록을 둔다 — 본문이 짧아지고 조판이 "
                             "정확해지지만 RSS 피드에서는 서식이 빠진다")
    parser.add_argument("--palette", choices=["light", "dark", "inherit"], default="light",
                        help="Blogger 테마 배경에 맞춘다. 검은 테마면 dark, "
                             "테마를 바꿀 수 있으면 inherit (기본: light)")
    args = parser.parse_args(argv)

    if not args.source.is_file():
        print(f"파일을 찾을 수 없습니다: {args.source}", file=sys.stderr)
        return 1

    text = args.source.read_text(encoding="utf-8")
    out_dir = args.out_dir or args.source.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.reverse:
        return _reverse(text, args, out_dir)

    result = convert(
        text,
        image_base_url=args.base_url,
        safe_linebreaks=not args.keep_newlines,
        palette=args.palette,
        output=args.output,
    )

    stem = args.source.stem

    paste_path = out_dir / f"{stem}.blogger.html"
    paste_path.write_text(result.html, encoding="utf-8")
    written = [paste_path]

    if args.preview:
        preview_path = out_dir / f"{stem}.preview.html"
        preview_path.write_text(
            _PREVIEW_DOC.format(
                title=stem,
                snippet=THEME_SNIPPET,
                body=result.html,
                surface=_PREVIEW_SURFACE.get(args.palette, _PREVIEW_SURFACE["light"]),
            ),
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


def _reverse(html: str, args, out_dir: Path) -> int:
    """HTML → 마크다운. bs4는 여기서만 필요하므로 늦게 import한다."""
    from converter.to_markdown import to_markdown

    result = to_markdown(html, base_url=args.base_url)
    path = out_dir / f"{args.source.stem}.md"
    if path.resolve() == args.source.resolve():
        # 원본이 .md인데 --reverse를 준 경우. 덮어쓰면 원문이 사라진다.
        path = out_dir / f"{args.source.stem}.from-html.md"
    path.write_text(result.markdown, encoding="utf-8")

    stats = result.stats
    print(f"변환 완료 — {stats['characters']:,}자 · {stats['lines']}줄 · "
          f"코드블록 {stats['code_blocks']}개 · 이미지 {stats['images']}개 · "
          f"표 {stats['tables']}개")
    print(f"  저장: {path}")
    for warning in result.warnings:
        print(f"  [확인] {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
