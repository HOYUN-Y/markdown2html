"""HTML → 마크다운 검증.

두 축으로 본다.

1. **왕복** — `md → html → md`가 원문으로 돌아오는가. 정방향 변환기의 출력은
   우리가 만든 구조라, 여기서 어긋나면 둘 중 하나가 틀린 것이다.
2. **지저분한 입력** — Blogger·워드프로세서가 뱉는 div 수프를 버티는가.

    .venv/bin/python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from converter import convert  # noqa: E402
from converter.to_markdown import to_markdown  # noqa: E402


def roundtrip(markdown_text: str, **kwargs) -> str:
    """md → html → md. 비교하기 쉽게 끝 공백을 정리한다."""
    return to_markdown(convert(markdown_text, **kwargs).html).markdown.strip()


class RoundTripTest(unittest.TestCase):
    """정방향이 만든 HTML을 되돌리면 원문이어야 한다."""

    def assertRoundTrips(self, source: str):
        self.assertEqual(roundtrip(source), source.strip())

    def test_headings(self):
        self.assertRoundTrips("# 제목\n\n## 소제목\n\n### 더 작은 제목")

    def test_paragraph_with_emphasis(self):
        self.assertRoundTrips("본문 **강조** 와 *기울임* 입니다.")

    def test_link_and_image(self):
        self.assertRoundTrips("[링크](https://example.com)")
        self.assertRoundTrips("![그림](https://cdn.example.com/a.png)")

    def test_inline_code(self):
        self.assertRoundTrips("본문 `코드` 입니다.")

    def test_fenced_code_keeps_language(self):
        self.assertRoundTrips('```python\ndef hi(x):\n    return x\n```')

    def test_code_block_special_characters(self):
        # <, &, " 가 살아 돌아와야 한다 — 이스케이프가 한쪽만 되면 여기서 깨진다.
        self.assertRoundTrips('```html\n<div class="x">a & b</div>\n```')

    def test_flat_lists(self):
        self.assertRoundTrips("- 하나\n- 둘")
        self.assertRoundTrips("1. 하나\n2. 둘")

    def test_nested_list_uses_four_space_indent(self):
        """**4칸이어야 한다.**

        Python-Markdown 3.4.1은 CommonMark가 아니라 원조 Markdown.pl 규칙을 따라
        4칸부터 중첩으로 본다. 요즘 흔한 2칸으로 내보내면 되돌린 글을 다시 변환할 때
        중첩이 조용히 평평해진다.
        """
        self.assertRoundTrips("- 하나\n- 둘\n    - 중첩")
        self.assertRoundTrips("1. 하나\n2. 둘\n    1. 안쪽")

    def test_blockquote(self):
        self.assertRoundTrips("> 인용구입니다.")

    def test_table(self):
        self.assertRoundTrips("| 항목 | 값 |\n|---|---|\n| a | 1 |")

    def test_horizontal_rule(self):
        self.assertRoundTrips("앞\n\n---\n\n뒤")

    def test_inline_math(self):
        self.assertRoundTrips("수식 $a_1 + b_2$ 도 있다.")

    def test_mermaid_block(self):
        self.assertRoundTrips("```mermaid\ngraph TD\n  A-->B\n```")

    def test_survives_css_output_mode(self):
        """`<style>` 블록 모드로 만든 HTML도 되돌릴 수 있어야 한다."""
        source = "## 소제목\n\n본문 **강조**"
        self.assertEqual(roundtrip(source, output="css"), source)

    def test_survives_every_palette(self):
        source = "## 소제목\n\n본문과 [링크](https://e.com)"
        for palette in ("light", "dark", "inherit"):
            with self.subTest(palette=palette):
                self.assertEqual(roundtrip(source, palette=palette), source)


class StabilityTest(unittest.TestCase):
    """글자까지 같지 않아도 좋다 — **다시 변환했을 때 같은 화면**이면 된다.

    되돌린 마크다운의 표기가 원문과 달라도(들여쓰기 폭 등) 문제가 아니다. 문제는
    그걸 다시 변환했을 때 다른 HTML이 나오는 것이다. 그건 정보가 샜다는 뜻이다.
    """

    def assertStable(self, source: str):
        first = convert(source, wrap=False).html
        second = convert(to_markdown(first).markdown, wrap=False).html
        self.assertEqual(first, second)

    def test_tight_and_loose_lists_keep_their_kind(self):
        # 빈 줄 유무가 목록의 성격(loose/tight)을 바꾼다 — 항목 간격이 달라진다.
        self.assertStable("- 하나\n- 둘")
        self.assertStable("- 하나\n\n- 둘")
        self.assertStable("- 하나\n\n    - 중첩\n\n다음 문단")

    def test_deep_nesting(self):
        self.assertStable("- 1\n    - 2\n        - 3")

    def test_mixed_document(self):
        self.assertStable(
            "# 제목\n\n본문 **강조**\n\n```python\nx = 1\n```\n\n"
            "> 인용\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n- 목록\n    - 중첩\n"
        )


class CodeBlockTest(unittest.TestCase):
    def test_br_inside_pre_becomes_newline(self):
        """정방향은 `<pre>` 안 개행을 `<br>`로 바꾼다(Blogger 대응).

        그걸 모르고 get_text()를 부르면 코드가 한 줄로 뭉친다.
        """
        html = convert("```python\na = 1\nb = 2\n```").html
        self.assertIn("<br>", html)
        self.assertIn("a = 1\nb = 2", to_markdown(html).markdown)

    def test_fence_grows_when_body_has_backticks(self):
        html = '<pre><code>``` 안에 울타리가 있다</code></pre>'
        self.assertIn("````", to_markdown(html).markdown)

    def test_inline_code_containing_backtick(self):
        self.assertIn("`` ` ``", to_markdown("<p><code>`</code></p>").markdown)

    def test_language_from_various_class_names(self):
        for cls in ("language-python", "lang-python", "highlight-python"):
            with self.subTest(cls=cls):
                html = f'<pre><code class="{cls}">x = 1</code></pre>'
                self.assertTrue(to_markdown(html).markdown.startswith("```python"))


class DirtyHtmlTest(unittest.TestCase):
    """Blogger·워드프로세서가 뱉는 것들. 버릴 것을 버려야 한다."""

    def test_inline_styles_and_spans_are_stripped(self):
        html = ('<div style="font-family:Arial"><span style="color:#333">'
                '본문 <span style="font-weight:700"><strong>강조</strong></span></span></div>')
        self.assertEqual(to_markdown(html).markdown.strip(), "본문 **강조**")

    def test_script_and_style_are_dropped(self):
        html = "<style>p{color:red}</style><p>본문</p><script>alert(1)</script>"
        self.assertEqual(to_markdown(html).markdown.strip(), "본문")

    def test_b_and_i_become_strong_and_em(self):
        self.assertEqual(to_markdown("<p><b>굵게</b> <i>기울임</i></p>").markdown.strip(),
                         "**굵게** *기울임*")

    def test_div_soup_becomes_paragraphs(self):
        html = "<div>첫 문단</div><div>둘째 문단</div>"
        self.assertEqual(to_markdown(html).markdown.strip(), "첫 문단\n\n둘째 문단")

    def test_br_becomes_hard_line_break(self):
        self.assertIn("  \n", to_markdown("<p>첫 줄<br/>둘째 줄</p>").markdown)

    def test_comments_are_dropped(self):
        self.assertEqual(to_markdown("<!-- 주석 --><p>본문</p>").markdown.strip(), "본문")

    def test_empty_input(self):
        self.assertEqual(to_markdown("").markdown, "")


class UnconvertibleTest(unittest.TestCase):
    """마크다운에 문법이 없는 것은 **버리지 말고** HTML로 남긴다."""

    def test_table_with_colspan_is_kept_as_html(self):
        html = '<table><tr><td colspan="2">병합된 셀</td></tr></table>'
        result = to_markdown(html)
        self.assertIn("colspan", result.markdown)
        self.assertEqual(result.stats["raw_html_kept"], 1)
        self.assertTrue(any("옮길 수 없는" in w for w in result.warnings))

    def test_nested_table_is_kept_as_html(self):
        html = "<table><tr><td><table><tr><td>안쪽</td></tr></table></td></tr></table>"
        self.assertIn("<table", to_markdown(html).markdown)

    def test_iframe_is_kept_not_dropped(self):
        result = to_markdown('<p>앞 <iframe src="https://e.com"></iframe> 뒤</p>')
        self.assertIn("<iframe", result.markdown)

    def test_plain_table_is_converted_not_kept(self):
        html = "<table><tr><th>a</th></tr><tr><td>1</td></tr></table>"
        result = to_markdown(html)
        self.assertNotIn("<table", result.markdown)
        self.assertEqual(result.stats["raw_html_kept"], 0)


class EscapingTest(unittest.TestCase):
    """**필요한 만큼만** 이스케이프한다.

    전부 이스케이프하면 되돌린 글이 역슬래시 범벅이 되고, 더 나쁘게는 없던 문법을
    만들어 낸다(아래 `test_bracketed_text_does_not_become_math` 참고).
    """

    def test_bracketed_text_does_not_become_math(self):
        r"""실제 글에서 터진 버그의 회귀 테스트.

        본문의 `[이미지2 - 월별 단속]`을 `\[…\]`로 감쌌더니, 다시 변환할 때
        arithmatex가 그걸 LaTeX display 수식 구분자로 읽어 **문단 하나가 통째로
        수식이 됐다.** 링크가 될 수 없는 대괄호는 건드리면 안 된다.
        """
        back = to_markdown("<p>[이미지2 - 월별 단속 횟수]</p>").markdown
        self.assertNotIn(r"\[", back)
        self.assertNotIn("arithmatex", convert(back).html)

    def test_brackets_that_would_become_a_link_are_escaped(self):
        # 이건 그냥 두면 다시 변환할 때 진짜 링크가 된다.
        self.assertIn(r"\[", to_markdown("<p>[제목](주소) 형식</p>").markdown)

    def test_emphasis_only_escaped_when_it_could_bind(self):
        # `2 * 3`은 별표 양쪽이 공백이라 강조가 되지 않는다 — 건드릴 이유가 없다.
        self.assertNotIn(r"\*", to_markdown("<p>2 * 3 * 4</p>").markdown)
        # 글자에 붙으면 강조가 된다.
        self.assertIn(r"\_", to_markdown("<p>_밑줄_</p>").markdown)

    def test_line_start_markers_are_escaped(self):
        # 문단 첫 줄이 `-`로 시작하면 다시 변환할 때 목록이 된다.
        self.assertTrue(to_markdown("<p>- 처럼 보이는 문장</p>").markdown.startswith(r"\-"))
        self.assertTrue(to_markdown("<p># 해시로 시작</p>").markdown.startswith(r"\#"))

    def test_angle_bracket_only_escaped_when_it_looks_like_a_tag(self):
        self.assertNotIn(r"\<", to_markdown("<p>a &lt; b 입니다</p>").markdown)
        self.assertIn(r"\<", to_markdown("<p>&lt;div&gt; 태그</p>").markdown)

    def test_pipe_in_table_cell_is_escaped(self):
        html = "<table><tr><th>a|b</th></tr><tr><td>1</td></tr></table>"
        self.assertIn(r"a\|b", to_markdown(html).markdown)

    def test_code_content_is_not_escaped(self):
        # 코드 안의 * 는 그대로여야 한다 — 이스케이프하면 코드가 달라진다.
        self.assertIn("a * b", to_markdown("<pre><code>a * b</code></pre>").markdown)


class UrlTest(unittest.TestCase):
    BASE = "https://blog.devprofessional.xyz"

    def test_relative_links_absolutized(self):
        result = to_markdown('<p><a href="/posts/hi">글</a></p>', base_url=self.BASE)
        self.assertIn(f"{self.BASE}/posts/hi", result.markdown)

    def test_absolute_and_anchor_untouched(self):
        html = '<a href="https://e.com/x">a</a> <a href="#s">b</a>'
        result = to_markdown(html, base_url=self.BASE).markdown
        self.assertIn("https://e.com/x", result)
        self.assertIn("(#s)", result)

    def test_without_base_url_relative_stays(self):
        self.assertIn("(/posts/hi)", to_markdown('<a href="/posts/hi">글</a>').markdown)


class StatsTest(unittest.TestCase):
    def test_counts(self):
        html = convert("# t\n\n```python\nx=1\n```\n\n![i](https://e.com/a.png)\n\n"
                       "[l](https://e.com)\n\n| a |\n|---|\n| 1 |").html
        stats = to_markdown(html).stats
        self.assertEqual(stats["code_blocks"], 1)
        self.assertEqual(stats["images"], 1)
        self.assertEqual(stats["links"], 1)
        self.assertEqual(stats["tables"], 1)


if __name__ == "__main__":
    unittest.main()
