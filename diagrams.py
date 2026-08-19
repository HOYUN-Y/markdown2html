"""다이어그램 편집기가 보여주는 시작 템플릿.

**빈 화면 앞에서 mermaid 문법을 기억해내야 하는 것**이 이 도구의 진짜 장벽이라,
자주 쓰는 도식 다섯 종류를 눌러서 불러올 수 있게 둔다. 새 종류를 늘릴 때는 아래
목록에만 추가하면 화면의 칩이 따라 늘어난다 — `tools.py`와 같은 방식이다.

`converter/`에 두지 않은 것은 **의도적이다.** 그 폴더는 블로그(django_blog_Enhanced)가
복사해 가는 변환 코어이고, 이 목록은 편집기 화면에만 필요한 UI 데이터다.

각 예시는 **그대로 렌더되는 완성품**이어야 한다. 불러오자마자 그림이 안 나오면
문법을 배우는 출발점이 되지 못한다.
"""

from __future__ import annotations

#: 순서가 곧 칩 순서다.
TEMPLATES = [
    {
        "slug": "flowchart",
        "name": "플로우차트",
        "summary": "흐름·분기. 가장 많이 쓴다.",
        "source": """graph TD
  A[시작] --> B{조건을 만족하나?}
  B -->|예| C[처리한다]
  B -->|아니오| D[건너뛴다]
  C --> E[완료]
  D --> E""",
    },
    {
        "slug": "sequence",
        "name": "시퀀스",
        "summary": "주고받는 순서. API 흐름 설명에.",
        # 참여자는 별칭(`participant U as 사용자`)으로 둔다. 한글을 식별자로 바로
        # 쓰면 화살표 문법과 붙어 파서가 헷갈리는 경우가 있다.
        "source": """sequenceDiagram
  participant U as 사용자
  participant B as 브라우저
  participant S as 서버
  U->>B: 마크다운 붙여넣기
  B->>S: POST /api/convert
  S-->>B: HTML + 경고
  B-->>U: 미리보기 표시""",
    },
    {
        "slug": "class",
        "name": "클래스",
        "summary": "구조·관계. 코드 설명에.",
        # 클래스 이름은 코드에서 오는 것이라 영문으로 둔다. 설명(`:` 뒤)은 한글.
        "source": """classDiagram
  class Converter {
    +convert(text) Result
    -render_markdown()
  }
  class Result {
    +str html
    +list warnings
  }
  Converter --> Result : 생성한다""",
    },
    {
        "slug": "gantt",
        "name": "간트",
        "summary": "일정. 프로젝트 회고 글에.",
        "source": """gantt
  title 작업 일정
  dateFormat YYYY-MM-DD
  axisFormat %m/%d
  section 변환기
    마크다운 to HTML  :done, a1, 2026-08-12, 3d
    역방향 되돌리기    :done, a2, after a1, 2d
  section 다이어그램
    편집기 화면       :active, b1, 2026-08-20, 2d
    내보내기          :b2, after b1, 1d""",
    },
    {
        "slug": "er",
        "name": "ER",
        "summary": "테이블·관계. DB 설계 글에.",
        # 관계 라벨은 **반드시 따옴표로 감싼다.** 맨몸으로 두면 한글이 들어간 순간
        # `Parse error on line 2`로 다이어그램이 통째로 안 그려진다 (실제로 밟았다).
        "source": """erDiagram
  CATEGORY ||--o{ POST : "담는다"
  POST ||--o{ COMMENT : "달린다"
  POST {
    int id
    string title
    datetime published_at
  }
  COMMENT {
    int id
    string body
  }""",
    },
]

#: 화면을 처음 열었을 때(저장된 원고가 없을 때) 채워 둘 예시.
DEFAULT_SOURCE = TEMPLATES[0]["source"]
