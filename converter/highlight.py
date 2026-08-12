"""코드 하이라이팅을 **서버에서** 끝낸다.

블로그는 브라우저에서 highlight.js가 색을 칠하지만(templates/blog/detail.html),
Blogger 글 본문에는 그런 스크립트를 넣을 수 없다. 그래서 Pygments로 미리 칠한다.
테마 수정 없이 동작한다.

출력 방식에 따라 색을 두는 자리가 다르다.

- 인라인 모드 — `noclasses=True`. 색을 span의 style 속성에 직접 박는다.
- `<style>` 블록 모드 — 클래스만 남기고 색은 `style_defs()`가 만드는 스타일시트로 뺀다.
"""

from __future__ import annotations

import re

from pygments import highlight as _pygments_highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.style import Style
from pygments.token import (
    Comment,
    Error,
    Generic,
    Keyword,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Token,
)

from . import theme


class BlogDarkDimmed(Style):
    """블로그 코드블록과 같은 색.

    블로그는 highlight.js의 **github-dark-dimmed** 테마를 blog.css의
    `--code-bg`(#11162A) 위에 얹어 쓴다(blog.css:435). 그 팔레트를 Pygments 토큰에
    옮긴 것이라, 같은 코드가 블로그와 Blogger에서 같은 색으로 보인다.
    """

    # nowrap=True라 이 값이 출력에 나가지는 않는다(껍데기는 theme.pre_style이 만든다).
    # Pygments Style이 요구하는 필드라 라이트 팔레트 값을 대표로 둔다.
    background_color = theme.LIGHT.code_bg

    styles = {
        Token: theme.CODE_FG,          # #adbac7
        Comment: "italic #768390",
        Comment.Preproc: "#6cb6ff",
        Keyword: "#f47067",
        Keyword.Type: "#f69d50",
        Name: theme.CODE_FG,
        Name.Builtin: "#f69d50",
        Name.Function: "#dcbdfb",
        Name.Class: "#f69d50",
        Name.Decorator: "#dcbdfb",
        Name.Tag: "#8ddb8c",
        Name.Attribute: "#6cb6ff",
        Name.Constant: "#6cb6ff",
        String: "#96d0ff",
        String.Escape: "#96d0ff",
        Number: "#6cb6ff",
        Operator: "#f47067",
        Punctuation: theme.CODE_FG,
        Generic.Inserted: "#b4f1b4",
        Generic.Deleted: "#ffd8d3",
        Generic.Emph: "italic",
        Generic.Strong: "bold",
        Error: "#ff938a",
    }


_CSS_COMMENT = re.compile(r"/\*.*?\*/")

# nowrap=True — Pygments가 두르는 <div class="highlight"><pre>를 받지 않는다.
# 껍데기는 우리가 직접 만든다.
#
# 두 벌인 이유: 인라인 모드는 색을 span의 style에 박아야 하고(noclasses=True),
# <style> 블록 모드는 클래스만 남기고 색은 스타일시트로 뺀다 — 후자가 훨씬 짧다.
_INLINE_FORMATTER = HtmlFormatter(style=BlogDarkDimmed, noclasses=True, nowrap=True)
_CLASS_FORMATTER = HtmlFormatter(style=BlogDarkDimmed, nowrap=True)


def highlight(code: str, lang: str | None, *, inline_colors: bool = True):
    """(하이라이팅된 HTML, 경고 또는 None)을 돌려준다.

    언어를 모르면 색칠을 포기하고 원본을 이스케이프해서 그대로 쓴다 —
    글이 깨지는 것보다 색이 없는 게 낫다.
    """
    if not lang:
        return _escape(code), None
    try:
        lexer = get_lexer_by_name(lang, stripnl=False)
    except Exception:
        return _escape(code), f"코드블록 언어 '{lang}'를 Pygments가 몰라 색칠을 건너뛰었습니다."
    formatter = _INLINE_FORMATTER if inline_colors else _CLASS_FORMATTER
    # Pygments는 끝에 개행을 하나 붙인다. 코드블록 마지막 빈 줄로 보여서 떼어낸다.
    return _pygments_highlight(code, lexer, formatter).rstrip("\n"), None


def style_defs(scope: str) -> str:
    """`<style>` 블록에 넣을 문법 강조 규칙. 한 줄로 돌려준다.

    Pygments 클래스명은 `.k`·`.s1`처럼 짧아 그대로 두면 테마 CSS와 부딪친다.
    반드시 코드블록 선택자 안으로 한정해서 쓴다.

    ``get_style_defs``의 출력을 그대로 쓰면 안 된다. 넘긴 선택자와 **무관한 규칙을
    같이 뱉기 때문이다** — `pre { line-height: 125% }` 와 줄번호용 규칙 넷.
    앞의 것은 테마의 모든 코드블록 행간을 건드린다. 또 `{scope} { background: … }`도
    끼워 넣는데, 이 배경은 스타일 클래스에 박제된 값이라 팔레트별 코드 배경
    (`dark`는 더 어둡다)을 덮어써 버린다. 토큰 규칙(`{scope} .xxx`)만 남긴다.
    """
    keep = f"{scope} ."
    lines = [
        # Pygments가 규칙 뒤에 붙이는 `/* Comment */` 꼬리표를 뗀다.
        # 붙여넣을 본문에 들어갈 내용이라 설명 주석은 자리만 차지한다.
        _CSS_COMMENT.sub("", line).strip()
        for line in _CLASS_FORMATTER.get_style_defs(scope).splitlines()
        if line.strip().startswith(keep)
    ]
    # Blogger의 줄바꿈 자동 변환이 <style> 안이라고 봐주지 않는다 — 한 줄로 만든다.
    return " ".join(line for line in lines if line)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
