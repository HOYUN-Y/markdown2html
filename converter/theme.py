"""블로그 본문 조판을 인라인 스타일 표로 옮긴 것.

출처: django_blog_Enhanced/static/css/blog.css 의 `body.blog` 토큰과
`body.blog .article-body` 규칙. **main.css(.prose)가 아니다** — 그쪽은 포트폴리오
사이트용 오렌지 테마이고, blog.devprofessional.xyz 본문은 blog.css의
'Slate & Navy'를 쓴다.

Blogger 글 본문에는 우리 CSS를 넣을 데가 없어서 같은 값을 `style=` 속성에 직접 박는다.
그런데 **박는 순간 Blogger 테마의 밝기와 충돌할 수 있다** — 검은 테마 블로그에
라이트 팔레트를 박으면 본문이 배경에 묻힌다. 그래서 팔레트를 셋 준비했다.

- ``light``   — 밝은 배경 블로그용. blog.css 라이트 토큰
- ``dark``    — 검은 배경 블로그용. blog.css `html[data-theme="dark"]` 토큰
- ``inherit`` — 글자색을 **아예 지정하지 않는다.** Blogger 테마가 칠한다.
                어떤 테마에도 맞고 나중에 테마를 바꿔도 안 깨지지만,
                블로그와 똑같은 색은 포기한다.

CSS와 1:1로 못 옮기는 규칙이 둘 있고, 아래처럼 근사했다.

- `.article-body > * + * { margin-top: 1.2em }` — 인접 형제 선택자는 인라인 불가.
  → 블록 요소마다 `margin-bottom`으로 대체.
- `li + li { margin-top: .4em }` — 마찬가지. → 모든 `li`에 위아래 여백으로 대체.
"""

from __future__ import annotations

from dataclasses import dataclass

# main.css :root의 폰트 토큰. Blogger 테마에는 없을 수 있어 폴백을 길게 둔다.
FONT_BODY = (
    "'Pretendard','Space Grotesk',-apple-system,BlinkMacSystemFont,"
    "'Segoe UI','Apple SD Gothic Neo','Malgun Gothic',sans-serif"
)
FONT_MONO = (
    "'Space Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,"
    "'D2Coding',monospace"
)

#: 코드블록 글자색 — 블로그가 쓰는 highlight.js github-dark-dimmed의 본문 색.
#: 코드블록은 **두 테마 모두 어둡다**(blog.css:435 주석) — 팔레트를 타지 않는다.
CODE_FG = "#adbac7"


@dataclass(frozen=True)
class Palette:
    """한 벌의 색. `text`/`heading`이 None이면 색을 지정하지 않는다(테마 상속)."""

    name: str
    text: str | None
    text_muted: str | None
    heading: str | None
    accent: str          # h2 왼쪽 막대·링크. 상속 모드에서는 currentColor
    line: str            # 표·구분선
    quote_bg: str        # 인용구·인라인 코드 배경
    code_bg: str         # 코드블록 배경

    @property
    def inherits(self) -> bool:
        return self.text is None


LIGHT = Palette(
    name="light",
    text="#1A1F2B",
    text_muted="#5B6478",
    heading="#0D1220",
    accent="#00215D",
    line="rgba(26,31,43,.12)",
    quote_bg="#E9ECF4",
    code_bg="#11162A",
)

#: blog.css `html[data-theme="dark"] body.blog` 값 그대로.
#: 본문에 순백(#FFF)을 쓰지 않는 것도 그쪽 의도를 따른 것이다(잔상 방지).
DARK = Palette(
    name="dark",
    text="#D7DEEC",
    text_muted="#8A94A8",
    heading="#F3F6FC",
    accent="#6E9BE8",
    line="rgba(215,222,236,.12)",
    quote_bg="#121826",
    code_bg="#0A0F1A",
)

#: 글자색을 Blogger 테마에 맡긴다. 선·배경은 밝기 어느 쪽에서도 읽히는 중립 회색.
INHERIT = Palette(
    name="inherit",
    text=None,
    text_muted=None,
    heading=None,
    accent="currentColor",
    line="rgba(128,128,128,.35)",
    quote_bg="rgba(128,128,128,.12)",
    code_bg="#11162A",
)

PALETTES = {p.name: p for p in (LIGHT, DARK, INHERIT)}
DEFAULT_PALETTE = "light"


def get(name: str | None) -> Palette:
    return PALETTES.get((name or DEFAULT_PALETTE).lower(), LIGHT)


