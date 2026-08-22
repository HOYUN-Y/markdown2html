"""로그인 비밀번호의 해시를 만든다. 환경변수에 넣을 값이다.

    .venv/bin/python scripts/make_password_hash.py

비밀번호를 **명령줄 인자로 받지 않는다.** 인자로 받으면 셸 기록(`~/.zsh_history`)과
`ps` 목록에 평문이 남는다. 화면에도 찍지 않는다(`getpass`).

나온 해시를 두 곳에 넣는다.

- Vercel: 프로젝트 → Settings → Environment Variables → `TOOLS_PASSWORD_HASH`
- 로컬(선택): `export TOOLS_PASSWORD_HASH='...'` — 넣지 않으면 로컬은 그냥 열린다

`SECRET_KEY`도 함께 필요하다. 아래 명령으로 만든다.

    .venv/bin/python -c "import secrets; print(secrets.token_hex(32))"
"""

import sys
from getpass import getpass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from werkzeug.security import generate_password_hash  # noqa: E402

import auth  # noqa: E402


def main() -> int:
    first = getpass("비밀번호: ")
    if len(first) < 8:
        print("너무 짧습니다. 8자 이상으로 해 주세요.", file=sys.stderr)
        return 1
    if first != getpass("한 번 더: "):
        print("두 번 입력한 값이 다릅니다.", file=sys.stderr)
        return 1

    print()
    print("아래 값을 TOOLS_PASSWORD_HASH 에 넣으세요 (비밀번호가 아니라 해시입니다).")
    print()
    print(generate_password_hash(first, method=auth.HASH_METHOD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
