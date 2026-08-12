# markdown2html

마크다운 원문을 **Blogger 글쓰기 화면에 그대로 붙여넣을 수 있는 HTML**로 바꾸는 로컬 도구.

결과물은 [`blog.devprofessional.xyz`](https://blog.devprofessional.xyz)의 본문 조판을
그대로 따른다. 같은 글이 두 곳에서 같은 모양으로 보인다.

## 왜 만들었나

블로그([`django_blog_Enhanced`](../django_blog_Enhanced))는 마크다운으로 글을 쓴다.
그런데 **Blogger는 마크다운을 지원하지 않는다.** 그대로 붙여넣으면 `#`이 글자로 찍히고
코드블록도 서식 없이 나온다.

우회로를 검토했지만 전부 대가가 컸다.

| 방법 | 대가 |
|---|---|
| 테마에 `marked.js`를 심어 브라우저에서 변환 | 크롤러·RSS 피드에 **마크다운 원문이 그대로 노출**(SEO 손해). JS가 죽으면 글이 깨짐 |
| 브라우저 확장(mdblogger 등) | 유지보수 끊긴 서드파티 의존 |
| StackEdit에서 Blogger로 퍼블리시 | 외부 서비스에 블로그 계정 권한을 넘겨야 함 |

→ **정적 HTML 변환**만이 SEO·피드·아카이빙이 모두 안전하다.

## 쓰는 법

### 웹 UI

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python app.py          # → http://127.0.0.1:5001
```

왼쪽에 마크다운을 붙여넣으면 오른쪽에 결과가 나온다. **HTML 복사**를 누르고
Blogger 글쓰기 화면의 **HTML 보기**에 붙여넣으면 끝이다.

- **미리보기** 탭은 테마 스니펫을 넣은 iframe이라, **Blogger에서 보일 모습과 같다.**
  선택한 팔레트에 맞춰 미리보기 배경도 바뀐다.
- **Blogger 테마 배경** · **출력 방식** — 아래 [두 가지 선택](#두-가지-선택--무슨-색으로-어디에)
  참고. **붙여넣기 전에 이 둘을 먼저 맞춘다.**
- **이미지 기준 URL** — 마크다운에 `/media/a.png` 같은 상대경로가 있을 때 채운다.
  비워두면 상대경로가 발견될 때 경고가 뜬다.
- **줄바꿈 안전 모드**(기본 켬) — 아래 [Blogger 대응](#blogger가-html을-망가뜨리는-지점) 참고.

### CLI

```bash
.venv/bin/python cli.py 글.md                        # → 글.blogger.html (붙여넣기용)
.venv/bin/python cli.py 글.md --preview              # → 글.preview.html 도 함께 (브라우저 확인용)
.venv/bin/python cli.py 글.md --palette dark         # 검은 배경 Blogger 테마용
.venv/bin/python cli.py 글.md --output css           # <style> 블록 방식
.venv/bin/python cli.py 글.md --base-url https://blog.devprofessional.xyz
```

### 수식·다이어그램을 쓴다면

코드블록·표·인용구·이미지는 **스타일이 딸려 나가므로 그냥 나온다.** 스크립트가 필요한 건
수식(KaTeX)과 mermaid뿐이고, Blogger 테마에 **한 번만** 넣으면 된다.
→ [`docs/blogger-theme-snippet.md`](docs/blogger-theme-snippet.md) (또는 화면의 **테마 스니펫** 버튼)

## 두 가지 선택 — 무슨 색으로, 어디에

붙여넣기 전에 고르는 옵션이 둘이다. **서로 독립이라 자유롭게 조합된다.**

| 축 | 정하는 것 | 값 |
|---|---|---|
| **팔레트** | 글자를 **무슨 색**으로 칠할지 | `light` · `dark` · `inherit` |
| **출력 방식** | 그 색을 **어디에 적을지** | `inline` · `css` |

### 팔레트 — 무슨 색

Blogger 테마의 배경 밝기에 맞춘다. **자동 대응은 불가능하다** — `prefers-color-scheme`은
OS/브라우저 설정을 따르지 Blogger 테마 밝기를 따르지 않는다. 테마가 OS와 무관하게 늘
검은색이면 밝은 OS에서 여전히 라이트 색이 나온다. (출력 방식을 `css`로 바꿔도 마찬가지다.)

| 팔레트 | 언제 | 대가 |
|---|---|---|
| `light` (기본) | 흰색·밝은 배경 테마 | 검은 테마에 쓰면 **본문이 배경에 묻힌다** |
| `dark` | 검은·어두운 배경 테마 | 나중에 테마를 밝게 바꾸면 **기존 글이 전부 안 읽힌다** (색이 HTML에 박제돼 있다) |
| `inherit` | 테마를 바꿀 수도 있을 때 | 블로그와 **똑같은 색은 아니다** |

`light`/`dark`는 블로그의 라이트·다크 모드 토큰을 **그대로** 쓴다.

**`inherit`은 색을 아예 안 적는 것이다.** 같은 문단에 대해 실제로 나가는 규칙:

```css
/* light   */  p { color:#1A1F2B }   ← 색을 박음
/* dark    */  p { color:#D7DEEC }   ← 색을 박음
/* inherit */  p { }                  ← 비어 있음
```

CSS에서 색을 지정하지 않으면 부모에게서 물려받고, 여기서 부모는 Blogger 테마다. 그래서
테마를 바꿔도 알아서 따라간다. 대신 링크가 파란색을 잃고 **본문색 + 밑줄**로만 구분된다
(색을 정할 수 없으니 `currentColor`를 쓴다). 색이 꼭 필요한 것 — 코드블록, 인용구 배경,
표 선 — 은 상속 모드에서도 유지하되, 밝기 어느 쪽에서도 보이는 반투명 회색을 쓴다.

코드블록은 팔레트와 무관하게 늘 어둡다 — 블로그도 두 테마 모두 어둡게 둔다(`blog.css:435`).

### 출력 방식 — 어디에

Blogger는 글 본문의 `<style>` 태그를 정상 처리한다(`<html>`/`<head>`/`<body>`만 넣지
않으면 된다). 그래서 같은 스타일을 두 자리에 둘 수 있다.

```html
<!-- inline — 태그마다 반복 -->
<p style="color:#D7DEEC;margin:0 0 21px;">첫 문단.</p>
<p style="color:#D7DEEC;margin:0 0 21px;">둘째 문단.</p>

<!-- css — 앞에 한 번, 본문은 깨끗 -->
<style>.md2b.md2b-dark p{color:#D7DEEC}…</style>
<div class="md2b md2b-dark"><p>첫 문단.</p><p>둘째 문단.</p></div>
```

| | `inline` (기본) | `css` |
|---|---|---|
| **조판 정확도** | blog.css의 `> * + *`·`li + li`를 **px로 근사** | **그대로 옮김** |
| 길이 | 짧은 글에 유리 | 원문 **700자 넘으면** 유리 |
| RSS 피드 | 서식 일부 유지 | **`<style>`이 제거돼 서식 없음** |
| 편집기 가독성 | `style="…"` 범벅 | 사람이 읽고 손볼 수 있음 |
| AMP | 가능 | **불가** (AMP는 본문 `<style>` 금지) |
| Compose 모드 전환 | 비교적 안전 | 깨질 수 있음 — HTML 보기에서만 다룰 것 |

`css`를 만든 이유는 길이가 아니라 **첫 줄**이다. 인라인 `style=` 속성으로는
"앞 요소로부터 1.2em 띄운다" 같은 **관계형 규칙을 표현할 수 없어** px로 어림잡아야 한다.
`css` 모드는 블로그 규칙을 글자 그대로 옮겨 여백이 정확히 같아진다.

길이 손익분기는 실측 **원문 약 700자**다. 스타일시트가 6.6천 자 고정 비용이라
짧은 글은 오히려 길어진다.

| 원문 | `inline` | `css` |
|---|---|---|
| 264자 | 2,609 | 6,931 |
| 880자 | 8,192 | **7,838** |
| 실제 글 21KB | 43,637 | **22,558** |

`css` 모드의 모든 규칙은 `.md2b.md2b-<팔레트>` 아래로 스코프된다. 글 목록·홈처럼 여러
글이 한 페이지에 뜰 때 테마나 다른 글을 건드리지 않고, 팔레트가 다른 글끼리도 충돌하지
않는다. 클래스를 겹쳐 특이도를 올려 테마 규칙에 지지 않는다.

> `!important`로 본문 여백을 강제하는 테마는 **두 방식 모두** 이길 수 없다.

### 고르는 법

- 테마를 바꿀 생각이 없다 → 밝기에 맞는 `light`/`dark`. 블로그와 색이 일치한다.
- 테마를 바꿀 여지가 있다 → `inherit`. 나중에 글을 다시 변환할 일이 없다.
- RSS 구독자가 있다 / AMP를 쓴다 → `inline`.
- 긴 글에서 블로그와 여백까지 똑같이 맞추고 싶다 → `css`.

## Blogger가 HTML을 망가뜨리는 지점

이 도구가 실제로 하는 일은 "마크다운 → HTML"이 아니라 **"블로그와 같은 HTML → Blogger가
안 망가뜨리는 HTML"** 이다. 막고 있는 것들:

| 문제 | 대응 |
|---|---|
| 테마 CSS는 손댈 수 없고 글마다 스타일을 들고 가야 함 | 스타일을 `style=` 속성에 인라인화, 또는 `<style>` 블록 + 스코프 클래스 |
| `prefers-color-scheme`은 OS를 따르지 테마 밝기를 안 따라 자동 대응 불가 | 팔레트 3종(`light`/`dark`/`inherit`)에서 선택 |
| `<style>` 안의 개행도 `<br>`로 바뀌어 CSS가 깨짐 | CSS도 개행 없이 한 줄로 출력 |
| 테마의 `p { color: … }` 한 줄이 본문 색을 통째로 덮음 (상속은 직접 지정에 무조건 짐) | 글자를 담는 요소마다 색·글꼴을 명시 |
| '엔터 = 줄바꿈' 설정이 개행을 전부 `<br>`로 바꿈 | 출력에 **개행 문자를 한 글자도 남기지 않음**. 코드블록은 `<br>`, 다이어그램은 `&#10;` |
| `<pre>` 안의 `<`·`&`·`"`가 태그로 해석됨 | 이스케이프를 유지한 채 Pygments 처리 |
| 상대경로 이미지가 Blogger 도메인 기준이 됨 | 기준 URL로 절대화, 없으면 경고 |
| 코드에 색이 안 나옴 | Pygments로 **서버에서** 칠함 (인라인은 span의 style, `css` 모드는 스타일시트) |

## 구조

```
converter/          변환 코어 — Flask/Django를 import하지 않는다
  pipeline.py         마크다운 → HTML (블로그와 같은 확장 조합)
  theme.py            팔레트 3종 + 인라인 스타일 표
  stylesheet.py       <style> 블록 모드용 스코프 CSS
  highlight.py        github-dark-dimmed 팔레트 → Pygments 하이라이팅 (인라인/클래스)
  blogger.py          스타일 적용·개행 제거·이미지 절대경로·경고 수집
  snippet.py          Blogger 테마용 KaTeX/Mermaid 스니펫 (단일 출처)
app.py              Flask 웹 UI (라우트 2개)
cli.py              파일 단위 변환
templates/ static/  화면 — 블로그 전용 페이지의 디자인 토큰을 따름
tests/              unittest 43개
docs/               PLAN · CHANGELOG · WORKLOG · 테마 스니펫
```

**`converter/`가 프레임워크를 모르는 것은 의도적이다.** 나중에 블로그(Django)에 붙일 때
이 폴더만 복사하고 뷰에서 `convert()`를 부르면 된다. Flask 코드는 버리면 된다.

```python
from converter import convert

result = convert(
    markdown_text,
    image_base_url="https://blog.devprofessional.xyz",
    palette="dark",     # light · dark · inherit
    output="css",       # inline · css
)
result.html      # 붙여넣을 HTML
result.warnings  # 손봐야 할 것 (상대경로 이미지, 모르는 코드 언어 …)
result.notes     # 테마 스니펫이 필요하다는 안내
result.stats     # 글자수·코드블록·이미지·다이어그램·남은 개행 수
```

## 블로그와 맞춰 둔 것

결과물이 블로그와 같은 모양이려면 아래가 어긋나면 안 된다.
블로그 쪽이 바뀌면 **여기도 함께 바꿔야 한다**(자동 동기화는 없다).

| 항목 | 블로그 출처 | 이 저장소 |
|---|---|---|
| 마크다운 확장 | `posts/views.py:129` | `converter/pipeline.py` |
| 라이브러리 버전 | `requirements.txt` | `requirements.txt` |
| 본문 조판 | `static/css/blog.css` (`body.blog .article-body`) | `converter/theme.py` · `converter/stylesheet.py` |
| 다크 모드 색 | `blog.css` (`html[data-theme="dark"] body.blog`) | `converter/theme.py`의 `DARK` |
| 코드 색 | highlight.js `github-dark-dimmed` (`blog.css:435`) | `converter/highlight.py` |
| KaTeX·Mermaid 설정 | `templates/blog/detail.html` | `converter/snippet.py` |

> 본문 스타일은 `main.css`의 `.prose`가 **아니다.** 그건 포트폴리오 사이트용
> 오렌지 테마이고, 블로그 서브도메인은 `blog.css`의 'Slate & Navy'(강조색 남색)를 쓴다.

## 테스트

```bash
.venv/bin/python -m unittest discover -s tests -v
```

단위 테스트만으로는 부족하다. 기능을 바꿨으면 **실제 글을 넣고 눈으로 확인한다** —
문법적으로 멀쩡한 HTML이 렌더에서만 깨지는 버그를 지금까지 다섯 번 잡았고,
**전부 테스트가 전부 통과하는 상태에서 나왔다** ([`docs/WORKLOG.md`](docs/WORKLOG.md) 참고).

```bash
.venv/bin/python cli.py 글.md --preview   # 생성된 .preview.html을 브라우저로 연다
```

`css` 모드를 손볼 때는 **적대적인 테마 CSS를 끼워 렌더해 본다.** 우리 규칙이 테마에
지는지는 그렇게 해야만 드러난다. 이 방법으로 세 건을 잡았다.

```html
<style>.post-body p{margin:0} p,li,td{color:#888;font-family:serif}</style>
```

## 알려진 제약

- `$$...$$`를 **문장 안에** 쓰면 arithmatex가 span을 이중으로 감싼다.
  블로그 파이프라인과 동일한 동작이라 그대로 뒀다 — 블록 수식은 `$$`를 줄 하나로 띄워 쓴다.
- Blogger 테마 CSS가 `!important`로 본문 여백을 강제하면 **두 출력 방식 모두** 진다.
- 팔레트는 자동으로 못 고른다. `prefers-color-scheme`은 OS 설정을 따르지 Blogger 테마
  밝기를 따르지 않는다.
- Blogger 실제 화면에서의 최종 확인은 아직 못 했다(계정 접근 필요).
