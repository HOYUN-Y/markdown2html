"""Blogger 글쓰기 화면의 'HTML 보기'에 붙여넣어도 안 깨지는 HTML로 후처리한다.

Blogger가 HTML을 망가뜨리는 지점이 넷 있고, 각각을 여기서 막는다.

1. **CSS 클래스가 무용지물** — 글 본문에는 스타일시트를 넣을 데가 없다.
   → 모든 스타일을 `style=` 속성으로 인라인화(`_Inliner`).
2. **개행이 `<br>`로 자동 변환** — Blogger 설정('엔터 = 줄바꿈')이 켜져 있으면
   붙여넣은 HTML의 줄바꿈이 전부 `<br>`이 돼 목록·코드블록 간격이 무너진다.
   → 출력에서 개행 문자를 **한 글자도 남기지 않는다**. 코드블록 줄바꿈은 `<br>`로
   미리 바꿔두므로 설정이 켜져 있든 꺼져 있든 결과가 같다.
3. **`<pre>` 안의 `<`·`&`** — 태그로 해석돼 글이 깨진다.
   → 마크다운 단계에서 이스케이프된 상태를 유지한 채 Pygments를 태운다.
4. **상대경로 이미지** — Blogger 도메인 기준이라 블로그 이미지가 안 보인다.
   → base URL을 주면 절대 URL로 치환한다.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from . import highlight as hl
from . import pipeline, stylesheet, theme

# fenced_code가 내놓는 코드블록. 언어가 없으면 class 속성 자체가 없다.
_CODE_BLOCK = re.compile(
    r'<pre><code(?:\s+class="([^"]*)")?\s*>(.*?)</code></pre>',
    re.DOTALL,
)

# 개행을 포함한 공백 덩어리 — <pre> 밖에서는 공백 하나로 접는다.
_NEWLINE_RUN = re.compile(r"[ \t]*\n[ \t\n]*")

_SKIP_ABS = ("#", "data:", "mailto:", "tel:", "javascript:")


@dataclass
class ConversionResult:
    """변환 결과와, 사람이 읽어야 할 안내를 함께 담는다."""

    html: str
    warnings: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)


def convert(
    markdown_text: str,
    *,
    image_base_url: str = "",
    safe_linebreaks: bool = True,
    wrap: bool = True,
    palette: str = theme.DEFAULT_PALETTE,
    output: str = "inline",
) -> ConversionResult:
    """마크다운 원문을 Blogger용 HTML 한 덩어리로 바꾼다.

    :param image_base_url: 상대경로 이미지/링크를 붙일 기준 URL
        (예: ``https://blog.devprofessional.xyz``)
    :param safe_linebreaks: 출력에서 개행 문자를 모두 없앤다.
        Blogger의 '엔터 = 줄바꿈' 설정과 무관하게 같은 결과를 보장한다.
    :param wrap: 글꼴·행간을 지정한 컨테이너 ``<div>``로 감싼다.
    :param palette: ``light`` / ``dark`` / ``inherit``.
        Blogger 테마의 배경 밝기에 맞춰 고른다 — 검은 테마에 ``light``를 쓰면
        본문이 배경에 묻힌다. ``inherit``은 글자색을 지정하지 않아 어떤 테마에도 맞다.
    :param output: ``inline`` — 모든 스타일을 `style=` 속성에 박는다(기본).
        ``css`` — 맨 앞에 `<style>` 블록을 두고 본문은 클래스만 갖는다.
        본문이 훨씬 짧아지고 blog.css의 형제 선택자 규칙까지 그대로 옮겨진다.
        대신 RSS 피드에서는 `<style>`이 제거돼 서식 없이 보인다.
    """
    warnings: list = []
    notes: list = []
    colors = theme.get(palette)
    use_css = output == "css"

    html, info = pipeline.render(markdown_text)
    code_blocks = _count_code_blocks(html)
    html = _restyle_code_blocks(
        html,
        colors=colors,
        safe_linebreaks=safe_linebreaks,
        warnings=warnings,
        use_css=use_css,
    )

    inliner = _Inliner(
        # CSS 모드에서는 스타일을 속성에 박지 않는다 — 스타일시트가 다 한다.
        tag_styles={} if use_css else theme.tag_styles(colors),
        image_base_url=(image_base_url or "").strip(),
        collapse_newlines=True,
    )
    inliner.feed(html)
    inliner.close()
    html = "".join(inliner.parts).strip()
    warnings.extend(inliner.warnings)

    if use_css:
        # 스타일시트가 컨테이너 클래스를 기준으로 쓰여 있어 감싸기는 선택이 아니다.
        if not wrap:
            notes.append("CSS 블록 모드는 컨테이너가 있어야 동작해 '컨테이너로 감싸기'를 켠 채로 처리했습니다.")
        html = (
            f"{stylesheet.block(colors)}"
            f'<div class="{stylesheet.root_class(colors)}">{html}</div>'
        )
    elif wrap:
        html = f'<div style="{theme.wrapper(colors)}">{html}</div>'

    if safe_linebreaks:
        # 마지막 보루 — 주석 등 파서가 그대로 흘려보낸 자리에 남은 개행까지 없앤다.
        html = html.replace("\r", "").replace("\n", " ")

    if info["has_math"]:
        notes.append(
            "수식이 있습니다. Blogger 테마에 KaTeX 스니펫을 한 번 넣어야 렌더됩니다 "
            "(docs/blogger-theme-snippet.md)."
        )
    if info["mermaid_count"]:
        notes.append(
            f"mermaid 다이어그램 {info['mermaid_count']}개가 있습니다. "
            "Blogger 테마에 Mermaid 스니펫이 필요합니다 (docs/blogger-theme-snippet.md)."
        )

    stats = {
        "characters": len(html),
        "code_blocks": code_blocks,
        "images": inliner.image_count,
        "mermaid": info["mermaid_count"],
        "has_math": info["has_math"],
        "newlines": html.count("\n"),
    }
    return ConversionResult(html=html, warnings=warnings, notes=notes, stats=stats)


# ---------------------------------------------------------------- 코드블록

def _count_code_blocks(html: str) -> int:
    return len(_CODE_BLOCK.findall(html))


def _restyle_code_blocks(
    html: str, *, colors: "theme.Palette", safe_linebreaks: bool, warnings: list,
    use_css: bool = False,
) -> str:
    # CSS 모드에서는 껍데기도 색도 스타일시트가 맡는다 — 여기서는 마크업만 만든다.
    open_pre = "<pre><code>" if use_css else (
        f'<pre style="{theme.pre_style(colors)}">'
        f'<code style="{theme.PRE_CODE_STYLE}">'
    )

    def replace(match: "re.Match") -> str:
        lang = _language_of(match.group(1))
        code = _unescape(match.group(2)).strip("\n")
        highlighted, warning = hl.highlight(code, lang, inline_colors=not use_css)
        if warning:
            warnings.append(warning)
        if safe_linebreaks:
            highlighted = highlighted.replace("\n", "<br>")
        return f"{open_pre}{highlighted}</code></pre>"

    return _CODE_BLOCK.sub(replace, html)


def _language_of(class_attr: str | None):
    """``class="language-python"`` 에서 ``python`` 만 뽑는다."""
    if not class_attr:
        return None
    for token in class_attr.split():
        if token.startswith("language-"):
            return token[len("language-"):] or None
        if token and token != "highlight":
            return token
    return None


def _unescape(text: str) -> str:
    """마크다운이 코드블록에 건 이스케이프를 되돌린다(Pygments에 원문을 넘기려고).

    `&lt;`·`&gt;`·`&amp;`만 되돌리면 안 된다 — Python-Markdown은 `"`도 `&quot;`로
    바꾼다. 그것을 빼먹으면 코드에 `&quot;`가 글자 그대로 찍힌다(실제로 그랬다).
    `html.unescape`는 한 번만 훑으므로, 원문의 `&lt;`(→ `&amp;lt;`)는 `&lt;`로
    정확히 복원되고 더 풀리지 않는다.
    """
    return html.unescape(text)


# ---------------------------------------------------------------- 인라인화

class _Inliner(HTMLParser):
    """태그별 스타일을 `style=` 속성으로 박고, `<pre>` 밖의 개행을 접는다.

    `convert_charrefs=False` — 기본값(True)이면 `&lt;` 같은 실체 참조가 문자로
    풀려버려서, 코드블록 안의 `<`가 다시 태그로 해석된다. 그대로 흘려보내야 한다.
    """

    def __init__(self, *, tag_styles: dict, image_base_url: str = "",
                 collapse_newlines: bool = True):
        super().__init__(convert_charrefs=False)
        self.parts: list = []
        self.warnings: list = []
        self.tag_styles = tag_styles
        self.pre_depth = 0
        self.image_count = 0
        self.image_base_url = image_base_url
        self.collapse_newlines = collapse_newlines
        self._warned_relative = False

    # -- 태그 --------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        self.parts.append(self._render_tag(tag, attrs, self_closing=False))
        if tag == "pre":
            self.pre_depth += 1

    def handle_startendtag(self, tag, attrs):
        self.parts.append(self._render_tag(tag, attrs, self_closing=True))

    def handle_endtag(self, tag):
        if tag == "pre" and self.pre_depth:
            self.pre_depth -= 1
        self.parts.append(f"</{tag}>")

    def _render_tag(self, tag, attrs, *, self_closing: bool) -> str:
        if tag == "img":
            self.image_count += 1

        pairs = [[name, value] for name, value in attrs]
        self._absolutize(tag, pairs)

        # <pre> 안은 이미 완성된 상태라 손대지 않는다.
        style = self.tag_styles.get(tag) if self.pre_depth == 0 else None

        rendered = []
        style_applied = False
        for name, value in pairs:
            if name == "style" and style:
                base = (value or "").strip().rstrip(";")
                value = f"{base};{style}" if base else style
                style_applied = True
            if value is None:
                rendered.append(name)
            else:
                rendered.append(f'{name}="{_attr_escape(value)}"')
        if style and not style_applied:
            rendered.append(f'style="{_attr_escape(style)}"')

        body = " ".join([tag] + rendered)
        return f"<{body} />" if self_closing else f"<{body}>"

    def _absolutize(self, tag, pairs) -> None:
        key = {"img": "src", "a": "href"}.get(tag)
        if not key:
            return
        for pair in pairs:
            if pair[0] != key or not pair[1]:
                continue
            value = pair[1]
            if value.startswith(_SKIP_ABS) or value.startswith("//"):
                continue
            if urlparse(value).scheme:
                continue
            if self.image_base_url:
                pair[1] = urljoin(self.image_base_url.rstrip("/") + "/", value.lstrip("/"))
            elif not self._warned_relative:
                self._warned_relative = True
                self.warnings.append(
                    "상대경로 이미지/링크가 있습니다. Blogger에서는 깨집니다 — "
                    "'이미지 기준 URL'을 채워 다시 변환하세요."
                )

    # -- 텍스트 ------------------------------------------------------
    def handle_data(self, data):
        if self.pre_depth or not self.collapse_newlines:
            self.parts.append(data)
        else:
            self.parts.append(_NEWLINE_RUN.sub(" ", data))

    def handle_entityref(self, name):
        self.parts.append(f"&{name};")

    def handle_charref(self, name):
        self.parts.append(f"&#{name};")

    def handle_comment(self, data):
        self.parts.append(f"<!--{data}-->")

    def handle_decl(self, decl):
        self.parts.append(f"<!{decl}>")


def _attr_escape(value: str) -> str:
    # 속성은 큰따옴표로 감싸므로 &와 "만 막으면 된다. 작은따옴표는 그대로 둔다 —
    # font-family:'Pretendard' 처럼 CSS에 필요한 문자다.
    return value.replace("&", "&amp;").replace('"', "&quot;")