def _color(prop: str, value: str | None) -> str:
    """색이 None이면 선언 자체를 빼서 Blogger 테마 값이 살아 있게 한다."""
    return f"{prop}:{value};" if value else ""


def wrapper(p: Palette) -> str:
    """본문 컨테이너 — blog.css `.article-body`의 18px / 1.85."""
    return (
        f"font-family:{FONT_BODY};font-size:18px;line-height:1.85;"
        f"{_color('color', p.text)}word-break:break-word;"
    )


def tag_styles(p: Palette) -> dict:
    """태그별 인라인 스타일. 여기 없는 태그는 손대지 않는다."""
    heading_font = f"font-family:{FONT_BODY};"
    return {
        # h2의 왼쪽 막대는 블로그 본문의 가장 눈에 띄는 표식이라 그대로 옮긴다.
        "h1": f"{heading_font}font-size:30px;font-weight:700;{_color('color', p.heading)}"
              "letter-spacing:-.015em;line-height:1.3;margin:56px 0 20px;",
        "h2": f"{heading_font}font-size:26px;font-weight:600;{_color('color', p.heading)}"
              f"letter-spacing:-.015em;line-height:1.35;padding-left:14px;"
              f"border-left:3px solid {p.accent};margin:52px 0 18px;",
        "h3": f"{heading_font}font-size:20px;font-weight:600;{_color('color', p.heading)}"
              "line-height:1.45;margin:32px 0 14px;",
        "h4": f"font-size:18px;font-weight:600;{_color('color', p.heading)}margin:28px 0 12px;",
        "h5": f"font-size:16px;font-weight:600;{_color('color', p.heading)}margin:24px 0 10px;",
        "h6": f"font-size:15px;font-weight:600;{_color('color', p.text_muted)}margin:24px 0 10px;",

        "p": f"{_color('color', p.text)}margin:0 0 21px;",

        # 마커를 본문과 같은 왼쪽선에 세운다 — blog.css가 일부러 padding-left:0 +
        # list-style-position:inside 로 맞춰둔 부분이라 그대로 따른다.
        "ul": "padding-left:0;list-style-position:inside;margin:0 0 21px;",
        "ol": "padding-left:0;list-style-position:inside;margin:0 0 21px;",
        "li": "margin:7px 0;",

        "a": f"color:{p.accent};text-decoration:underline;text-underline-offset:3px;"
             "text-decoration-thickness:1px;",
        "strong": f"{_color('color', p.heading)}font-weight:600;",
        "em": "font-style:italic;",
        "hr": f"border:0;border-top:1px solid {p.line};margin:36px 0;",

        "blockquote": f"padding:18px 20px;background:{p.quote_bg};"
                      f"border-left:3px solid {p.accent};border-radius:0 3px 3px 0;"
                      f"font-size:16px;line-height:1.75;{_color('color', p.text)}"
                      "margin:0 0 21px;",

        "table": "width:100%;border-collapse:collapse;font-size:16px;margin:0 0 21px;",
        "th": f"text-align:left;padding:10px 12px;border-bottom:1.5px solid {p.line};"
              f"{_color('color', p.heading)}font-weight:600;",
        "td": f"padding:10px 12px;border-bottom:1px solid {p.line};vertical-align:top;",

        "img": "width:100%;height:auto;border-radius:3px;",

        # <pre> 밖의 인라인 코드에만 적용된다(코드블록 내부는 건드리지 않음).
        "code": f"font-family:{FONT_MONO};font-size:.86em;background:{p.quote_bg};"
                f"{_color('color', p.heading)}padding:2px 6px;border-radius:3px;",
    }


def pre_style(p: Palette) -> str:
    """코드블록 껍데기 — blog.css `.article-body pre`.

    코드블록은 팔레트와 무관하게 늘 어둡다. 배경만 팔레트를 따른다.
    """
    return (
        f"background:{p.code_bg};color:{CODE_FG};font-family:{FONT_MONO};font-size:14px;"
        f"border:1px solid {p.line};border-radius:3px;padding:16px 18px;"
        "line-height:1.75;overflow-x:auto;margin:0 0 21px;white-space:pre;"
    )


PRE_CODE_STYLE = (
    f"font-family:{FONT_MONO};background:none;color:inherit;padding:0;"
    "border-radius:0;font-size:inherit;white-space:inherit;"
)

#: mermaid 다이어그램 자리. Mermaid.js가 이 div를 찾아 SVG로 바꾼다.
MERMAID_STYLE = "margin:28px 0;text-align:center;"
