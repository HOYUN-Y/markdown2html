"""이 사이트가 담고 있는 도구 목록.

**도구를 늘릴 때 여기만 고친다.** 화면 상단 탭은 이 목록에서 그려지므로,
탭을 따로 손댈 일이 없다. 새 도구는 이렇게 붙인다.

1. 아래 목록에 항목을 추가하고 ``ready=True``, ``url``을 채운다
2. `app.py`에 라우트를 만들고 `render_template(..., **nav("<slug>"))`을 넘긴다
3. 템플릿에서 `{% include "_toolbar.html" %}`

아직 없는 도구도 ``ready=False``로 적어 둔다. 화면에 '준비 중'으로 나와서
무엇을 만들 셈인지가 코드와 화면 양쪽에 남는다 — 계획을 문서 밖에 두지 않기 위한 것이다.
"""

from __future__ import annotations

#: 순서가 곧 탭 순서다.
TOOLS = [
    {
        "slug": "convert",
        "name": "마크다운 ⇄ HTML",
        "summary": "블로그 글을 Blogger에 붙여넣을 HTML로. 되돌리기도 된다.",
        "url": "/",
        "ready": True,
    },
    {
        "slug": "mermaid",
        "name": "Mermaid 다이어그램",
        "summary": "다이어그램을 그려 보고 마크다운 코드블록으로 가져간다.",
        "url": "/mermaid",
        "ready": True,
    },
    {
        "slug": "drawio",
        "name": "draw.io 임베드",
        "summary": "draw.io 그림을 글에 넣을 수 있는 형태로 만든다.",
        "url": "",
        "ready": False,
    },
]


def nav(current: str) -> dict:
    """템플릿에 넘길 탭 정보. `render_template(..., **nav("convert"))`."""
    return {"tools": TOOLS, "current_tool": current}
