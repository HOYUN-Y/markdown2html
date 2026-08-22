# PLAN.md — 마크다운 → Blogger HTML 변환기

## 목표

`blog.devprofessional.xyz`(django_blog_Enhanced)에 쓰던 **마크다운 원문을 그대로 붙여넣으면**,
Blogger 글쓰기 화면의 **HTML 보기에 붙여넣어도 안 깨지는 HTML**을 돌려주는 로컬 웹 도구.

## 결정 사항 (2026-08-12)

| 항목 | 결정 | 이유 |
|---|---|---|
| Blogger에 마크다운 직접 입력 | **불가 → HTML 변환** | Blogger는 마크다운 네이티브 미지원. 테마에 marked.js를 심는 우회로는 크롤러·RSS에 마크다운 원문이 노출돼 SEO 손해 |
| 도구 형태 | **로컬 웹 UI** | 붙여넣기 → 변환 → 복사 한 번에 |
| 서버 | **Flask** | 라우트 2개짜리에 Django는 과함 |
| 코드 구조 | `converter/`는 **프레임워크 무관 순수 파이썬** | 나중에 블로그(Django)에 이식할 때 폴더째 복사하면 끝 |
| 코드 하이라이팅 | **Pygments 인라인 스타일** (서버에서 색까지 박음) | Blogger 테마에 CSS 클래스가 없어 클래스 방식은 색이 전혀 안 나옴 |
| 수식 · mermaid | **Blogger 테마에 CDN 스니펫 1회 추가** | 사용자 결정. 변환기는 KaTeX/Mermaid가 알아보는 마크업만 내보냄 |
| 블로그 레포 수정 | **안 함** | 별도 세션에서 다룸 |

## 고정 버전 (블로그 `requirements.txt`와 일치)

- `markdown==3.4.1`
- `pymdown-extensions==9.11`
- Pygments, Flask (블로그에 없는 도구 전용 의존성)

> 블로그가 이 버전을 고정한 이유가 blog `requirements.txt` 주석에 있음 —
> pymdown-extensions를 올리면 markdown도 끌려 올라가 빌드가 깨짐. 여기서도 맞춰 둔다.

## Blogger가 HTML을 망가뜨리는 지점 (이 프로젝트의 실제 난이도)

1. **CSS 클래스 무용지물** → 모든 스타일을 `style=` 속성으로 인라인화
2. **개행 → `<br>` 자동 변환** → 출력 HTML에서 `\n`을 **한 글자도 남기지 않음**
   (코드블록 줄바꿈은 `<br>`로 바꿔 `<pre>` 안에서도 안전하게)
3. **`<pre>` 안 `<`·`&`** → 마크다운 변환 단계에서 이스케이프된 상태 유지
4. **KaTeX/Mermaid 스크립트 부재** → 테마 스니펫 안내 + 감지 시 경고
5. **상대경로 이미지** → 절대 URL로 치환

## 체크리스트

### 1단계 — 기반
- [x] docs 파악, 블로그 파이프라인 조사
- [x] 작업 브랜치 `feat/blogger-converter` 생성
- [x] venv + 고정 버전 설치
- [x] `docs/PLAN.md` 작성
- [x] `requirements.txt` 작성
- [x] `.gitignore` 작성 (`.venv/`, `__pycache__/`, `.DS_Store`)

### 2단계 — 변환 코어 (`converter/`, Flask 무관)
- [x] `converter/pipeline.py` — 블로그와 같은 확장 조합으로 마크다운 → HTML
- [x] `converter/theme.py` — 블로그 **`blog.css`(Slate & Navy)** 조판을 인라인 스타일 표로 이식
      ※ 처음엔 `main.css` `.prose`(포폴 오렌지 테마) 기준으로 만들었다가 갈아엎었다
- [x] `converter/highlight.py` — 블로그가 쓰는 highlight.js `github-dark-dimmed`를
      Pygments 스타일로 옮겨 인라인 하이라이팅
- [x] `converter/blogger.py` — 인라인화 · 개행 제거 · 이미지 절대경로 · 경고 수집
- [x] mermaid 블록 보호 (Pygments를 안 태우고 `<div class="mermaid">`로 직접 출력)
- [x] `converter/snippet.py` — 테마 스니펫 단일 출처

