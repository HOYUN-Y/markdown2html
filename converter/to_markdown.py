"""HTML → 마크다운. `blogger.convert()`의 역방향.

세 가지 입력을 받는다. 난이도가 다르다.

1. **우리 변환기 출력** — 구조를 우리가 만들었으니 왕복이 목표다.
   `md → html → md`가 원문으로 돌아오는지가 그대로 명세다(tests/test_to_markdown.py).
2. **Blogger에 올린 글** — div 수프, 문단 대신 `<br>`, 태그마다 인라인 스타일.
   여기서는 **버릴 것을 정하는 규칙**이 절반이다(`_clean`).
3. **임의의 웹페이지** — 위 둘에 더해 본문이 아닌 것(네비게이션·푸터)이 섞인다.
   이 모듈은 본문 추출을 하지 않는다. 붙여넣을 조각을 사람이 골라 주는 전제다.

## 되돌릴 수 없는 것

마크다운에 문법이 없는 것은 **원본 HTML을 그대로 남기고 경고한다.** 셀을 병합한 표,
중첩 표, iframe 같은 것들이다. 마크다운은 원시 HTML을 허용하므로 이게 정보를 잃지
않는 유일한 길이다 — 억지로 평평하게 만들면 표가 조용히 뭉개진다.

## bs4를 `__init__`에서 import하지 않는 이유

블로그(django_blog_Enhanced)가 `converter/` 폴더를 통째로 복사해 쓰는데, 그쪽은
정방향만 쓴다. `__init__.py`가 bs4를 끌어오면 블로그에도 없는 의존성이 강제된다.
그래서 이 모듈은 직접 import해야 한다.

    from converter.to_markdown import to_markdown
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

#: 통째로 버린다. 본문이 아니거나 마크다운으로 옮길 수 없는 것들.
_DROP = {"script", "style", "noscript", "head", "meta", "link", "template"}

#: 알맹이만 남기고 태그는 벗긴다. Blogger가 글자마다 씌우는 것들이다.
_UNWRAP = {"span", "font", "small", "big", "center", "article", "section",
           "main", "header", "footer", "nav", "figure", "figcaption", "tbody",
           "thead", "tfoot", "colgroup", "col"}

_BLOCKS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li",
           "blockquote", "pre", "table", "hr", "dl", "dt", "dd"}

# ── 이스케이프 ────────────────────────────────────────────────────
#
# **필요한 만큼만 한다.** 전부 이스케이프하면 되돌린 글이 역슬래시 범벅이 되고,
# 더 나쁘게는 **없던 문법을 만들어 낸다.** 실제로 겪은 사고: 본문의
# `[이미지2 - 월별 단속]`을 `\[…\]`로 감쌌더니, 다시 변환할 때 arithmatex가
# 그걸 LaTeX display 수식 구분자(`\[ … \]`)로 읽어 문단이 수식이 됐다.
#
# 그래서 "그 자리에서 실제로 문법이 될 수 있을 때"만 이스케이프한다.

#: 언제나 위험하다 — 역슬래시 자신과 코드 구분자.
_ESC_ALWAYS = re.compile(r"([\\`])")
#: 강조는 **공백이 아닌 글자에 붙어야** 성립한다. `2 * 3`은 강조가 아니다.
_ESC_EMPHASIS = re.compile(r"(?<=\S)([*_])|([*_])(?=\S)")
#: 링크·참조가 될 수 있는 대괄호만. 그냥 `[메모]`는 건드리지 않는다.
_ESC_LINK = re.compile(r"\[([^\]\n]*)\](?=[(\[])")
#: 태그로 보이는 꺾쇠만. `a < b`는 그대로 둔다.
_ESC_TAG = re.compile(r"<(?=[a-zA-Z/!?])")
#: 줄 맨 앞에서만 의미가 생기는 것들 — 인용·목록·제목 기호.
_ESC_LINE_START = re.compile(r"^(\s*)([-+*>#]|\d+[.)])(\s)", re.MULTILINE)


@dataclass
class MarkdownResult:
    markdown: str
    warnings: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)


def to_markdown(html: str, *, base_url: str = "") -> MarkdownResult:
    """HTML 조각을 마크다운으로 되돌린다.

    :param base_url: 상대경로 링크·이미지를 절대 URL로 만들 기준.
        비워 두면 상대경로 그대로 둔다.
    """
    warnings: list = []
    notes: list = []

    soup = BeautifulSoup(html or "", "html.parser")
    _clean(soup)
    ctx = _Ctx(base_url=(base_url or "").strip(), warnings=warnings)

    body = soup.body or soup
    text = _join(_blocks(body, ctx))
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    text = text + "\n" if text else ""

    if ctx.raw_html_kept:
        warnings.append(
            f"마크다운으로 옮길 수 없는 요소 {ctx.raw_html_kept}개는 HTML 그대로 두었습니다"
            "(셀을 병합한 표·중첩 표·그림(SVG) 등). 마크다운은 원시 HTML을 허용하므로 그대로 "
            "두면 동작하지만, 다른 편집기에서는 손봐야 할 수 있습니다."
        )
    stats = {
        "characters": len(text),
        "lines": text.count("\n"),
        "code_blocks": ctx.code_blocks,
        "images": ctx.images,
        "links": ctx.links,
        "tables": ctx.tables,
        "raw_html_kept": ctx.raw_html_kept,
    }
    return MarkdownResult(markdown=text, warnings=warnings, notes=notes, stats=stats)


@dataclass
class _Ctx:
    base_url: str = ""
    warnings: list = field(default_factory=list)
    code_blocks: int = 0
    images: int = 0
    links: int = 0
    tables: int = 0
    raw_html_kept: int = 0


# ---------------------------------------------------------------- 청소

def _clean(soup: BeautifulSoup) -> None:
    """마크다운에 옮길 수 없는 껍데기를 걷어낸다.

    Blogger·워드프로세서가 붙인 것들은 **의미가 없고 부피만 크다.** 여기서 걷어내지
    않으면 뒤의 렌더가 빈 문단과 중첩된 강조를 잔뜩 만들어 낸다.
    """
    for node in soup.find_all(string=lambda s: isinstance(s, Comment)):
        node.extract()
    for tag in soup.find_all(list(_DROP)):
        # svg 안의 <style>은 그림의 일부다. 지우면 색과 선이 사라진다.
        if _in_svg(tag):
            continue
        tag.decompose()

    # b/i/strike는 의미 태그로 통일한다. 뒤 렌더가 한 곳만 보게 하려는 것.
    for old, new in (("b", "strong"), ("i", "em"), ("strike", "del"), ("s", "del")):
        for tag in soup.find_all(old):
            if _in_svg(tag):
                continue
            tag.name = new

    for tag in soup.find_all(list(_UNWRAP)):
        # 우리 마커는 클래스로 알아보므로 벗기면 안 된다.
        if _has_class(tag, "arithmatex", "mermaid") or _in_svg(tag):
            continue
        tag.unwrap()

    # div는 문단 대용으로도, 그냥 감싸개로도 쓰인다. 안에 블록이 있으면 감싸개일
    # 뿐이니 벗기고, 글만 있으면 문단으로 승격한다.
    for tag in soup.find_all("div"):
        if _has_class(tag, "arithmatex", "mermaid"):
            continue
        # 그림을 **직접** 감싼 div는 감싸개째 남긴다. 벗기면 다시 변환할 때 <svg>가
        # <p>에 감싸이고, 그 안의 글자에 마크다운 인라인 문법이 먹어 <text>*x*</text>가
        # <em>이 된다. 감싸개가 있어야 왕복이 닫힌다.
        #
        # 직계 자식만 보는 것이 중요하다 — 글 전체를 감싼 컨테이너 div도 그림을
        # '품고' 있어서, 깊이를 안 따지면 본문 전체가 통째로 보존돼 버린다.
        if _wraps_svg(tag):
            continue
        if tag.find(list(_BLOCKS)):
            tag.unwrap()
        else:
            tag.name = "p"

    # 남은 스타일 흔적. 우리가 읽는 것(class)만 남기고 전부 버린다.
    for tag in soup.find_all(True):
        # **svg 안은 건드리지 않는다.** viewBox·width·height·id·fill은 껍데기가 아니라
        # 그림 그 자체다. 지우면 0×0이 되거나 화살표·그라디언트 참조가 끊긴다.
        #
        # 그림을 직접 감싼 div도 그대로 둔다 — 그 style이 그림의 여백과 가운데 정렬을
        # 들고 있고, 어차피 통째로 원본으로 내보낼 것이라 여기서 지우면 왕복에서
        # 첫 번째와 두 번째 결과가 달라진다.
        if _in_svg(tag) or _wraps_svg(tag):
            continue
        for attr in ("style", "id", "width", "height", "align", "bgcolor",
                     "color", "face", "size", "border", "cellpadding", "cellspacing"):
            tag.attrs.pop(attr, None)
        for attr in list(tag.attrs):
            if attr.startswith("data-") or attr.startswith("on"):
                del tag.attrs[attr]


def _in_svg(tag: Tag) -> bool:
    """이 태그가 그림(svg) 안에 있거나 svg 자신인가.

    청소 규칙은 전부 **본문 HTML**을 겨냥한 것이라 그림에 적용하면 그림이 망가진다.
    """
    return tag.name == "svg" or tag.find_parent("svg") is not None


def _wraps_svg(tag: Tag) -> bool:
    """이 태그가 그림을 **직접** 감싸고 있는가(직계 자식에 svg가 있는가)."""
    return tag.find("svg", recursive=False) is not None


def _has_class(tag: Tag, *names: str) -> bool:
    classes = tag.get("class") or []
    return any(name in classes for name in names)


# ---------------------------------------------------------------- 블록

def _blocks(node, ctx: _Ctx) -> list:
    """자식들을 블록 단위 마크다운 문자열 목록으로 만든다."""
    out: list = []
    inline_buffer: list = []

    def flush():
        if inline_buffer:
            text = "".join(inline_buffer).strip()
            if text:
                # 강제 줄바꿈(공백 둘 + 개행) 뒤에 붙은 여백을 턴다. 마크다운에서
                # 의미는 없지만 되돌린 글이 들쭉날쭉해 보인다.
                text = re.sub(r"  \n[ \t]+", "  \n", text)
                # 문단이 완성된 뒤에야 '줄 맨 앞'이 어디인지 알 수 있다.
                out.append(_escape_line_starts(text))
            inline_buffer.clear()

    for child in list(node.children):
        if isinstance(child, NavigableString):
            inline_buffer.append(_text(str(child)))
            continue
        if not isinstance(child, Tag):
            continue
        if child.name in _BLOCKS or child.name in ("table", "pre"):
            flush()
            block = _block(child, ctx)
            if block:
                out.append(block)
        else:
            inline_buffer.append(_inline(child, ctx))
    flush()
    return out


def _block(tag: Tag, ctx: _Ctx) -> str:
    name = tag.name

    if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = int(name[1])
        return f"{'#' * level} {_inline(tag, ctx).strip()}"

    if name == "hr":
        return "---"

    if name == "pre":
        return _code_block(tag, ctx)

    if name == "blockquote":
        inner = _join(_blocks(tag, ctx))
        return _prefix(inner, "> ")

    if name in ("ul", "ol"):
        return _list(tag, ctx)

    if name == "table":
        return _table(tag, ctx)

    if name in ("dl", "dt", "dd"):
        # 마크다운 표준에 정의 목록이 없다. 굵은 항목 + 들여쓴 설명으로 근사한다.
        return _join(_blocks(tag, ctx))

    if tag.name == "svg" or _wraps_svg(tag):
        # 마크다운에 그림 문법이 없다. 평평하게 만들면 그림이 통째로 사라지므로
        # 원본을 그대로 두고 경고한다 — 셀 병합 표를 다룰 때와 같은 원칙이다.
        ctx.raw_html_kept += 1
        return _raw(tag)

    if _has_class(tag, "mermaid"):
        ctx.code_blocks += 1
        return _fence(tag.get_text(), "mermaid")

    if _has_class(tag, "arithmatex"):
        return _math(tag.get_text(), block=True)

    # p, div, li 등 — 알맹이가 블록을 품고 있으면 그대로 이어 붙인다.
    inner = _blocks(tag, ctx)
    return _join(inner)


#: 중첩 목록 들여쓰기. **4칸이어야 한다.**
#:
#: 우리가 되돌린 마크다운은 다시 이 저장소(그리고 블로그)의 Python-Markdown을 통과한다.
#: 그런데 Python-Markdown 3.4.1은 CommonMark가 아니라 원조 Markdown.pl 규칙을 따라
#: **4칸부터** 중첩으로 본다. 2칸(요즘 흔한 표기)으로 내보내면 되돌린 글을 다시 변환할 때
#: 중첩이 조용히 평평해진다 — 실제로 그렇게 깨지는 것을 확인하고 4칸으로 고정했다.
_LIST_INDENT = "    "

#: 목록 항목처럼 보이는 블록. 항목 안의 중첩 목록은 빈 줄 없이 바로 이어야 한다.
_LOOKS_LIKE_LIST = re.compile(r"^\s*(?:[-*+]\s|\d+\.\s)")


def _list(tag: Tag, ctx: _Ctx) -> str:
    ordered = tag.name == "ol"
    items = tag.find_all("li", recursive=False)
    # 항목 하나라도 글을 `<p>`로 감싸고 있으면 원본이 loose 목록이었다는 뜻이다.
    # 그때는 항목 **사이에도** 빈 줄을 넣어야 다시 변환했을 때 같은 HTML이 나온다.
    loose = any(item.find("p", recursive=False) is not None for item in items)

    rendered: list = []
    index = int(tag.get("start") or 1)
    for item in items:
        marker = f"{index}. " if ordered else "- "
        body = _item_body(item, ctx)
        if not body:
            continue
        first, *rest = body.split("\n")
        lines = [marker + first]
        # 이어지는 줄은 들여쓴다. 안 그러면 목록이 거기서 끊긴다.
        lines += [_LIST_INDENT + line if line.strip() else "" for line in rest]
        rendered.append("\n".join(lines))
        index += 1
    return ("\n\n" if loose else "\n").join(rendered)


def _item_body(item: Tag, ctx: _Ctx) -> str:
    """`<li>` 안을 한 덩어리로 만든다.

    중첩 목록 앞의 빈 줄이 **목록의 성격을 바꾼다.** 빈 줄이 있으면 loose 목록이 되어
    항목마다 `<p>`가 씌워지고(항목 간격이 벌어진다), 없으면 tight 목록이 된다.
    그래서 원본이 어느 쪽이었는지를 보고 따라간다 — `<li>`가 글을 `<p>`로 감싸고
    있으면 loose였다는 뜻이다. 이걸 안 보고 한쪽으로 고정하면 왕복에서 목록이
    조용히 조여지거나 벌어진다.
    """
    blocks = [b for b in _blocks(item, ctx) if b and b.strip()]
    if not blocks:
        return ""
    loose = item.find("p", recursive=False) is not None
    out = blocks[0].strip()
    for block in blocks[1:]:
        tight_enough = _LOOKS_LIKE_LIST.match(block) and not loose
        out += ("\n" if tight_enough else "\n\n") + block.strip()
    return out


def _code_block(tag: Tag, ctx: _Ctx) -> str:
    ctx.code_blocks += 1
    code = tag.find("code") or tag
    lang = _language_of(code) or _language_of(tag) or ""
    # 우리 정방향은 `<pre>` 안 개행을 `<br>`로 바꾼다(Blogger의 줄바꿈 자동 변환
    # 때문에). 그대로 get_text()를 부르면 줄이 전부 붙어버린다.
    for br in code.find_all("br"):
        br.replace_with("\n")
    return _fence(code.get_text(), lang)


def _language_of(tag: Tag):
    for token in tag.get("class") or []:
        for prefix in ("language-", "lang-", "highlight-"):
            if token.startswith(prefix):
                return token[len(prefix):]
    return None


def _fence(text: str, lang: str = "") -> str:
    body = text.strip("\n")
    # 본문에 백틱 울타리가 있으면 더 긴 울타리로 감싼다. 안 그러면 블록이 중간에 끝난다.
    longest = max((len(m) for m in re.findall(r"`+", body)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}{lang}\n{body}\n{fence}"


def _table(tag: Tag, ctx: _Ctx) -> str:
    """GFM 표로 옮긴다. 옮길 수 없으면 HTML을 그대로 남긴다."""
    ctx.tables += 1
    if tag.find("table") or tag.find(attrs={"colspan": True}) or tag.find(attrs={"rowspan": True}):
        # 셀 병합과 중첩 표는 마크다운에 문법이 없다. 억지로 평평하게 만들면
        # 표가 조용히 뭉개진다 — 원본을 남기는 편이 정보를 안 잃는다.
        ctx.raw_html_kept += 1
        return _raw(tag)

    rows = []
    for tr in tag.find_all("tr"):
        cells = tr.find_all(["th", "td"], recursive=False)
        if cells:
            rows.append([_inline(c, ctx).strip().replace("|", "\\|") for c in cells])
    if not rows:
        return ""

    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    head, *body = rows
    lines = ["| " + " | ".join(head) + " |",
             "|" + "|".join(["---"] * width) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in body]
    return "\n".join(lines)


def _raw(tag: Tag) -> str:
    """HTML을 한 줄로 눌러 그대로 남긴다."""
    return re.sub(r"\s*\n\s*", " ", str(tag)).strip()


# ---------------------------------------------------------------- 인라인

def _inline(node, ctx: _Ctx) -> str:
    if isinstance(node, NavigableString):
        return _text(str(node))
    if not isinstance(node, Tag):
        return ""

    name = node.name

    if name == "br":
        # 마크다운의 강제 줄바꿈은 공백 둘 + 개행이다.
        return "  \n"

    if name == "img":
        ctx.images += 1
        src = _url(node.get("src") or "", ctx)
        alt = (node.get("alt") or "").strip()
        title = (node.get("title") or "").strip()
        suffix = ' "%s"' % title if title else ""
        return "![%s](%s%s)" % (alt, src, suffix)

    if name == "a":
        href = _url(node.get("href") or "", ctx)
        label = _children(node, ctx).strip()
        if not href:
            return label
        ctx.links += 1
        return f"[{label}]({href})"

    if name == "code":
        return _inline_code(node.get_text())

    if _has_class(node, "arithmatex"):
        return _math(node.get_text(), block=False)

    if name in ("strong", "em", "del"):
        inner = _children(node, ctx).strip()
        if not inner:
            return ""
        mark = {"strong": "**", "em": "*", "del": "~~"}[name]
        return f"{mark}{inner}{mark}"

    if name in ("sub", "sup", "kbd", "abbr", "iframe", "video", "audio", "svg"):
        # 마크다운에 문법이 없다. 원본을 남긴다 — 지우면 내용이 사라진다.
        ctx.raw_html_kept += 1
        return _raw(node)

    return _children(node, ctx)


def _children(node, ctx: _Ctx) -> str:
    return "".join(_inline(child, ctx) for child in node.children)


def _inline_code(text: str) -> str:
    body = text.strip()
    if not body:
        return ""
    longest = max((len(m) for m in re.findall(r"`+", body)), default=0)
    tick = "`" * (longest + 1)
    # 백틱으로 시작하거나 끝나면 공백을 넣어야 구분된다(CommonMark 규칙).
    pad = " " if body.startswith("`") or body.endswith("`") else ""
    return f"{tick}{pad}{body}{pad}{tick}"


def _math(text: str, *, block: bool) -> str:
    r"""arithmatex가 씌운 `\(…\)`·`\[…\]`를 벗겨 `$…$`로 되돌린다.

    정방향에서 `$$…$$`를 문장 **안에** 쓰면 arithmatex가 span을 이중으로 감싸는
    버그가 있다(블로그와 같은 동작이라 고치지 않았다). 그 결과 텍스트에 구분자가
    두 번 들어 있을 수 있어, 남을 때까지 벗긴다.
    """
    body = text.strip()
    for _ in range(3):
        stripped = body
        for left, right in ((r"\[", r"\]"), (r"\(", r"\)")):
            if stripped.startswith(left) and stripped.endswith(right):
                stripped = stripped[len(left):-len(right)].strip()
        if stripped == body:
            break
        body = stripped
    return f"$$\n{body}\n$$" if block else f"${body}$"


# ---------------------------------------------------------------- 도우미

def _text(raw: str) -> str:
    """본문 텍스트 — 공백을 접고, **문법이 될 수 있는 것만** 이스케이프한다."""
    text = re.sub(r"\s+", " ", raw)
    if not text.strip():
        return " " if text else ""
    text = _ESC_ALWAYS.sub(r"\\\1", text)
    text = _ESC_EMPHASIS.sub(lambda m: "\\" + (m.group(1) or m.group(2)), text)
    text = _ESC_LINK.sub(r"\\[\1\\]", text)
    text = _ESC_TAG.sub(r"\\<", text)
    return text


def _escape_line_starts(block: str) -> str:
    """줄 맨 앞의 `#`·`>`·목록 기호만 이스케이프한다.

    본문 한가운데의 `-`나 `#`은 아무 문법도 아니다. 줄 앞에 올 때만 제목·인용·목록이
    되므로, 블록을 다 만든 뒤 그 자리에서만 처리한다.
    """
    return _ESC_LINE_START.sub(lambda m: f"{m.group(1)}\\{m.group(2)}{m.group(3)}", block)


def _url(value: str, ctx: _Ctx) -> str:
    value = (value or "").strip()
    if not value or not ctx.base_url:
        return value
    if urlparse(value).scheme or value.startswith(("#", "//", "data:", "mailto:")):
        return value
    return urljoin(ctx.base_url.rstrip("/") + "/", value.lstrip("/"))


def _prefix(text: str, marker: str) -> str:
    return "\n".join((marker + line).rstrip() if line.strip() else marker.rstrip()
                     for line in text.split("\n"))


def _join(blocks: list) -> str:
    return "\n\n".join(b for b in blocks if b and b.strip())
