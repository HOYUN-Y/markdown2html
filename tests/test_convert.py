"""변환 결과 검증.

stdlib unittest만 쓴다(pytest를 새 의존성으로 들이지 않기 위해).

    .venv/bin/python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from converter import convert  # noqa: E402

BASE = "https://blog.devprofessional.xyz"


class InlineStyleTest(unittest.TestCase):
    """Blogger에는 CSS를 넣을 데가 없다 — 스타일이 전부 인라인이어야 한다."""

    def test_heading_carries_blog_accent_bar(self):
        html = convert("## 소제목").html
        self.assertIn("border-left:3px solid #00215D", html)
        self.assertIn("color:#0D1220", html)

    def test_paragraph_and_link_styled(self):
        html = convert("본문 [링크](https://example.com) 입니다.").html
        self.assertIn('<p style="', html)
        self.assertIn("color:#00215D;text-decoration:underline", html)

    def test_table_and_blockquote_styled(self):
        html = convert("| a | b |\n|---|---|\n| 1 | 2 |\n\n> 인용").html
        self.assertIn("border-collapse:collapse", html)
        self.assertIn("border-left:3px solid #00215D", html)

    def test_inline_code_styled_but_block_code_untouched(self):
        html = convert("`인라인` 과\n\n```\nblock\n```").html
        # 인라인 code에는 배지 스타일이, 코드블록 안 code에는 pre용 스타일이 붙는다
        self.assertIn("background:#E9ECF4", html)
        self.assertIn("background:none;color:inherit", html)


class LinebreakSafetyTest(unittest.TestCase):
    """Blogger의 '엔터 = 줄바꿈' 설정이 켜져 있어도 결과가 같아야 한다."""

    SAMPLE = "# 제목\n\n문단1\n\n- 항목1\n- 항목2\n\n```python\na = 1\nb = 2\n```\n\n| a |\n|---|\n| 1 |\n"

    def test_no_newline_survives(self):
        result = convert(self.SAMPLE)
        self.assertEqual(result.html.count("\n"), 0)
        self.assertEqual(result.stats["newlines"], 0)

    def test_code_lines_become_br(self):
        html = convert("```python\na = 1\nb = 2\n```").html
        self.assertIn("<br>", html)

    def test_opt_out_keeps_code_newlines(self):
        html = convert("```python\na = 1\nb = 2\n```", safe_linebreaks=False).html
        self.assertIn("\n", html)
        self.assertNotIn("<br>", html)


class CodeBlockTest(unittest.TestCase):
    def test_known_language_is_highlighted_inline(self):
        result = convert("```python\ndef f():\n    return 1\n```")
        self.assertIn("<span style=\"color:", result.html.replace("; ", ";"))
        self.assertEqual(result.stats["code_blocks"], 1)
        self.assertEqual(result.warnings, [])

    def test_unknown_language_warns_but_keeps_code(self):
        result = convert("```wubbalubba\nhello world\n```")
        self.assertIn("hello world", result.html)
        self.assertTrue(any("wubbalubba" in w for w in result.warnings))

    def _plain_warning(self, result):
        return next((w for w in result.warnings if "색이 칠해지지 않은" in w), None)

    def test_untagged_block_warns(self):
        """언어 태그가 없으면 무채색이 되는데, 예전에는 **아무 신호도 없었다.**

        블로그 화면은 highlight.js가 언어를 자동 감지해 태그 없이도 칠한다. 그래서
        태그를 안 붙이면 같은 글이 블로그에서는 색이 있고 Blogger에서는 무채색이 된다.
        조용히 지나가면 붙여넣고 나서야 알게 된다.
        """
        self.assertIsNotNone(self._plain_warning(convert("```\ndef f(): pass\n```")))

    def test_colorless_language_warns_even_though_pygments_knows_it(self):
        """```text 는 Pygments가 아는 언어라 '모르는 언어' 경고에 안 걸린다.

        언어 이름이 아니라 **결과에 색이 붙었는지**로 판단해야 이게 잡힌다.
        """
        self.assertIsNotNone(self._plain_warning(convert("```text\nhello\n```")))

    def test_warning_lists_which_blocks(self):
        """어느 블록인지 안 알려주면 긴 글에서 찾을 수가 없다."""
        doc = "```python\na=1\n```\n\n```\nb=2\n```\n\n```\nc=3\n```\n"
        warning = self._plain_warning(convert(doc))
        self.assertIn("2개", warning)
        self.assertIn("2·3", warning)

    def test_empty_block_does_not_warn(self):
        """빈 블록은 칠할 내용이 없어서 span이 없는 것이다 — 언어를 적어도 안 바뀐다."""
        self.assertIsNone(self._plain_warning(convert("```\n```")))

    def test_warning_does_not_blame_the_language_name(self):
        """```text 는 이름이 맞는데도 걸린다. '모르는 이름'이라고 하면 안 된다 —
        멀쩡한 언어 이름을 고치러 다니게 만든다."""
        warning = self._plain_warning(convert("```text\nhello\n```"))
        self.assertNotIn("모르는 이름", warning)

    def test_tagged_blocks_do_not_warn(self):
        doc = "```python\na=1\n```\n\n```javascript\nvar b=2\n```\n"
        self.assertIsNone(self._plain_warning(convert(doc)))

    def test_warning_is_independent_of_output_mode(self):
        """색이 어디에 적히든(속성이든 스타일시트든) 무채색 여부는 같아야 한다."""
        for output in ("inline", "css"):
            with self.subTest(output=output):
                self.assertIsNotNone(
                    self._plain_warning(convert("```\nx\n```", output=output))
                )

    def test_language_name_survives_in_a_class(self):
        """언어 이름이 남아야 HTML을 다시 마크다운으로 되돌릴 수 있다.

        색은 이미 칠해져 있어 화면에는 영향이 없지만, 이 클래스가 없으면
        왕복에서 ```python 이 그냥 ``` 으로 무너진다.
        """
        for output in ("inline", "css"):
            with self.subTest(output=output):
                html = convert("```python\nx = 1\n```", output=output).html
                self.assertIn('class="language-python"', html)

    def test_untagged_block_gets_no_language_class(self):
        self.assertNotIn("language-", convert("```\nx = 1\n```").html)

    def test_html_special_chars_stay_escaped(self):
        # 이스케이프가 풀리면 Blogger 에디터가 태그로 해석해 글이 깨진다.
        result = convert("```html\n<div class=\"x\">a & b</div>\n```")
        self.assertIn("&lt;", result.html)
        self.assertIn("&amp;", result.html)
        self.assertNotIn('<div class="x">', result.html)

    def test_round_trip_of_escaped_entity(self):
        # 원문에 `&lt;` 라고 쓴 경우 — 그대로 보여야 한다.
        result = convert("```\n&lt;\n```")
        self.assertIn("&amp;lt;", result.html)

    def test_double_quotes_are_not_left_as_entities(self):
        # Python-Markdown은 "를 &quot;로 바꾼다. 되돌리지 않으면 코드에
        # `&quot;`가 글자 그대로 찍힌다(실제 문서에서 발견된 버그).
        result = convert('```python\nheaders = {"a": "b"}\n```')
        self.assertNotIn("&amp;quot;", result.html)
        self.assertIn("&quot;a&quot;", result.html)


class MermaidTest(unittest.TestCase):
    def test_becomes_mermaid_div_not_code_block(self):
        result = convert("```mermaid\ngraph TD\n  A-->B\n```")
        self.assertIn('<div class="mermaid"', result.html)
        self.assertNotIn("<pre", result.html)
        self.assertEqual(result.stats["mermaid"], 1)
        self.assertEqual(result.stats["code_blocks"], 0)

    def test_source_is_escaped_and_paragraph_wrapper_removed(self):
        html = convert("```mermaid\ngraph TD\n  A-->B & C\n```").html
        self.assertIn("A--&gt;B &amp; C", html)
        self.assertNotIn("<p>", html)

    def test_note_mentions_theme_snippet(self):
        result = convert("```mermaid\ngraph TD\n  A-->B\n```")
        self.assertTrue(any("Mermaid" in n for n in result.notes))

    def test_line_breaks_survive_as_entities(self):
        # 줄바꿈이 공백으로 접히면 Mermaid가 'Syntax error in text'를 낸다.
        # 개행 문자를 남길 수도 없어서(Blogger가 <br>로 바꾼다) `&#10;`을 쓴다.
        html = convert("```mermaid\ngraph TD\n  A-->B\n  B-->C\n```").html
        self.assertEqual(html.count("&#10;"), 2)
        self.assertEqual(html.count("\n"), 0)
        self.assertNotIn("<br>", html)


class MathTest(unittest.TestCase):
    def test_arithmatex_class_survives_inlining(self):
        result = convert("인라인 $a_1 + b_2$ 수식")
        self.assertIn('class="arithmatex"', result.html)
        self.assertTrue(result.stats["has_math"])
        self.assertTrue(any("KaTeX" in n for n in result.notes))

    def test_subscript_not_turned_into_italics(self):
        # arithmatex가 없으면 _가 <em>으로 해석돼 수식이 깨진다(블로그 주석 참고).
        html = convert("$a_1 + b_2$").html
        self.assertNotIn("<em>", html)


class AssetUrlTest(unittest.TestCase):
    def test_relative_image_absolutized(self):
        html = convert("![x](/media/a.png)", image_base_url=BASE).html
        self.assertIn(f'src="{BASE}/media/a.png"', html)

    def test_relative_link_absolutized(self):
        html = convert("[글](/posts/hello)", image_base_url=BASE).html
        self.assertIn(f'href="{BASE}/posts/hello"', html)

    def test_absolute_and_anchor_untouched(self):
        html = convert(
            "![x](https://cdn.example.com/a.png) [앵커](#section)", image_base_url=BASE
        ).html
        self.assertIn('src="https://cdn.example.com/a.png"', html)
        self.assertIn('href="#section"', html)

    def test_warns_when_base_missing(self):
        result = convert("![x](/media/a.png)")
        self.assertTrue(any("상대경로" in w for w in result.warnings))

    def test_no_warning_when_nothing_relative(self):
        result = convert("![x](https://cdn.example.com/a.png)")
        self.assertEqual(result.warnings, [])


class WrapperTest(unittest.TestCase):
    def test_wrapper_sets_blog_typography(self):
        html = convert("본문").html
        self.assertTrue(html.startswith('<div style="font-family:'))
        self.assertIn("font-size:18px;line-height:1.85", html)

    def test_can_opt_out(self):
        html = convert("본문", wrap=False).html
        self.assertTrue(html.startswith("<p"))


class PaletteTest(unittest.TestCase):
    """Blogger 테마가 검은 배경이면 라이트 팔레트 글자가 배경에 묻힌다."""

    SAMPLE = "## 소제목\n\n본문 [링크](https://e.com) `코드`\n\n> 인용\n\n| a |\n|---|\n| 1 |"

    def test_light_is_the_default(self):
        self.assertEqual(convert(self.SAMPLE).html, convert(self.SAMPLE, palette="light").html)

    def test_dark_uses_blog_dark_tokens(self):
        html = convert(self.SAMPLE, palette="dark").html
        self.assertIn("color:#D7DEEC", html)      # 본문
        self.assertIn("color:#F3F6FC", html)      # 제목
        self.assertIn("#6E9BE8", html)            # 강조(링크·h2 막대)
        self.assertNotIn("#1A1F2B", html)         # 라이트 본문색이 새면 안 된다

    def test_dark_darkens_code_background(self):
        self.assertIn("background:#0A0F1A", convert("```\na\n```", palette="dark").html)

    def test_inherit_sets_no_text_color(self):
        html = convert(self.SAMPLE, palette="inherit").html
        # 본문·제목에 색을 박지 않아야 Blogger 테마 색이 살아 있다.
        self.assertNotIn("color:#D7DEEC", html)
        self.assertNotIn("color:#1A1F2B", html)
        self.assertNotIn("color:#0D1220", html)
        # 링크·인용구 막대는 글자색을 따라간다.
        self.assertIn("currentColor", html)

    def test_inherit_still_styles_code_blocks(self):
        # 코드블록은 블로그에서도 두 테마 모두 어둡다 — 상속 모드에서도 유지한다.
        html = convert("```python\na = 1\n```", palette="inherit").html
        self.assertIn("background:#11162A", html)

    def test_unknown_palette_falls_back_to_light(self):
        self.assertEqual(
            convert(self.SAMPLE, palette="보라색").html,
            convert(self.SAMPLE, palette="light").html,
        )

    def test_all_palettes_keep_linebreak_safety(self):
        for name in ("light", "dark", "inherit"):
            with self.subTest(palette=name):
                self.assertEqual(convert(self.SAMPLE, palette=name).html.count("\n"), 0)


class CssOutputTest(unittest.TestCase):
    """`<style>` 블록 모드 — Blogger는 글 본문의 style 태그를 정상 처리한다."""

    SAMPLE = ("## 소제목\n\n본문 [링크](https://e.com) `코드`\n\n> 인용\n\n"
              "- 항목\n- 항목\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n"
              "```python\nx = \"a\"\n```")

    def test_style_block_comes_first(self):
        html = convert(self.SAMPLE, output="css").html
        self.assertTrue(html.startswith("<style>"))
        self.assertIn("</style><div class=\"md2b md2b-light\">", html)

    def test_body_has_no_inline_styles(self):
        html = convert(self.SAMPLE, output="css").html
        body = html.split("</style>", 1)[1]
        self.assertNotIn("style=", body.replace('style="margin:28px 0', ""))

    def test_every_rule_is_scoped(self):
        css = convert(self.SAMPLE, output="css").html.split("</style>")[0]
        # 스코프 없는 선택자가 하나라도 있으면 테마와 다른 글까지 건드린다.
        for rule in css.replace("<style>", "").split("}"):
            selector = rule.split("{")[0].strip()
            if not selector:
                continue
            for part in selector.split(","):
                self.assertTrue(
                    part.strip().startswith(".md2b"),
                    f"스코프 없는 선택자: {part.strip()!r}",
                )

    def test_palette_is_part_of_the_scope(self):
        # 팔레트가 다른 글이 같은 페이지에 있어도 서로 덮어쓰지 않아야 한다.
        light = convert(self.SAMPLE, output="css", palette="light").html
        dark = convert(self.SAMPLE, output="css", palette="dark").html
        self.assertIn(".md2b.md2b-light", light)
        self.assertIn(".md2b.md2b-dark", dark)
        self.assertNotIn(".md2b-dark", light)

    def test_text_colors_are_explicit_not_inherited(self):
        # 상속은 요소를 직접 겨냥한 테마 규칙(`p { color: … }`)에 무조건 진다.
        css = convert(self.SAMPLE, output="css", palette="dark").html.split("</style>")[0]
        self.assertIn(".md2b.md2b-dark p", css)
        self.assertIn("#D7DEEC", css)

    def test_inherit_palette_sets_no_text_color(self):
        css = convert(self.SAMPLE, output="css", palette="inherit").html.split("</style>")[0]
        self.assertNotIn("color:#D7DEEC", css)
        self.assertNotIn("color:#1A1F2B", css)

    def test_syntax_colors_move_into_the_stylesheet(self):
        result = convert(self.SAMPLE, output="css")
        css, body = result.html.split("</style>", 1)
        self.assertIn("pre", css)
        self.assertIn("<pre><code", body)                    # 껍데기에 style= 이 없다
        self.assertNotIn("<pre style=", body)
        self.assertIn('class="', body)                       # 강조는 클래스로

    def test_no_newline_anywhere_including_css(self):
        # <style> 안의 개행도 Blogger가 <br>로 바꾼다 — 그 지점부터 CSS가 깨진다.
        self.assertEqual(convert(self.SAMPLE, output="css").html.count("\n"), 0)

    def test_css_wins_on_long_posts_and_loses_on_short_ones(self):
        """스타일시트는 고정 비용이다 — 짧은 글에서는 인라인이 더 짧다.

        이걸 모르고 'CSS 모드가 항상 짧다'고 안내하면 안 된다.
        """
        short = self.SAMPLE
        long_post = self.SAMPLE + ("\n\n문단입니다. " * 400)

        def size(text, mode):
            return convert(text, output=mode).stats["characters"]

        self.assertGreater(size(short, "css"), size(short, "inline"))
        self.assertLess(size(long_post, "css"), size(long_post, "inline"))

    def test_wrap_off_is_reported_not_silently_ignored(self):
        result = convert(self.SAMPLE, output="css", wrap=False)
        self.assertIn('class="md2b', result.html)
        self.assertTrue(any("컨테이너" in n for n in result.notes))


class EmptyInputTest(unittest.TestCase):
    def test_empty_is_not_an_error(self):
        result = convert("")
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.stats["code_blocks"], 0)


if __name__ == "__main__":
    unittest.main()
