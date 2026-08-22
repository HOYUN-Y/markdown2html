"""문서 저장 API 검증.

**진짜 DB를 붙이지 않는다.** 붙이면 테스트가 네트워크와 남의 서비스에 매이고,
연결이 안 되는 날 코드와 상관없이 빨개진다. 여기서 보는 것은 우리 쪽 판단이다 —
설정이 없을 때 무엇을 답하는지, 이상한 입력을 거르는지, 제목을 어떻게 채우는지.

실제 SQL은 `db.py`가 들고 있고, 그건 배포본에서 사람이 눌러 확인한다.

    .venv/bin/python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db  # noqa: E402
from app import app  # noqa: E402

#: 로그인은 `test_auth.py`가 본다. 여기서는 꺼 둔다.
_env = None


def setUpModule():
    global _env
    _env = mock.patch.dict("os.environ", {"TOOLS_PASSWORD_HASH": ""}, clear=False)
    _env.start()


def tearDownModule():
    _env.stop()


def connected(**fakes):
    """DB가 붙어 있는 셈 치고, 오가는 값만 가짜로 바꾼다."""
    patches = [mock.patch("db.is_configured", return_value=True)]
    for name, value in fakes.items():
        patches.append(mock.patch("db." + name, value))
    return patches


class Patched:
    def __init__(self, patches):
        self.patches = patches

    def __enter__(self):
        for p in self.patches:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in reversed(self.patches):
            p.stop()
        return False


class NotConnectedTest(unittest.TestCase):
    """DB가 없을 때. **화면은 살아 있어야 하고** 저장만 안 되어야 한다."""

    def setUp(self):
        self.client = app.test_client()

    def test_pages_still_open(self):
        with mock.patch("db.is_configured", return_value=False):
            for path in ("/", "/mermaid", "/drawio"):
                with self.subTest(page=path):
                    self.assertEqual(self.client.get(path).status_code, 200)

    def test_save_bar_is_not_drawn(self):
        """눌러도 아무 일이 없는 버튼을 두느니 자리 자체를 두지 않는다."""
        with mock.patch("db.is_configured", return_value=False):
            page = self.client.get("/mermaid").get_data(as_text=True)
            self.assertNotIn('id="docsMount"', page)

    def test_save_bar_appears_when_connected(self):
        with mock.patch("db.is_configured", return_value=True):
            page = self.client.get("/mermaid").get_data(as_text=True)
            self.assertIn('id="docsMount"', page)

    def test_api_says_why_instead_of_failing_oddly(self):
        with mock.patch("db.is_configured", return_value=False):
            response = self.client.get("/api/docs?tool=mermaid")
            self.assertEqual(response.status_code, 503)
            self.assertIn("DATABASE_URL", response.get_json()["error"])


class ValidationTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_unknown_tool_is_refused(self):
        """아무 값이나 받으면 목록이 오염된다."""
        with Patched(connected()):
            self.assertEqual(self.client.get("/api/docs?tool=없는도구").status_code, 400)
            response = self.client.post("/api/docs", json={"tool": "x", "content": "y"})
            self.assertEqual(response.status_code, 400)

    def test_empty_content_is_refused(self):
        with Patched(connected()):
            response = self.client.post(
                "/api/docs", json={"tool": "mermaid", "content": "   "}
            )
            self.assertEqual(response.status_code, 400)

    def test_too_long_content_is_refused(self):
        with Patched(connected()):
            response = self.client.post(
                "/api/docs", json={"tool": "mermaid", "content": "가" * (db.MAX_CONTENT + 1)}
            )
            self.assertEqual(response.status_code, 413)

    def test_missing_title_is_filled_in_not_refused(self):
        """제목을 비워 두고 저장하는 일이 잦다. 막지 말고 채워 준다."""
        seen = {}

        def fake_save(tool, title, content, doc_id=None):
            seen.update(tool=tool, title=title, content=content, doc_id=doc_id)
            return {"id": 1, "tool": tool, "title": title, "updated_at": None}

        with Patched(connected(save=fake_save)):
            response = self.client.post(
                "/api/docs", json={"tool": "drawio", "content": "<mxfile/>"}
            )
            self.assertEqual(response.status_code, 200)
        self.assertEqual(seen["title"], "제목 없음")
        self.assertIsNone(seen["doc_id"])

    def test_title_is_trimmed_to_the_limit(self):
        seen = {}

        def fake_save(tool, title, content, doc_id=None):
            seen["title"] = title
            return {"id": 1, "tool": tool, "title": title, "updated_at": None}

        with Patched(connected(save=fake_save)):
            self.client.post(
                "/api/docs",
                json={"tool": "convert", "title": "제" * (db.MAX_TITLE + 50), "content": "x"},
            )
        self.assertEqual(len(seen["title"]), db.MAX_TITLE)


class RoundTripTest(unittest.TestCase):
    """화면이 실제로 밟는 길 — 저장 → 목록 → 열기 → 삭제."""

    def setUp(self):
        self.client = app.test_client()

    def test_save_then_list_then_open(self):
        doc = {"id": 7, "tool": "mermaid", "title": "흐름도", "updated_at": "2026-08-22T00:00:00+00:00"}
        full = dict(doc, content="graph TD\n  A-->B")

        with Patched(connected(
            save=lambda *a, **k: doc,
            listing=lambda tool: [doc],
            get=lambda doc_id: full if doc_id == 7 else None,
        )):
            saved = self.client.post(
                "/api/docs", json={"tool": "mermaid", "title": "흐름도", "content": "graph TD"}
            ).get_json()
            self.assertEqual(saved["doc"]["id"], 7)

            listed = self.client.get("/api/docs?tool=mermaid").get_json()
            self.assertEqual(len(listed["docs"]), 1)
            # 목록에 본문을 싣지 않는다 — 필요 없고 무겁다.
            self.assertNotIn("content", listed["docs"][0])

            opened = self.client.get("/api/docs/7").get_json()
            self.assertIn("graph TD", opened["doc"]["content"])

    def test_missing_document_is_404_not_500(self):
        with Patched(connected(get=lambda doc_id: None, delete=lambda doc_id: False)):
            self.assertEqual(self.client.get("/api/docs/999").status_code, 404)
            self.assertEqual(self.client.delete("/api/docs/999").status_code, 404)

    def test_delete_reports_success(self):
        with Patched(connected(delete=lambda doc_id: True)):
            response = self.client.delete("/api/docs/7")
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.get_json()["ok"])

    def test_database_trouble_becomes_a_readable_error(self):
        """연결이 끊기면 500 스택이 아니라 사람이 읽을 말이 나가야 한다."""
        def boom(tool):
            raise RuntimeError("connection refused")

        # 일부러 터뜨리는 것이라 스택이 찍힌다. 통과한 테스트 출력에 섞이면
        # 실패한 것처럼 보이므로 이 테스트 동안만 로그를 막는다.
        with Patched(connected(listing=boom)), mock.patch.object(app.logger, "exception"):
            response = self.client.get("/api/docs?tool=mermaid")
            self.assertEqual(response.status_code, 502)
            self.assertIn("저장소에 접근하지 못했습니다", response.get_json()["error"])


class ToolListTest(unittest.TestCase):
    def test_db_tools_match_the_site_tools(self):
        """도구를 늘리면서 여기를 빠뜨리면 그 도구만 저장이 안 된다."""
        import tools

        ready = {t["slug"] for t in tools.TOOLS if t["ready"]}
        self.assertEqual(ready - set(db.TOOLS), set())


if __name__ == "__main__":
    unittest.main()
