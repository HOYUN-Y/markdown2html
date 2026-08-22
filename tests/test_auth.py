"""로그인 검증.

이 사이트는 주소만 알면 누구나 열 수 있는 곳에 있다(`tools.devprofessional.xyz`).
Vercel의 Deployment Protection은 Hobby 플랜에서 프로덕션을 못 가리므로 앱이 직접 막는다.

여기서 잡으려는 사고는 하나다 — **가려야 할 화면이 열려 있는 것.**

    .venv/bin/python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import auth  # noqa: E402
import tools  # noqa: E402
from app import app  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

PASSWORD = "열려라참깨1234"
HASH = generate_password_hash(PASSWORD, method=auth.HASH_METHOD)

#: 가려야 하는 화면 전부. 도구를 늘리면 여기도 늘어난다.
PAGES = ["/"] + [t["url"] for t in tools.TOOLS if t["ready"] and t["url"] != "/"]
APIS = ["/api/convert", "/api/to-markdown"]


def locked(**extra):
    """로그인이 켜진 환경."""
    env = {"TOOLS_PASSWORD_HASH": HASH}
    env.update(extra)
    return mock.patch.dict("os.environ", env, clear=False)


class LockedTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_every_page_redirects_to_login(self):
        with locked():
            for path in PAGES:
                with self.subTest(page=path):
                    response = self.client.get(path)
                    self.assertEqual(response.status_code, 302)
                    self.assertIn("/login", response.headers["Location"])

    def test_apis_answer_json_not_a_redirect(self):
        """화면 JS가 HTML 리다이렉트를 받으면 '서버에 연결하지 못했습니다'라고 잘못 말한다."""
        with locked():
            for path in APIS:
                with self.subTest(api=path):
                    response = self.client.post(path, json={})
                    self.assertEqual(response.status_code, 401)
                    self.assertIn("로그인", response.get_json()["error"])

    def test_login_page_itself_is_open(self):
        with locked():
            self.assertEqual(self.client.get("/login").status_code, 200)

    def test_wrong_password_is_refused(self):
        with locked():
            response = self.client.post("/login", data={"password": "틀린비밀번호"})
            self.assertEqual(response.status_code, 401)
            self.assertIn("맞지 않습니다", response.get_data(as_text=True))

    def test_right_password_opens_everything(self):
        with locked():
            response = self.client.post("/login", data={"password": PASSWORD})
            self.assertEqual(response.status_code, 302)
            for path in PAGES:
                with self.subTest(page=path):
                    self.assertEqual(self.client.get(path).status_code, 200)

    def test_logout_closes_it_again(self):
        with locked():
            self.client.post("/login", data={"password": PASSWORD})
            self.assertEqual(self.client.get("/").status_code, 200)
            self.client.post("/logout")
            self.assertEqual(self.client.get("/").status_code, 302)

    def test_next_only_follows_our_own_paths(self):
        """열린 리다이렉트가 되면 이 화면이 피싱 발판이 된다."""
        with locked():
            response = self.client.post(
                "/login", data={"password": PASSWORD, "next": "https://evil.example/x"}
            )
            self.assertNotIn("evil.example", response.headers["Location"])
        with locked():
            client = app.test_client()
            response = client.post(
                "/login", data={"password": PASSWORD, "next": "//evil.example/x"}
            )
            self.assertNotIn("evil.example", response.headers["Location"])

    def test_next_brings_you_back_to_where_you_were(self):
        with locked():
            response = self.client.post(
                "/login", data={"password": PASSWORD, "next": "/drawio"}
            )
            self.assertTrue(response.headers["Location"].endswith("/drawio"))


class NotConfiguredTest(unittest.TestCase):
    """해시를 안 넣었을 때. 로컬은 열고, 배포본은 **잠근다.**"""

    def setUp(self):
        self.client = app.test_client()

    def test_local_stays_open(self):
        with mock.patch.dict("os.environ", {"TOOLS_PASSWORD_HASH": ""}, clear=False):
            self.assertEqual(self.client.get("/").status_code, 200)

    def test_hosted_locks_itself_instead_of_serving(self):
        """설정을 빠뜨린 채 올라가면 사이트가 통째로 공개된다 — 닫는 쪽으로 실패한다."""
        with mock.patch.dict(
            "os.environ", {"TOOLS_PASSWORD_HASH": "", "VERCEL": "1"}, clear=False
        ):
            response = self.client.get("/")
            self.assertEqual(response.status_code, 503)


class SecretKeyTest(unittest.TestCase):
    def test_hosted_without_secret_key_refuses_to_start(self):
        """배포본에서 임시 키를 쓰면 인스턴스마다 키가 달라 로그인이 계속 풀린다."""
        with mock.patch.dict("os.environ", {"SECRET_KEY": "", "VERCEL": "1"}, clear=False):
            with self.assertRaises(RuntimeError):
                auth.secret_key()

    def test_local_falls_back_to_a_throwaway_key(self):
        with mock.patch.dict("os.environ", {"SECRET_KEY": ""}, clear=False):
            self.assertTrue(auth.secret_key())


if __name__ == "__main__":
    unittest.main()
