"""화면(라우트)과 도구 목록 검증.

변환 로직은 `test_convert.py`·`test_to_markdown.py`가 본다. 여기서 잡으려는 것은
**화면이 안 뜨는 사고**다 — 도구를 늘릴 때 `tools.py`·라우트·템플릿 셋 중 하나를
빠뜨리면 탭은 보이는데 눌러도 404가 난다.

    .venv/bin/python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import diagrams  # noqa: E402
import tools  # noqa: E402
from app import app  # noqa: E402
from converter.snippet import MERMAID_SRC, MERMAID_THEME, THEME_SNIPPET  # noqa: E402


class RouteTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_convert_page_opens(self):
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_mermaid_page_opens(self):
        self.assertEqual(self.client.get("/mermaid").status_code, 200)

    def test_every_ready_tool_has_a_working_url(self):
        """'준비 중'이 아닌 도구는 반드시 열려야 한다."""
        for tool in tools.TOOLS:
            if not tool["ready"]:
                continue
            with self.subTest(tool=tool["slug"]):
                self.assertTrue(tool["url"], "ready=True인데 url이 비어 있다")
                self.assertEqual(self.client.get(tool["url"]).status_code, 200)

    def test_mermaid_tab_is_current_not_soon(self):
        """탭이 '준비 중' 자리표시자가 아니라 현재 페이지로 그려져야 한다."""
        page = self.client.get("/mermaid").get_data(as_text=True)
        self.assertIn(">Mermaid 다이어그램</span>", page)          # 현재 탭
        self.assertNotIn("Mermaid 다이어그램<em", page)            # '준비 중' 배지
        self.assertIn('aria-current="page"', page)

    def test_page_carries_mermaid_source_and_templates(self):
        """편집기는 서버가 넘긴 CDN 주소·템플릿으로 그린다 — 둘 다 실려 나가야 한다."""
        page = self.client.get("/mermaid").get_data(as_text=True)
        self.assertIn(MERMAID_SRC, page)
        self.assertIn('data-mermaid-theme="%s"' % MERMAID_THEME, page)
        for template in diagrams.TEMPLATES:
            self.assertIn(template["name"], page)


class TemplateDataTest(unittest.TestCase):
    """불러오자마자 그려지지 않는 템플릿은 출발점이 되지 못한다."""

    #: 각 템플릿이 시작해야 하는 mermaid 선언. 오타 하나로 통째로 안 그려진다.
    HEADS = {
        "flowchart": ("graph ", "flowchart "),
        "sequence": ("sequenceDiagram",),
        "class": ("classDiagram",),
        "gantt": ("gantt",),
        "er": ("erDiagram",),
    }

    def test_templates_are_unique_and_complete(self):
        slugs = [t["slug"] for t in diagrams.TEMPLATES]
        self.assertEqual(len(slugs), len(set(slugs)))
        for template in diagrams.TEMPLATES:
            with self.subTest(slug=template["slug"]):
                for key in ("slug", "name", "summary", "source"):
                    self.assertTrue(template[key].strip(), "%s가 비어 있다" % key)

    def test_each_source_starts_with_its_declaration(self):
        for template in diagrams.TEMPLATES:
            with self.subTest(slug=template["slug"]):
                heads = self.HEADS[template["slug"]]
                self.assertTrue(
                    template["source"].startswith(heads),
                    "%s는 %s 로 시작해야 한다" % (template["slug"], " 또는 ".join(heads)),
                )

    def test_sources_have_no_fence_markers(self):
        """화면이 ```mermaid 를 붙여 준다. 원문에 있으면 두 겹이 된다."""
        for template in diagrams.TEMPLATES:
            with self.subTest(slug=template["slug"]):
                self.assertNotIn("```", template["source"])

    def test_default_source_is_one_of_the_templates(self):
        sources = [t["source"] for t in diagrams.TEMPLATES]
        self.assertIn(diagrams.DEFAULT_SOURCE, sources)


class SnippetSourceTest(unittest.TestCase):
    """mermaid 버전이 갈라지면 편집기에서 본 그림과 Blogger의 그림이 달라진다."""

    def test_theme_snippet_uses_the_same_constants(self):
        self.assertIn(MERMAID_SRC, THEME_SNIPPET)
        self.assertIn('theme: "%s"' % MERMAID_THEME, THEME_SNIPPET)


if __name__ == "__main__":
    unittest.main()
