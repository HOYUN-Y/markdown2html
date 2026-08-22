"""화면(라우트)과 도구 목록 검증.

변환 로직은 `test_convert.py`·`test_to_markdown.py`가 본다. 여기서 잡으려는 것은
**화면이 안 뜨는 사고**다 — 도구를 늘릴 때 `tools.py`·라우트·템플릿 셋 중 하나를
빠뜨리면 탭은 보이는데 눌러도 404가 난다.

    .venv/bin/python -m unittest discover -s tests -v
"""

import re
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import diagrams  # noqa: E402
import drawio  # noqa: E402
import tools  # noqa: E402
from app import app  # noqa: E402
from converter import theme  # noqa: E402
from converter.snippet import MERMAID_SRC, MERMAID_THEME, THEME_SNIPPET  # noqa: E402


#: 이 파일은 화면이 **열리는지**를 본다. 로그인은 `test_auth.py`가 따로 본다.
#:
#: 개발자가 로컬에 `TOOLS_PASSWORD_HASH`를 설정해 두면 여기 있는 모든 요청이
#: 로그인으로 튕겨 테스트가 무더기로 깨진다 — 코드가 아니라 **환경 때문에** 깨지는
#: 것이라 원인을 찾기 어렵다. 이 파일이 도는 동안에는 로그인을 꺼 둔다.
_env = None


def setUpModule():
    global _env
    _env = mock.patch.dict("os.environ", {"TOOLS_PASSWORD_HASH": ""}, clear=False)
    _env.start()


def tearDownModule():
    _env.stop()


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

    def test_drawio_page_opens(self):
        self.assertEqual(self.client.get("/drawio").status_code, 200)

    def test_drawio_tab_is_current_not_soon(self):
        page = self.client.get("/drawio").get_data(as_text=True)
        self.assertIn(">draw.io 다이어그램</span>", page)
        self.assertNotIn("draw.io 다이어그램<em", page)

    def test_drawio_page_carries_embed_url_and_origin(self):
        """편집기 주소와 origin이 함께 나가야 JS가 메시지를 받아들인다."""
        page = self.client.get("/drawio").get_data(as_text=True)
        # 속성 안이라 `&`가 `&amp;`로 나간다 — 브라우저가 되돌려 읽는다.
        self.assertIn(drawio.embed_url().replace("&", "&amp;"), page)
        self.assertIn('data-embed-origin="%s"' % drawio.EMBED_ORIGIN, page)

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


class DrawioConfigTest(unittest.TestCase):
    """임베드 설정이 어긋나면 **화면은 멀쩡한데 아무 반응이 없다.** 눈으로는 못 잡는다."""

    def test_embed_url_matches_origin(self):
        """주소와 origin이 갈라지면 JS가 모든 메시지를 조용히 버린다."""
        self.assertTrue(drawio.EMBED_ORIGIN.startswith("https://"))
        self.assertTrue(drawio.embed_url().startswith(drawio.EMBED_ORIGIN + "/"))

    def test_required_params_present(self):
        """둘 중 하나만 빠져도 init이 오지 않아 편집기가 영원히 준비되지 않는다."""
        self.assertEqual(drawio.EMBED_PARAMS.get("embed"), "1")
        self.assertEqual(drawio.EMBED_PARAMS.get("proto"), "json")

    def test_dark_is_pinned_off(self):
        """다크로 뜨면 내보낸 그림의 글자가 흰색이 되어 흰 배경에서 안 보인다."""
        self.assertEqual(drawio.EMBED_PARAMS.get("dark"), "0")

    def test_configure_is_not_enabled(self):
        """켜면 편집기가 우리 응답을 기다리며 로딩에서 멈춘다."""
        self.assertNotIn("configure", drawio.EMBED_PARAMS)

    def test_wrap_style_follows_the_diagram_spacing(self):
        """인라인 조각의 여백은 mermaid 다이어그램과 같아야 한다(한 글 안에서 섞인다)."""
        self.assertIn(theme.MERMAID_STYLE, drawio.WRAP_STYLE)


class ScriptWiringTest(unittest.TestCase):
    """JS가 찾는 id가 화면에 없으면 그 버튼만 **조용히** 죽는다.

    브라우저를 열지 않고 잡을 수 있는 몇 안 되는 화면 버그다.
    """

    ROOT = Path(__file__).resolve().parent.parent
    PAGES = [("/mermaid", "public/js/diagram.js"), ("/drawio", "public/js/drawio.js")]

    def test_every_id_the_script_looks_up_exists(self):
        client = app.test_client()
        for url, script in self.PAGES:
            with self.subTest(page=url):
                page = client.get(url).get_data(as_text=True)
                source = (self.ROOT / script).read_text(encoding="utf-8")
                wanted = set(re.findall(r'getElementById\("([^"]+)"\)', source))
                wanted |= set(re.findall(r'querySelectorAll?\("#([A-Za-z0-9_-]+)', source))
                present = set(re.findall(r'id="([^"]+)"', page))
                self.assertEqual(wanted - present, set(), "화면에 없는 id를 찾고 있다")


if __name__ == "__main__":
    unittest.main()