### 3단계 — 웹 UI
- [x] `app.py` — `GET /`, `POST /api/convert`
- [x] `templates/index.html` — 좌: 마크다운 / 우: 미리보기 + HTML 탭
- [x] 블로그 전용 페이지 디자인 따르기 (`b-btn`/`b-mono`/`ed-card` · Slate & Navy)
- [x] 옵션: 줄바꿈 안전 모드, 이미지 base URL, 컨테이너 감싸기 (localStorage 저장)
- [x] 클립보드 복사 버튼, 경고/안내 배너, 테마 스니펫 다이얼로그
- [x] 미리보기 iframe에 테마 스니펫 주입 → Blogger 최종 모습과 일치

### 4단계 — 검증 · 문서
- [x] `tests/test_convert.py` — 26개 통과
- [x] 실제 글(수원시 주차 문제, 21KB)로 변환 후 브라우저 렌더 확인
- [x] 렌더에서 발견한 버그 2건 수정 (`&quot;` 누출 / mermaid 줄바꿈)
- [x] `cli.py` — 파일 단위 변환 (실제 문서 테스트에 필요해 추가)
- [x] `docs/blogger-theme-snippet.md`
- [x] `README.md`, `docs/CHANGELOG.md`, `docs/WORKLOG.md`

### 5단계 — 팔레트 (실제 붙여넣기 후 나온 요구)

사용자의 Blogger 테마가 **검은 배경**이라 라이트 팔레트 글자가 배경에 묻혔다.
인라인 스타일은 미디어쿼리를 담을 수 없어 자동 대응이 불가능 → 선택지로 해결.

- [x] `theme.py`를 `Palette` 구조로 재구성 (모듈 상수 → 함수)
- [x] `dark` 팔레트 — blog.css `html[data-theme="dark"]` 토큰 그대로
- [x] `inherit` 팔레트 — 글자색 미지정, Blogger 테마가 칠함
- [x] 웹 UI 칩 선택 + 미리보기 배경 연동
- [x] `cli.py --palette`
- [x] 테스트 7개 추가 (총 33개)
- [x] 다크·상속 팔레트 렌더 확인

### 6단계 — `<style>` 블록 출력 모드

"글 본문에 CSS를 넣을 수 없다"는 대전제가 **틀렸음**을 확인했다(Blogger는 본문
`<style>`을 정상 처리). 인라인으로는 못 옮기던 blog.css 형제 선택자 규칙을
그대로 쓸 수 있게 됐다.

- [x] `converter/stylesheet.py` — 팔레트별 스코프 CSS
- [x] `highlight.style_defs()` — 강조 색을 스타일시트로
- [x] `blogger.convert(output=...)` 분기
- [x] 웹 UI 칩 + `cli.py --output`
- [x] 스코프 강제 테스트 (`test_every_rule_is_scoped`)
- [x] 적대적 테마 CSS를 주입해 렌더 검증 → 버그 3건 발견·수정
- [x] 손익분기 실측 (원문 약 700자)

### 7단계 — 문서·라벨 정리

- [x] README 재구성 — 옵션 설명이 `쓰는 법` 중간에 끼어 CLI를 밀어내고 있었다.
      `두 가지 선택(팔레트 × 출력 방식)`을 독립 절로 빼고 고르는 법을 붙였다.
- [x] `테마 상속`·`CSS 블록`이 무엇인지 실제 출력 예시로 설명 (물어보게 만들었던 부분)
- [x] 복사 버튼·탭 라벨을 출력 방식에 따라 바꿈 —
      CSS 모드에서 `<style>`이 함께 나가는데 'HTML 복사'는 오해를 준다
- [x] 채우지 못한 README 스크린샷 자리표시자 제거

### 8단계 — 역방향: HTML → 마크다운 (진행 중)

정방향만으로는 한 방향 통행이다. Blogger에만 있는 글을 블로그로 회수하거나,
정방향 변환기가 제대로 동작했는지 **왕복으로 검증**하려면 역방향이 필요하다.

**입력 출처 셋을 모두 다룬다** (사용자 결정) — 난이도가 다르므로 순서대로 간다.

