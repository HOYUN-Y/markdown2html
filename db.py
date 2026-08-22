"""도구별 문서 저장 — Neon Postgres.

`localStorage`는 **브라우저마다 따로**다. 노트북에서 그린 그림이 데스크톱에 없고,
브라우저 데이터를 지우면 사라진다. 남겨 둘 것은 서버에 둔다.

역할을 나눈다.

- `localStorage` — **작업 중인 임시본.** 자동 저장이 계속 덮어쓴다.
- 이 테이블 — **남겨 둘 것.** 사용자가 `저장`을 눌렀을 때만 들어온다.
  (draw.io는 도형을 끌 때마다 autosave가 오는데 그걸 매번 DB로 보내면 요청이 폭주한다.)

저장하는 것은 **원본뿐이다.** 마크다운 원문·mermaid 소스·`.drawio` XML만 넣고,
변환 결과(HTML·SVG·PNG)는 넣지 않는다 — 언제든 다시 만들 수 있고, 넣어 두면
원본을 고쳤을 때 조용히 어긋난다.

SQLite를 쓰지 않는 이유: Vercel 함수는 요청마다 다른 인스턴스일 수 있고 디스크도
사라진다. 연결은 요청마다 열고 닫는다(Neon의 풀링 주소를 쓰면 그 비용이 작다).
"""

from __future__ import annotations

import os
from contextlib import contextmanager

#: 연결 문자열이 담길 환경변수. Vercel에 Neon을 붙이면 이 이름들 중 하나로 들어온다.
#: 이름이 통합돼 있지 않아 순서대로 찾는다.
URL_ENV_NAMES = (
    "DATABASE_URL",
    "POSTGRES_URL",
    "POSTGRES_URL_NON_POOLING",
    "NEON_DATABASE_URL",
)

#: 도구 slug. `tools.py`의 목록과 같아야 한다 — 아무 값이나 받으면 목록이 오염된다.
TOOLS = ("convert", "mermaid", "drawio")

#: 제목·본문 상한. 본문은 draw.io가 그림 안에 사진을 넣으면 커진다.
MAX_TITLE = 200
MAX_CONTENT = 2_000_000

_ready = False


def url() -> str:
    for name in URL_ENV_NAMES:
        value = (os.environ.get(name) or "").strip()
        if value:
            return value
    return ""


def is_configured() -> bool:
    return bool(url())


class NotConfigured(RuntimeError):
    """DB가 붙어 있지 않다. 화면을 죽이지 말고 저장 기능만 끈다."""


@contextmanager
def _connect():
    if not is_configured():
        raise NotConfigured("DATABASE_URL이 설정되어 있지 않습니다.")
    import psycopg  # 이 경로에서만 필요하다. 없는 환경에서 화면까지 죽이지 않는다.

    # prepare_threshold=None — **준비된 구문(prepared statement)을 쓰지 않는다.**
    # Neon이 주는 DATABASE_URL은 PgBouncer를 거치는 풀링 주소이고, 트랜잭션 풀링에서는
    # 서버 쪽 준비된 구문이 다음 요청과 엉켜 `prepared statement "_pg3_0" already exists`가
    # 난다. 요청마다 연결을 새로 여는 지금 구조에서는 실제로 걸릴 일이 드물지만,
    # 걸리면 원인을 찾기가 매우 어려운 종류라 아예 꺼 둔다.
    with psycopg.connect(url(), connect_timeout=10, prepare_threshold=None) as conn:
        yield conn


def _ensure(conn) -> None:
    """테이블이 없으면 만든다.

    마이그레이션 도구를 들이지 않는다 — 테이블 하나짜리다. 프로세스마다 한 번만
    확인하고(`_ready`), `IF NOT EXISTS`라 여러 인스턴스가 동시에 불러도 안전하다.
    """
    global _ready
    if _ready:
        return
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id          bigserial PRIMARY KEY,
                tool        text        NOT NULL,
                title       text        NOT NULL,
                content     text        NOT NULL,
                created_at  timestamptz NOT NULL DEFAULT now(),
                updated_at  timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        # 목록은 항상 '한 도구의 최근 순'으로 읽는다.
        cur.execute(
            "CREATE INDEX IF NOT EXISTS documents_tool_updated "
            "ON documents (tool, updated_at DESC)"
        )
    conn.commit()
    _ready = True


def _row(record) -> dict:
    doc_id, tool, title, updated_at = record[0], record[1], record[2], record[3]
    return {
        "id": doc_id,
        "tool": tool,
        "title": title,
        "updated_at": updated_at.isoformat() if updated_at else None,
    }


def listing(tool: str) -> list:
    """한 도구의 문서 목록. **본문은 싣지 않는다** — 목록에 필요 없고 무겁다."""
    with _connect() as conn:
        _ensure(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tool, title, updated_at FROM documents "
                "WHERE tool = %s ORDER BY updated_at DESC LIMIT 200",
                (tool,),
            )
            return [_row(record) for record in cur.fetchall()]


def get(doc_id: int) -> dict | None:
    with _connect() as conn:
        _ensure(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tool, title, updated_at, content FROM documents WHERE id = %s",
                (doc_id,),
            )
            record = cur.fetchone()
            if not record:
                return None
            doc = _row(record)
            doc["content"] = record[4]
            return doc


def save(tool: str, title: str, content: str, doc_id: int | None = None) -> dict:
    """새로 넣거나(id 없음), 열어 둔 문서를 덮어쓴다(id 있음).

    덮어쓰기에서 `tool`을 조건에 함께 넣는 것은, 다른 도구의 문서를 실수로
    덮어쓰지 않게 하려는 것이다.
    """
    with _connect() as conn:
        _ensure(conn)
        with conn.cursor() as cur:
            if doc_id:
                cur.execute(
                    "UPDATE documents SET title = %s, content = %s, updated_at = now() "
                    "WHERE id = %s AND tool = %s "
                    "RETURNING id, tool, title, updated_at",
                    (title, content, doc_id, tool),
                )
                record = cur.fetchone()
                if record:
                    conn.commit()
                    return _row(record)
                # 지워진 문서를 덮어쓰려 한 것이다. 잃지 않도록 새로 넣는다.
            cur.execute(
                "INSERT INTO documents (tool, title, content) VALUES (%s, %s, %s) "
                "RETURNING id, tool, title, updated_at",
                (tool, title, content),
            )
            record = cur.fetchone()
        conn.commit()
        return _row(record)


def delete(doc_id: int) -> bool:
    with _connect() as conn:
        _ensure(conn)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
            removed = cur.rowcount > 0
        conn.commit()
        return removed
