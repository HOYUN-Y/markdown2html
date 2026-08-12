"""`<style>` 블록 출력용 CSS.

Blogger는 글 본문의 `<style>` 태그를 정상 처리한다. 인라인 스타일 대신 이걸 쓰면
본문이 짧아지고(실측: 43.6천 자 → 24.6천 자, 44% 감소 — 본문 텍스트 자체가 하한이라
그 이상은 안 줄어든다), 무엇보다 **인라인으로는 표현할 수 없던 규칙을 그대로 옮길 수
있다** — blog.css의 `> * + *`(형제 여백)와 `li + li`가 그것이다. 인라인 모드에서는
이걸 px로 어림잡아야 했다.

지켜야 할 것 둘:

1. **모든 규칙을 고유 클래스 아래로 스코프한다.** 글 목록·홈 화면에서는 여러 글이 한
   페이지에 뜨고 각 글의 `<style>`이 전부 로드된다. 스코프가 없으면 테마와 다른 글까지
   건드린다. 팔레트 이름까지 클래스에 넣어(`md2b-dark`) 서로 다른 팔레트의 글이 같은
   페이지에 있어도 충돌하지 않게 한다.

2. **CSS도 개행을 남기지 않는다.** Blogger의 '엔터 = 줄바꿈' 설정은 `<style>` 안이라고
   봐주지 않는다. `<br>`이 끼면 그 지점부터 CSS가 깨진다.

특이도: 테마 CSS(`.post-body p { … }` 같은 것)와 싸워야 해서 루트를 두 클래스로
겹쳐 쓴다(`.md2b.md2b-dark`). `!important`를 뿌리는 것보다 낫다 — 필요하면 사용자가
직접 붙일 여지를 남긴다.
"""

from __future__ import annotations

from . import highlight as hl
from . import theme
from .theme import FONT_BODY, FONT_MONO, Palette

#: 본문 컨테이너에 붙는 클래스. 팔레트별로 갈라 같은 페이지에서 섞여도 안전하다.
BASE_CLASS = "md2b"


def root_class(p: Palette) -> str:
    return f"{BASE_CLASS} {BASE_CLASS}-{p.name}"


def _scope(p: Palette) -> str:
    # 클래스를 겹쳐 특이도를 (0,2,0)으로 올린다 — 테마 규칙에 지지 않게.
    return f".{BASE_CLASS}.{BASE_CLASS}-{p.name}"


