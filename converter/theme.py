"""블로그 본문 조판을 인라인 스타일 표로 옮긴 것.

출처: django_blog_Enhanced/static/css/blog.css 의 `body.blog` 토큰과
`body.blog .article-body` 규칙. **main.css(.prose)가 아니다** — 그쪽은 포트폴리오
사이트용 오렌지 테마이고, blog.devprofessional.xyz 본문은 blog.css의
'Slate & Navy'(강조색 = 남색 #00215D)를 쓴다.

Blogger 글 본문에는 우리 CSS를 넣을 데가 없어서 같은 값을 `style=` 속성에 직접 박는다.
CSS와 1:1로 못 옮기는 규칙이 둘 있고, 아래처럼 근사했다.

- `.article-body > * + * { margin-top: 1.2em }` — 인접 형제 선택자는 인라인 불가.
  → 블록 요소마다 `margin-bottom`으로 대체(첫 요소 위쪽 여백만 조금 다르다).
- `li + li { margin-top: .4em }` — 마찬가지. → 모든 `li`에 위아래 여백으로 대체.
"""

# ---------- blog.css `body.blog` 토큰 (라이트) ----------
BG_ALT = "#E9ECF4"
TEXT = "#1A1F2B"
TEXT_MUTED = "#5B6478"
HEADING = "#0D1220"
LINE = "rgba(26,31,43,.12)"
ACCENT = "#00215D"
RADIUS = "3px"

#: 코드블록 배경 — blog.css `--code-bg`. 라이트/다크 양쪽에서 항상 어둡다.
CODE_BG = "#11162A"
#: 블로그가 쓰는 highlight.js github-dark-dimmed의 본문 색
CODE_FG = "#adbac7"

# main.css :root의 폰트 토큰. Blogger 테마에는 없을 수 있어 폴백을 길게 둔다.
FONT_BODY = (
    "'Pretendard','Space Grotesk',-apple-system,BlinkMacSystemFont,"
    "'Segoe UI','Apple SD Gothic Neo','Malgun Gothic',sans-serif"
)
FONT_MONO = (
    "'Space Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,"
    "'D2Coding',monospace"
)

#: 본문 컨테이너 — blog.css `.article-body`의 18px / 1.85
WRAPPER = (
    f"font-family:{FONT_BODY};font-size:18px;line-height:1.85;"
    f"color:{TEXT};word-break:break-word;"
)

#: 태그별 인라인 스타일. 여기 없는 태그는 손대지 않는다.
TAG_STYLES = {
    # h2의 왼쪽 남색 막대는 블로그 본문의 가장 눈에 띄는 표식이라 그대로 옮긴다.
    "h1": f"font-family:{FONT_BODY};font-size:30px;font-weight:700;color:{HEADING};"
          "letter-spacing:-.015em;line-height:1.3;margin:56px 0 20px;",
    "h2": f"font-family:{FONT_BODY};font-size:26px;font-weight:600;color:{HEADING};"
          f"letter-spacing:-.015em;line-height:1.35;padding-left:14px;"
          f"border-left:3px solid {ACCENT};margin:52px 0 18px;",
    "h3": f"font-family:{FONT_BODY};font-size:20px;font-weight:600;color:{HEADING};"
          "line-height:1.45;margin:32px 0 14px;",
    "h4": f"font-size:18px;font-weight:600;color:{HEADING};margin:28px 0 12px;",
    "h5": f"font-size:16px;font-weight:600;color:{HEADING};margin:24px 0 10px;",
    "h6": f"font-size:15px;font-weight:600;color:{TEXT_MUTED};margin:24px 0 10px;",

    "p": f"color:{TEXT};margin:0 0 21px;",

    # 마커를 본문과 같은 왼쪽선에 세운다 — blog.css가 일부러 padding-left:0 +
    # list-style-position:inside 로 맞춰둔 부분이라 그대로 따른다.
    "ul": "padding-left:0;list-style-position:inside;margin:0 0 21px;",
    "ol": "padding-left:0;list-style-position:inside;margin:0 0 21px;",
    "li": "margin:7px 0;",

    "a": f"color:{ACCENT};text-decoration:underline;text-underline-offset:3px;"
         "text-decoration-thickness:1px;",
    "strong": f"color:{HEADING};font-weight:600;",
    "em": "font-style:italic;",
    "hr": f"border:0;border-top:1px solid {LINE};margin:36px 0;",

    "blockquote": f"padding:18px 20px;background:{BG_ALT};"
                  f"border-left:3px solid {ACCENT};border-radius:0 {RADIUS} {RADIUS} 0;"
                  f"font-size:16px;line-height:1.75;color:{TEXT};margin:0 0 21px;",

    "table": "width:100%;border-collapse:collapse;font-size:16px;margin:0 0 21px;",
    "th": f"text-align:left;padding:10px 12px;border-bottom:1.5px solid {HEADING};"
          f"color:{HEADING};font-weight:600;",
    "td": f"padding:10px 12px;border-bottom:1px solid {LINE};vertical-align:top;",

    "img": f"width:100%;height:auto;border-radius:{RADIUS};",

    # <pre> 밖의 인라인 코드에만 적용된다(코드블록 내부는 건드리지 않음).
    # blog.css에는 인라인 code 규칙이 없어 본문 톤에 맞춰 새로 정했다.
    "code": f"font-family:{FONT_MONO};font-size:.86em;background:{BG_ALT};"
            f"color:{HEADING};padding:2px 6px;border-radius:{RADIUS};",
}

#: 코드블록 껍데기 — blog.css `.article-body pre`.
#: 하이라이팅 색은 Pygments가 span마다 인라인으로 박는다.
PRE_STYLE = (
    f"background:{CODE_BG};color:{CODE_FG};font-family:{FONT_MONO};font-size:14px;"
    f"border:1px solid {LINE};border-radius:{RADIUS};padding:16px 18px;"
    "line-height:1.75;overflow-x:auto;margin:0 0 21px;white-space:pre;"
)
PRE_CODE_STYLE = (
    f"font-family:{FONT_MONO};background:none;color:inherit;padding:0;"
    "border-radius:0;font-size:inherit;white-space:inherit;"
)

#: mermaid 다이어그램 자리. Mermaid.js가 이 div를 찾아 SVG로 바꾼다.
MERMAID_STYLE = "margin:28px 0;text-align:center;"
