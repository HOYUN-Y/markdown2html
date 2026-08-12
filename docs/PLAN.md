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

## 남은 일

- [ ] **Blogger 실제 화면에 붙여넣어 확인** — 계정 접근이 필요해 아직 못 함.
      무너지는 곳이 있으면 그 지점이 `converter/blogger.py`에 추가할 다음 대응이다.
- [ ] 테마를 바꿀 계획이 있는지에 따라 `dark` / `inherit` 중 기본 선택 결정
- [ ] 테마 스니펫을 실제 Blogger 테마에 넣고 수식·다이어그램 동작 확인
- [ ] README 스크린샷 — 헤드리스 Chrome으로는 빈 화면만 찍혀 보류.
      화면에 내용을 채운 상태로 캡처할 방법이 필요하다.

## 범위 밖 (나중에)

- 블로그 글 상세 화면에 "Blogger용 복사" 버튼 달기 → 블로그 세션에서 논의
- Blogger API 자동 발행
- 티스토리·미디엄 등 다른 플랫폼 프리셋