| 출처 | 난이도 | 핵심 |
|---|---|---|
| 우리 변환기 출력 | 낮음 | 구조를 우리가 만들었다. 왕복 테스트가 그대로 명세 |
| Blogger에 올린 글 | 중간 | div 수프·인라인 스타일·`<br>` 문단. **버릴 것을 정하는 규칙**이 절반 |
| 임의의 웹페이지 | 높음 | 본문 추출이라는 별개 문제가 붙는다 |

의존성: `beautifulsoup4` 추가 (사용자 승인). 깨진 HTML·비정상 중첩을 버텨야 한다.

> ⚠️ **`converter/__init__.py`에서 eager import하지 않는다.** 블로그가 이 폴더를
> 복사해 쓰는데, `__init__`이 bs4를 끌어오면 블로그에도 의존성이 강제된다.
> 블로그는 정방향만 쓴다. → `from converter.to_markdown import to_markdown`

- [x] 왕복 가능성 점검 — **정방향이 코드블록 언어를 버린다**는 것을 발견
- [x] 정방향 수정: `<code>`에 `class="language-x"` 복원 (왕복의 전제)
- [x] `converter/to_markdown.py` — 청소 → 블록/인라인 재귀 렌더
- [x] 우리 마커 되돌리기: arithmatex → `$…$`, `.mermaid` → ```` ```mermaid ````,
      `<pre>` 안의 `<br>` → 개행
- [x] 되돌릴 수 없는 것은 **원본 HTML을 그대로 남기고 경고** (셀 병합 표·중첩 표·iframe)
- [x] 이스케이프 — **필요한 만큼만.** 전부 감쌌더니 본문의 `[이미지2 - 월별 단속]`이
      `\[…\]`가 되어 arithmatex가 수식으로 읽는 사고가 났다
- [x] 왕복 테스트 + **안정성 테스트**(`md→html→md→html`이 같은가)
- [x] 중첩 목록 4칸 들여쓰기 · loose/tight 목록 구분
- [x] 실제 글(21KB) 왕복 — 렌더에 영향 없는 공백만 빼면 HTML 동일
- [x] 웹 UI 방향 전환 · `cli.py --reverse`
- [ ] **역방향 화면을 실제로 눌러 확인** — 확장이 localhost에 접근하지 못해
      API·문법·테스트만 검증했다. 화면 상호작용은 아직 사람이 봐야 한다

## 9단계 — Mermaid 다이어그램 도구

탭에 `준비 중`으로만 있던 두 번째 도구를 실제로 만든다. **변환 파이프라인 쪽은 이미
끝나 있다** — ```` ```mermaid ````를 `<div class="mermaid">`로 내보내고(`pipeline.py`),
개행을 `&#10;`로 살리고, 역방향도 되돌린다. 없는 것은 **다이어그램을 그리는 화면**뿐이다.

