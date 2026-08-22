"""draw.io 편집기 임베드 설정 — 주소와 파라미터의 단일 출처.

그림을 마우스로 그리는 편집기는 **직접 만들지 않는다.** 드래그·연결점 스냅·선 경로·
되돌리기까지 만들어야 하고, 다 만들어도 draw.io보다 못하다. draw.io는 Apache 2.0이고
공식 임베드 모드를 제공하며 계정도 필요 없다. 우리가 만드는 것은 바깥 틀과 내보내기뿐이다.

통신은 `postMessage`로만 한다(`proto=json`). 그림 내용이 우리 서버로 오지 않고,
이 화면에는 API도 없다 — `/mermaid`와 같은 이유다(브라우저에서 그려야 실제와 같다).

`converter/`에 두지 않은 것은 의도적이다. 그 폴더는 블로그(django_blog_Enhanced)가
복사해 가는 변환 코어이고, 편집기 임베드는 블로그와 아무 상관이 없다.
"""

from __future__ import annotations

from urllib.parse import urlencode

from converter import theme

#: 편집기 출처. **JS가 postMessage의 `event.origin`을 이 값과 대조한다** —
#: 검증을 빼면 아무 페이지나 우리 창에 내보내기 응답을 흉내 내 보낼 수 있다.
#:
#: iframe 주소와 이 값이 갈라지면 **모든 메시지가 조용히 버려진다** — 편집기는 멀쩡히
#: 뜨고 그림도 그려지는데 버튼만 아무 반응이 없다. 한 값에서 주소를 조립하는 이유다.
EMBED_ORIGIN = "https://embed.diagrams.net"

#: 임베드 파라미터. 값의 의미는 draw.io 공식 문서(supported URL parameters) 기준.
EMBED_PARAMS = {
    "embed": "1",       # 임베드 모드. embed.diagrams.net 에서만 쓴다
    "proto": "json",    # JSON postMessage 프로토콜. 이게 없으면 대화가 안 된다
    "spin": "1",        # 로딩 스피너. 느린 회선에서 빈 화면으로 보이지 않게
    "libraries": "1",   # 도형 라이브러리 패널 — 도형을 끌어다 쓰려면 필요하다
    "lang": "ko",       # 편집기 UI 한글
    "ui": "kennedy",    # 기본 UI로 고정. 취향 옵션을 늘리지 않는다
    "grid": "1",        # 격자 — 스냅이 눈에 보여야 맞춰 놓기 쉽다
    "splash": "0",      # 시작 대화상자 끄기. 바로 빈 캔버스에서 시작한다
    "noSaveBtn": "1",   # 저장은 우리 버튼이 한다. 편집기 안에 또 있으면 헷갈린다
    # `dark`를 **고정한다.** OS가 다크면 편집기가 검게 뜨고, 그 상태로 내보낸 그림은
    # 글자가 흰색이 될 수 있다 — 흰 배경 블로그에서 **글자만 안 보이는** 조용한 실패다.
    "dark": "0",
    # `configure`는 쓰지 않는다. 켜면 편집기가 configure 이벤트를 보내고 우리 응답을
    # 기다리며 로딩에서 멈춘다. 얻는 것에 비해 정지 위험이 크다.
}

#: 인라인 조각을 감쌀 `<div>`의 스타일.
#:
#: 앞부분은 mermaid 다이어그램과 **같은 값**을 쓴다(`converter/theme.py`가 출처) —
#: 한 글 안에서 그림마다 여백이 다르면 조판이 어긋나 보인다. 뒤의 두 줄은 큰 그림이
#: 본문 폭을 넘어 잘리지 않게 하는 것으로, 이쪽에만 필요하다.
WRAP_STYLE = theme.MERMAID_STYLE + "max-width:100%;overflow:auto;"

#: 인라인 조각이 이보다 길면 "파일로 저장해 이미지로 올리는 편이 낫다"고 알린다.
#:
#: 조용히 거대한 조각을 내주면 Blogger 편집기가 버벅이거나 붙여넣기가 잘린다.
#: 기준을 8만 자로 잡은 것은 `app.py`의 `MAX_INPUT`(50만 자)에 견줘 본문 한 편에서
#: 그림 하나가 차지하기에 이미 과한 크기이기 때문이다.
MAX_INLINE_CHARS = 80_000


def embed_url() -> str:
    """iframe에 넣을 전체 주소."""
    return "%s/?%s" % (EMBED_ORIGIN, urlencode(EMBED_PARAMS))
