# Blogger 테마 스니펫

수식(KaTeX)과 mermaid 다이어그램을 쓸 때만 필요하다. **블로그당 한 번**만 넣으면
이후 모든 글에 적용된다.

> 코드블록·표·인용구·이미지는 스타일이 전부 인라인이라 **스니펫 없이도 그대로 나온다.**
> 스크립트가 필요한 건 수식과 다이어그램뿐이다.

## 넣는 방법

1. Blogger 관리 → **테마** → 오른쪽 아래 `▾` → **HTML 편집**
2. 맨 아래 `</body>` **바로 위**에 아래 내용을 붙여넣는다
3. **저장**

## 스니펫

```html
<!-- ── 마크다운 변환 글용 · KaTeX(수식) ─────────────── -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css" />
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
<script>
document.addEventListener("DOMContentLoaded", function () {
  if (!window.renderMathInElement) return;
  document.querySelectorAll(".arithmatex").forEach(function (el) {
    renderMathInElement(el, {
      delimiters: [
        { left: "\\[", right: "\\]", display: true },
        { left: "\\(", right: "\\)", display: false }
      ],
      throwOnError: false
    });
  });
});
</script>

<!-- ── 마크다운 변환 글용 · Mermaid(다이어그램) ───────── -->
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
  mermaid.initialize({ startOnLoad: true, theme: "neutral" });
</script>
```

## 무엇을 하는가

| 스크립트 | 대상 | 하는 일 |
|---|---|---|
| KaTeX | `<span class="arithmatex">` | `\(...\)`·`\[...\]`로 감싸인 수식을 그린다 |
| Mermaid | `<div class="mermaid">` | 다이어그램 소스를 SVG로 바꾼다 |

블로그(`templates/blog/detail.html`)가 쓰는 것과 **같은 버전·같은 설정**이다.
`throwOnError: false`는 수식 하나가 틀렸다고 글 전체가 안 보이는 일을 막는다 —
틀린 수식만 빨갛게 남고 나머지는 정상으로 그려진다.

## 주의

- 이 파일은 `converter/snippet.py`의 `THEME_SNIPPET`에서 생성했다.
  **스니펫을 고칠 일이 생기면 그 파일을 고친다.** 여기만 고치면 화면의
  '테마 스니펫' 버튼과 내용이 어긋난다.
- Mermaid 테마는 `neutral`로 뒀다. 블로그 본문은 `dark`를 쓰지만, Blogger 글 배경은
  보통 흰색이라 그대로 쓰면 다이어그램이 거의 안 보인다.
