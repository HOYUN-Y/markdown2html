"""마크다운 → HTML. 블로그(django_blog_Enhanced)와 같은 확장 조합을 쓴다.

기준: `posts/views.py:129`

    markdown.Markdown(
        extensions=["extra", "codehilite", "toc", "fenced_code", "pymdownx.arithmatex"],
        extension_configs={"pymdownx.arithmatex": {"generic": True}},
    )

여기서 **codehilite만 뺐다.** 이유:

- codehilite는 Pygments **CSS 클래스**를 뱉는데, Blogger에는 그 CSS를 넣을 데가 없다.
  색을 인라인으로 박아야 해서 `converter.highlight`가 나중 단계에서 직접 칠한다.
- 블로그도 실제 화면 색은 codehilite가 아니라 브라우저의 highlight.js가 칠한다
  (templates/blog/detail.html:234). 즉 뒤 단계에서 칠하는 쪽이 오히려 블로그 동작에 가깝다.

나머지(extra의 표·각주·attr_list, toc의 heading id, arithmatex의 수식 보호)는 블로그와 동일하다.
"""

from __future__ import annotations

import re

import markdown

from . import theme

EXTENSIONS = ["extra", "toc", "fenced_code", "pymdownx.arithmatex"]
EXTENSION_CONFIGS = {"pymdownx.arithmatex": {"generic": True}}

# ```mermaid 블록. 마크다운 변환 **전에** 빼돌린다 —
# 그냥 두면 Pygments가 다이어그램 소스를 코드로 색칠해버려서 Mermaid.js가 못 읽는다.
_MERMAID_FENCE = re.compile(
    r"^[ \t]*(?:```|~~~)[ \t]*mermaid[ \t]*\n(.*?)\n?^[ \t]*(?:```|~~~)[ \t]*$",
    re.MULTILINE | re.DOTALL,
)

# 마크다운 문법에 걸리지 않도록 영문·숫자만 쓴 자리표시자.
# (밑줄이나 대괄호를 쓰면 기울임·링크로 해석될 수 있다)
_MERMAID_TOKEN = "xMdToBloggerMermaid{}x"


def render(text: str):
    """(html, 정보 dict)를 돌려준다.

    정보 dict: ``mermaid_count``, ``has_math``, ``toc_html``
    """
    text = text or ""
    diagrams: list[str] = []

    def _stash(match: "re.Match") -> str:
        diagrams.append(match.group(1))
        # 앞뒤 빈 줄 — 자리표시자가 독립된 문단이 되게 한다.
        return "\n\n" + _MERMAID_TOKEN.format(len(diagrams) - 1) + "\n\n"

    text = _MERMAID_FENCE.sub(_stash, text)

    md = markdown.Markdown(
        extensions=EXTENSIONS,
        extension_configs=EXTENSION_CONFIGS,
    )
    html = md.convert(text)

    for index, source in enumerate(diagrams):
        token = _MERMAID_TOKEN.format(index)
        div = (
            f'<div class="mermaid" style="{theme.MERMAID_STYLE}">'
            f"{_escape_diagram(source)}</div>"
        )
        # 자리표시자는 <p>로 감싸여 나온다. 문단째 걷어내야 <p> 껍데기가 안 남는다.
        html = html.replace(f"<p>{token}</p>", div).replace(token, div)

    info = {
        "mermaid_count": len(diagrams),
        # arithmatex(generic)가 붙이는 클래스가 수식 존재의 유일한 신호다.
        # 블로그도 같은 방식으로 KaTeX 로드 여부를 정한다(posts/views.py:168).
        "has_math": 'class="arithmatex"' in html,
        "toc_html": getattr(md, "toc", "") or "",
    }
    return html, info


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _escape_diagram(source: str) -> str:
    """다이어그램 소스를 이스케이프하되, 줄바꿈은 `&#10;`으로 남긴다.

    Mermaid는 요소의 textContent를 줄 단위로 파싱한다. 그런데 Blogger 대응 때문에
    출력에서 **개행 문자를 전부 없애야** 하고, 그러면 `graph TD` 이하가 한 줄로
    뭉쳐 'Syntax error in text'가 난다. `<br>`도 답이 아니다 — textContent에는
    아무것도 기여하지 않아 줄이 그대로 붙어버린다.

    실체 참조 `&#10;`은 HTML 소스에 개행 문자로 존재하지 않으므로 Blogger의
    줄바꿈 자동 변환에 걸리지 않으면서, 브라우저가 DOM 텍스트로 만들 때는 진짜
    개행이 된다. 양쪽을 동시에 만족하는 유일한 형태다.
    """
    return _escape(source).replace("\r\n", "\n").replace("\r", "\n").replace("\n", "&#10;")
