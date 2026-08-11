"""코드 하이라이팅을 **서버에서 인라인 스타일로** 끝낸다.

블로그는 브라우저에서 highlight.js가 색을 칠하지만(templates/blog/detail.html),
Blogger 글 본문에는 그런 스크립트를 넣을 수 없다. 그래서 Pygments로 미리 칠하고
`noclasses=True`로 색을 span의 style 속성에 직접 박는다 — 테마 수정 없이 동작한다.
"""

from __future__ import annotations

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

    background_color = theme.CODE_BG

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


# nowrap=True — Pygments가 두르는 <div class="highlight"><pre>를 받지 않는다.
# 껍데기는 theme.PRE_STYLE로 우리가 직접 만든다.
_FORMATTER = HtmlFormatter(style=BlogDarkDimmed, noclasses=True, nowrap=True)


def highlight(code: str, lang: str | None):
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
    # Pygments는 끝에 개행을 하나 붙인다. 코드블록 마지막 빈 줄로 보여서 떼어낸다.
    return _pygments_highlight(code, lexer, _FORMATTER).rstrip("\n"), None


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
