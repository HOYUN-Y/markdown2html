"""로그인 — 이 사이트를 주소만 알면 누구나 쓰는 상태로 두지 않기 위한 것.

Vercel의 Deployment Protection은 **쓸 수 없다.** Hobby 플랜에서는 프리뷰만 가릴 수
있고 프로덕션 도메인은 계속 공개다(프로덕션까지 가리려면 Pro 이상). 그래서 앱에서 직접 막는다.

설계:

- **비밀번호 하나.** 쓰는 사람이 한 명이라 계정 테이블이 필요 없다.
- **세션은 서명된 쿠키.** 서버에 세션 저장소를 두지 않는다 — Vercel 함수는 요청마다
  다른 인스턴스일 수 있어서, 서버 쪽에 상태를 두면 로그인이 제멋대로 풀린다.
- **평문 비밀번호는 어디에도 두지 않는다.** 환경변수에는 해시만 넣는다
  (`scripts/make_password_hash.py`로 만든다).

환경변수 둘:

    TOOLS_PASSWORD_HASH   비밀번호 해시. **이 값이 없으면 로그인 기능이 꺼진다.**
    SECRET_KEY            쿠키 서명 키. 바뀌면 기존 로그인이 전부 풀린다.

`TOOLS_PASSWORD_HASH`가 없을 때의 동작이 환경마다 다르다 — 의도한 것이다.

- 로컬: 그냥 열린다. 개발할 때마다 비밀번호를 넣게 하지 않는다.
- 배포본(Vercel): **503으로 잠근다.** 설정을 빠뜨린 채 올라가면 사이트가 통째로
  공개되는데, 그건 조용히 넘어가서는 안 되는 사고다. 열어 두는 대신 닫는 쪽으로 실패한다.
"""

from __future__ import annotations

import os
import secrets
from datetime import timedelta

from flask import jsonify, redirect, request, session, url_for
from werkzeug.security import check_password_hash

#: 해시 방식을 못 박는다. Werkzeug 기본값(scrypt)은 OpenSSL 빌드에 따라
#: `hashlib.scrypt`가 없을 수 있어(실제로 이 저장소의 로컬 파이썬에 없다) 환경이
#: 갈리면 검증이 통째로 실패한다. pbkdf2는 어디에나 있다.
HASH_METHOD = "pbkdf2:sha256"

#: 로그인 유지 기간. 개인 도구라 짧게 잡을 이유가 없다.
SESSION_LIFETIME = timedelta(days=30)

SESSION_KEY = "authed"

#: 로그인 없이 지나갈 수 있는 곳. 정적 파일은 배포본에서 CDN이 직접 내보내므로
#: 어차피 함수까지 오지 않는다(그 안에 가릴 것도 없다).
OPEN_ENDPOINTS = {"login", "static"}


def password_hash() -> str:
    return (os.environ.get("TOOLS_PASSWORD_HASH") or "").strip()


def is_hosted() -> bool:
    """Vercel 위에서 도는가. 런타임이 넣어 주는 값이다."""
    return bool(os.environ.get("VERCEL"))


def is_enabled() -> bool:
    """로그인 기능이 켜져 있는가(= 해시가 설정돼 있는가)."""
    return bool(password_hash())


def secret_key() -> str:
    """쿠키 서명 키.

    배포본에서 임시 키를 쓰면 **인스턴스마다 키가 달라 로그인이 계속 풀린다.**
    조용히 이상하게 도느니 뜨지 않는 편이 낫다.
    """
    key = (os.environ.get("SECRET_KEY") or "").strip()
    if key:
        return key
    if is_hosted():
        raise RuntimeError(
            "SECRET_KEY 환경변수가 없습니다. Vercel 프로젝트 설정에 넣어 주세요."
        )
    # 로컬 전용. 서버를 다시 띄우면 로그인이 풀리는 것 말고는 문제가 없다.
    return secrets.token_hex(32)


def check(password: str) -> bool:
    stored = password_hash()
    if not stored or not password:
        return False
    return check_password_hash(stored, password)


def log_in() -> None:
    session.permanent = True
    session[SESSION_KEY] = True


def log_out() -> None:
    session.pop(SESSION_KEY, None)


def is_logged_in() -> bool:
    return bool(session.get(SESSION_KEY))


def guard():
    """모든 요청 앞에 선다. `app.before_request(auth.guard)`.

    화면 하나하나에 데코레이터를 붙이지 않는 것은, **도구를 새로 만들 때 빠뜨리면
    그 화면만 공개되기 때문이다.** 기본을 '막힘'으로 두고 예외를 적는다.
    """
    if request.endpoint in OPEN_ENDPOINTS:
        return None

    if not is_enabled():
        if is_hosted():
            return (
                "로그인 설정이 되어 있지 않습니다 (TOOLS_PASSWORD_HASH). "
                "설정 전까지 잠급니다.",
                503,
            )
        return None

    if is_logged_in():
        return None

    # 화면은 로그인으로 보내고, API는 JSON으로 답한다 — 화면 JS가 HTML 리다이렉트를
    # 받으면 파싱에 실패해 '서버에 연결하지 못했습니다'라는 엉뚱한 말을 하게 된다.
    if request.path.startswith("/api/"):
        return jsonify(error="로그인이 필요합니다. 새로고침한 뒤 다시 로그인해 주세요."), 401
    return redirect(url_for("login", next=request.full_path.rstrip("?")))