def build(p: Palette) -> str:
    """팔레트 하나에 대한 CSS 전문을 한 줄로 돌려준다."""
    s = _scope(p)
    text = f"color:{p.text};" if p.text else ""
    heading = f"color:{p.heading};" if p.heading else ""
    muted = f"color:{p.text_muted};" if p.text_muted else ""

    rules = [
        # 본문 — blog.css `.article-body` (18px / 1.85)
        (s, f"font-family:{FONT_BODY};font-size:18px;line-height:1.85;{text}"
            "word-break:break-word"),

        # 형제 여백. 인라인으로는 못 옮기던 규칙이다.
        # 테마가 걸어둔 기본 margin을 먼저 지워야 계산이 맞는다.
        (f"{s} > *", "margin:0"),
        (f"{s} > * + *", "margin-top:1.2em"),

        # 글자색·글꼴을 컨테이너 **상속에 맡기면 안 된다.** 상속은 요소를 직접 겨냥한
        # 규칙에 무조건 진다 — 테마에 `p { color: … }` 한 줄만 있어도 본문이 통째로
        # 그 색이 된다(실제로 적대적 테마를 흉내 내 확인했다). 특이도 문제가 아니라
        # 규칙이 없어서 지는 것이므로, 글자를 담는 요소마다 명시한다.
        # `inherit` 팔레트에서는 색을 비워 둔다 — 테마 색을 따르는 게 그 모드의 목적이다.
        (f"{s} p,{s} li,{s} td,{s} th,{s} blockquote,{s} dd,{s} dt",
         f"font-family:inherit;{text}"),

        (f"{s} h1", f"font-size:1.9rem;font-weight:700;letter-spacing:-.015em;"
                    f"line-height:1.3;margin-top:2.2em;{heading}"),
        # h2의 왼쪽 막대는 블로그 본문의 가장 눈에 띄는 표식이다.
        (f"{s} h2", f"margin-top:2em;font-size:1.62rem;font-weight:600;"
                    f"letter-spacing:-.015em;line-height:1.35;padding-left:14px;"
                    f"border-left:3px solid {p.accent};{heading}"),
        (f"{s} h3", f"margin-top:1.6em;font-size:1.25rem;font-weight:600;"
                    f"line-height:1.45;{heading}"),
        (f"{s} h4", f"margin-top:1.5em;font-size:1.08rem;font-weight:600;{heading}"),
        (f"{s} h5", f"margin-top:1.4em;font-size:1rem;font-weight:600;{heading}"),
        (f"{s} h6", f"margin-top:1.4em;font-size:.95rem;font-weight:600;{muted}"),

        (f"{s} strong", f"font-weight:600;{heading}"),
        (f"{s} em", "font-style:italic"),
        (f"{s} a", f"color:{p.accent};text-decoration:underline;"
                   "text-underline-offset:3px;text-decoration-thickness:1px"),
        (f"{s} hr", f"border:0;border-top:1px solid {p.line};margin-top:2em"),

        # 리스트 — 마커를 본문과 같은 왼쪽선에 세운다(blog.css가 일부러 맞춰둔 부분)
        (f"{s} ul,{s} ol", "padding-left:0;list-style-position:inside"),
        (f"{s} li > ul,{s} li > ol", "padding-left:1.2em;margin-top:.4em"),
        (f"{s} li + li", "margin-top:.4em"),

        (f"{s} blockquote", f"padding:18px 20px;background:{p.quote_bg};"
                            f"border-left:3px solid {p.accent};"
                            f"border-radius:0 3px 3px 0;font-size:1rem;"
                            f"line-height:1.75;{text}"),

        (f"{s} table", "width:100%;border-collapse:collapse;font-size:.94rem"),
        (f"{s} th", f"text-align:left;padding:10px 12px;"
                    f"border-bottom:1.5px solid {p.line};font-weight:600;{heading}"),
        (f"{s} td", f"padding:10px 12px;border-bottom:1px solid {p.line};"
                    "vertical-align:top"),

        (f"{s} img", "width:100%;height:auto;border-radius:3px"),

        # 코드블록은 팔레트와 무관하게 늘 어둡다(blog.css:435와 같은 방침)
        (f"{s} pre", f"background:{p.code_bg};color:{theme.CODE_FG};"
                     f"font-family:{FONT_MONO};font-size:.81rem;line-height:1.75;"
                     f"border:1px solid {p.line};border-radius:3px;"
                     "padding:16px 18px;overflow-x:auto;white-space:pre"),
        (f"{s} pre code", "background:none;color:inherit;padding:0;border-radius:0;"
                          "font-size:inherit;font-family:inherit;white-space:inherit"),
        (f"{s} code", f"font-family:{FONT_MONO};font-size:.86em;"
                      f"background:{p.quote_bg};padding:2px 6px;border-radius:3px;{heading}"),

        (f"{s} .mermaid", "margin-top:1.8em;text-align:center"),
    ]

    css = "".join(f"{selector}{{{declarations}}}" for selector, declarations in rules)
    # 문법 강조 색 — Pygments가 만든 클래스 규칙을 코드블록 안으로 한정한다.
    css += hl.style_defs(f"{s} pre")
    return css


def block(p: Palette) -> str:
    """붙여넣을 `<style>` 태그 한 줄."""
    return f"<style>{build(p)}</style>"