사용자 결정: **텍스트 편집 + 실시간 미리보기 + 템플릿 갤러리**. 결과물은
```` ```mermaid ```` 코드블록 복사 · SVG · PNG 셋 다. GUI 노드 편집기는 범위 밖
(mermaid가 GUI 편집을 지원하지 않아 캔버스 엔진을 직접 만들어야 한다).

### 설계에서 지킬 것

- **렌더는 브라우저에서.** 배포처가 Vercel Python 함수라 서버에서 mermaid-cli(Node)를
  돌릴 수 없다. 이 화면에는 **API가 없다** — 첫 서버 왕복 없는 도구다.
- **mermaid 버전은 단일 출처.** `snippet.py`에서 CDN 주소·테마를 상수로 빼고 테마
  스니펫과 편집기가 같은 값을 쓴다. 갈라지면 편집기에서 본 그림과 Blogger에 붙여넣은
  그림이 달라진다.
- **템플릿 데이터는 `converter/`에 두지 않는다.** 그 폴더는 블로그가 복사해 가는 변환
  코어다. 편집기 UI 데이터는 `diagrams.py`(루트, `tools.py`와 같은 방식)에 둔다.
- **PNG만 다른 설정으로 다시 렌더한다.** mermaid 기본값은 라벨을 `<foreignObject>`
  (HTML)로 그리는데 canvas 래스터화에서 빈 그림이 나온다. 미리보기는 Blogger와 같은
  기본 설정을 쓰고(정확도), PNG 경로만 `htmlLabels:false`로 재렌더한다.

- [x] `converter/snippet.py` — `MERMAID_SRC`·`MERMAID_THEME` 상수 추출 (출력은 그대로)
- [x] `diagrams.py` — 템플릿 5종(플로우차트·시퀀스·클래스·간트·ER)
      ※ ER은 관계 라벨을 따옴표로 감싸야 한다 — 맨몸으로 두면 파싱 자체가 안 된다
- [x] `app.py` — `GET /mermaid` (API 없음)
- [x] `templates/mermaid.html` — 좌: 소스 / 우: 미리보기, 기존 컴포넌트 재사용
- [x] `public/js/diagram.js` — 디바운스 렌더 · 문법 오류 배너 · 템플릿 · 내보내기
- [x] 내보내기 버그 수정 — SVG 여는 태그의 `width` 중복으로 파일이 통째로 무효였다
- [x] `public/css/app.css` — 이 화면용 섹션
- [x] `tools.py` — mermaid `ready=True`, `url="/mermaid"`
- [x] `tests/test_pages.py` — 라우트·탭 상태·템플릿 데이터 (10개 추가, 총 109개)
- [x] 템플릿 5종·내보내기 경로를 브라우저에서 검증 (mermaid를 CDN에서 직접 불러)
- [ ] **화면을 실제로 눌러 확인** — 이 세션의 브라우저가 로컬 서버에 닿지 못했다
      (`ERR_CONNECTION_REFUSED`). 배포본에서 버튼·복사·다운로드를 사람이 봐야 한다

## 10단계 — draw.io 다이어그램 도구

mermaid는 문법을 글로 써야 한다. **마우스로 상자를 끌어다 놓고 선이 알아서 달라붙는**
그림에는 맞지 않는다 — 사용자가 원한 것이 정확히 그것이다.

편집기를 직접 만들지 않고 **draw.io 공식 임베드**를 쓴다(사용자 결정). 드래그·연결점
스냅·선 경로·되돌리기를 다 만들어도 draw.io보다 못하다. Apache 2.0이고 계정이 필요 없다.
우리가 만드는 것은 바깥 틀과 내보내기뿐이다.

### 설계에서 지킬 것

- **주소와 origin은 한 값에서 나온다**(`drawio.py`). 갈라지면 편집기는 멀쩡히 뜨는데
  postMessage가 전부 버려져 **버튼만 반응이 없다** — 눈으로는 원인을 알 수 없다.
- `dark=0` **고정.** OS가 다크면 편집기가 검게 뜨고 내보낸 그림의 글자가 흰색이 된다 →
  흰 배경 블로그에서 글자만 안 보이는 조용한 실패.
- 내보내기는 **한 번에 하나 + 타임아웃.** 응답이 유실됐을 때 잠금이 안 풀리면 버튼
  다섯이 영원히 죽는다.
- 인라인 조각은 **`<div>`로 감싸고 개행을 없애고 id에 접두사를 붙인다.**
  (감싸지 않으면 그림 속 글자에 마크다운 문법이 먹고, id가 겹치면 한 글의 **두 번째**
  그림에서 화살표가 사라진다.)
- 자동 저장 실패를 **삼키지 않는다.** draw.io XML은 MB 단위가 되어 실제로 한도를 넘는다.

- [x] `drawio.py` — 임베드 주소·파라미터·인라인 상한·감싸개 스타일
- [x] `app.py` — `GET /drawio` (API 없음), `tools.py` — `ready=True`
- [x] `templates/drawio.html` · `public/js/drawio.js` · `app.css` 섹션
- [x] `public/js/shared.js` — 다운로드·버튼 플래시·배너를 두 도구가 함께 쓴다
- [x] 내보내기 4종 — 편집 가능한 SVG · PNG · 인라인 조각 · `.drawio` 원본
- [x] 불러오기 — `.drawio`/`.xml`/편집 가능한 `.svg`(content 속성에서 XML 추출) + 되돌리기
- [x] **역방향이 인라인 SVG를 벗겨내던 문제 수정** (아래)
- [x] 테스트 14개 추가 (총 123개) — 임베드 설정, 화면 id 배선, SVG 왕복
- [x] 조각 변환 로직을 실제 draw.io 형태 SVG로 검증 (node) · 변환기 통과까지 확인
- [ ] **화면을 실제로 눌러 확인** — 이 세션의 브라우저가 로컬 서버에 닿지 못한다.
      배포본에서 편집기 로딩·내보내기 4종·불러오기·되돌리기를 사람이 봐야 한다
- [ ] 인라인 조각을 **Blogger에 실제로 붙여넣어** 살아남는지 확인 (가장 불확실한 지점)

### 곁다리로 고친 것 — 역방향이 그림을 삼키고 있었다

`to_markdown`이 인라인 SVG를 **경고 없이** 텍스트로 뭉갰다. "되돌릴 수 없는 것은 버리지
않고 HTML로 남기고 경고한다"는 원칙이 표에만 적용돼 있고 그림에는 빠져 있었다.
이 도구가 조각을 내보내기 시작하면 바로 밟는 길이라 함께 고쳤다.

- `_in_svg` / `_wraps_svg` 가드 — 청소 규칙이 그림의 `viewBox`·`id`·`<style>`을 지우지
  않게. 감싸개 `<div>`도 style째 남긴다(그 style이 그림의 여백을 들고 있다)
- 직계 자식만 본다 — 글 전체를 감싼 컨테이너 div도 그림을 '품고' 있어서,
  깊이를 안 따지면 본문이 통째로 원본 HTML로 남는다(실제로 밟았다)

## 남은 일

- [ ] **Blogger 실제 화면에 붙여넣어 확인** — 계정 접근이 필요해 아직 못 함.
      무너지는 곳이 있으면 그 지점이 `converter/blogger.py`에 추가할 다음 대응이다.
- [ ] 테마를 바꿀 계획이 있는지에 따라 `dark` / `inherit` 중 기본 선택 결정
- [ ] 테마 스니펫을 실제 Blogger 테마에 넣고 수식·다이어그램 동작 확인
- [ ] `diagram.js`도 `shared.js`를 쓰게 정리 — mermaid 화면을 사람이 확인한 뒤에.
      아직 눌러 보지 못한 파일을 지금 건드리면 확인할 것이 두 배가 된다.
- [ ] draw.io PNG 불러오기(zTXt 청크에 원본이 들어 있다). 지금은 저장만 되고
      다시 열지는 못한다 — 그 PNG는 app.diagrams.net에 끌어다 놓으면 열린다.
- [ ] 다이어그램 테마 — `neutral` 고정이라 검은 배경 Blogger 테마에서는 글자가 어둡다.
      배포본에서 읽히는지 보고, 안 되면 팔레트처럼 고를 수 있게 한다.
- [ ] README 스크린샷 — 헤드리스 Chrome으로는 빈 화면만 찍혀 보류.
      화면에 내용을 채운 상태로 캡처할 방법이 필요하다.

## 앞으로 만들 도구

이 저장소는 도구 하나가 아니라 **글쓰기 도구 모음**으로 간다. 화면 상단 탭은
`tools.py`의 `TOOLS` 목록에서 그려지고, 아직 없는 것도 '준비 중'으로 표시된다 —
계획을 문서 밖에 두지 않기 위한 것이다.

- [x] **마크다운 ⇄ HTML** — Blogger 붙여넣기용 변환과 되돌리기
- [x] **Mermaid 다이어그램** — 그려 보고 마크다운 코드블록으로 가져가기.
      정방향 변환기가 이미 ```` ```mermaid ````를 `<div class="mermaid">`로 내보내므로,
      편집기만 붙이면 글까지 이어진다
- [x] **draw.io 임베드** — 끌어다 놓아 그리고, 글에 넣을 형태로 가져간다

도구를 추가할 때: `tools.py`에 항목 추가(`ready=True`·`url`) → `app.py`에 라우트
(`render_template(..., **nav("<slug>"))`) → 템플릿에서 `{% include "_toolbar.html" %}`.
탭 자체는 손댈 일이 없다.

## 범위 밖 (나중에)

- 블로그 글 상세 화면에 "Blogger용 복사" 버튼 달기 → 블로그 세션에서 논의
- Blogger API 자동 발행
- 티스토리·미디엄 등 다른 플랫폼 프리셋
