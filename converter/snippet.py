"""Blogger 테마에 한 번만 넣어두면 되는 스크립트.

변환기가 내보내는 HTML은 스타일이 전부 인라인이라 **코드블록·표·인용구는 그냥 나온다**.
스크립트가 필요한 건 두 가지뿐이다.

- 수식: arithmatex가 `\\(...\\)`·`\\[...\\]`로 감싼 것을 KaTeX가 그린다.
- 다이어그램: `<div class="mermaid">`를 Mermaid.js가 SVG로 바꾼다.

블로그(templates/blog/detail.html)가 쓰는 것과 같은 버전·같은 설정이다.
`throwOnError:false`는 수식 하나가 틀렸다고 글 전체가 안 보이는 일을 막는다.

Mermaid의 CDN 주소와 테마는 **상수로 빼 두었다.** 다이어그램 편집기 화면(`/mermaid`)이
같은 값을 읽어 같은 버전으로 그린다 — 갈라지면 편집기에서 본 그림과 Blogger에 붙여넣은
그림이 달라진다. 이 파일이 유일한 출처다.
"""

THEME_SNIPPET = """<!-- ── 마크다운 변환 글용 · KaTeX(수식) ─────────────── -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css" />
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
<script>
document.addEventListener("DOMContentLoaded", function () {
  if (!window.renderMathInElement) return;
  document.querySelectorAll(".arithmatex").forEach(function (el) {
    renderMathInElement(el, {
      delimiters: [
        { left: "\\\\[", right: "\\\\]", display: true },
        { left: "\\\\(", right: "\\\\)", display: false }
      ],
      throwOnError: false
    });
  });
});
</script>
"""

#: Mermaid.js CDN(ESM). 테마 스니펫과 편집기 화면이 같은 주소를 쓴다.
MERMAID_SRC = "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs"

#: 다이어그램 테마. Blogger 글 배경이 밝을 수도 어두울 수도 있어 중립을 쓴다
#: (블로그 본문은 dark를 쓴다 — docs/blogger-theme-snippet.md 참고).
MERMAID_THEME = "neutral"

THEME_SNIPPET += """
<!-- ── 마크다운 변환 글용 · Mermaid(다이어그램) ───────── -->
<script type="module">
  import mermaid from "%s";
  mermaid.initialize({ startOnLoad: true, theme: "%s" });
</script>
""" % (MERMAID_SRC, MERMAID_THEME)
