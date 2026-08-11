# markdown2html

마크다운 원문을 **Blogger 글쓰기 화면에 그대로 붙여넣을 수 있는 HTML**로 바꾸는 로컬 도구.

결과물은 [`blog.devprofessional.xyz`](https://blog.devprofessional.xyz)의 본문 조판을
그대로 따른다. 같은 글이 두 곳에서 같은 모양으로 보인다.

<!-- 스크린샷 자리 — 화면을 바꾸면 갱신할 것 -->

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
- **이미지 기준 URL** — 마크다운에 `/media/a.png` 같은 상대경로가 있을 때 채운다.
  비워두면 상대경로가 발견될 때 경고가 뜬다.
- **줄바꿈 안전 모드**(기본 켬) — 아래 [Blogger 대응](#blogger가-html을-망가뜨리는-지점) 참고.

### CLI

```bash
.venv/bin/python cli.py 글.md                        # → 글.blogger.html (붙여넣기용)
.venv/bin/python cli.py 글.md --preview              # → 글.preview.html 도 함께 (브라우저 확인용)
.venv/bin/python cli.py 글.md --base-url https://blog.devprofessional.xyz
```

### 수식·다이어그램을 쓴다면

코드블록·표·인용구·이미지는 **스타일이 인라인이라 그냥 나온다.** 스크립트가 필요한 건
수식(KaTeX)과 mermaid뿐이고, Blogger 테마에 **한 번만** 넣으면 된다.
→ [`docs/blogger-theme-snippet.md`](docs/blogger-theme-snippet.md) (또는 화면의 **테마 스니펫** 버튼)

## Blogger가 HTML을 망가뜨리는 지점

이 도구가 실제로 하는 일은 "마크다운 → HTML"이 아니라 **"블로그와 같은 HTML → Blogger가
안 망가뜨리는 HTML"** 이다. 막고 있는 것들:

| 문제 | 대응 |
|---|---|
| 글 본문에 CSS를 넣을 수 없어 클래스가 무용지물 | 모든 스타일을 `style=` 속성으로 인라인화 |
| '엔터 = 줄바꿈' 설정이 개행을 전부 `<br>`로 바꿈 | 출력에 **개행 문자를 한 글자도 남기지 않음**. 코드블록은 `<br>`, 다이어그램은 `&#10;` |
| `<pre>` 안의 `<`·`&`·`"`가 태그로 해석됨 | 이스케이프를 유지한 채 Pygments 처리 |
| 상대경로 이미지가 Blogger 도메인 기준이 됨 | 기준 URL로 절대화, 없으면 경고 |
| 코드에 색이 안 나옴 | Pygments로 **서버에서** 칠하고 색을 span에 인라인으로 박음 |

## 구조

```
converter/          변환 코어 — Flask/Django를 import하지 않는다
  pipeline.py         마크다운 → HTML (블로그와 같은 확장 조합)
  theme.py            블로그 blog.css 본문 조판 → 인라인 스타일 표
  highlight.py        github-dark-dimmed 팔레트 → Pygments 인라인 하이라이팅
  blogger.py          인라인화·개행 제거·이미지 절대경로·경고 수집
  snippet.py          Blogger 테마용 KaTeX/Mermaid 스니펫 (단일 출처)
app.py              Flask 웹 UI (라우트 2개)
cli.py              파일 단위 변환
templates/ static/  화면 — 블로그 전용 페이지의 디자인 토큰을 따름
tests/              unittest 26개
docs/               PLAN · CHANGELOG · WORKLOG · 테마 스니펫
```

**`converter/`가 프레임워크를 모르는 것은 의도적이다.** 나중에 블로그(Django)에 붙일 때
이 폴더만 복사하고 뷰에서 `convert()`를 부르면 된다. Flask 코드는 버리면 된다.

```python
from converter import convert

result = convert(markdown_text, image_base_url="https://blog.devprofessional.xyz")
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
| 본문 조판 | `static/css/blog.css` (`body.blog .article-body`) | `converter/theme.py` |
| 코드 색 | highlight.js `github-dark-dimmed` (`blog.css:435`) | `converter/highlight.py` |
| KaTeX·Mermaid 설정 | `templates/blog/detail.html` | `converter/snippet.py` |

> 본문 스타일은 `main.css`의 `.prose`가 **아니다.** 그건 포트폴리오 사이트용
> 오렌지 테마이고, 블로그 서브도메인은 `blog.css`의 'Slate & Navy'(강조색 남색)를 쓴다.

## 테스트

```bash
.venv/bin/python -m unittest discover -s tests -v
```

단위 테스트만으로는 부족하다. 기능을 바꿨으면 **실제 글을 넣고 눈으로 확인한다** —
문법적으로 멀쩡한 HTML이 렌더에서 깨지는 버그를 두 번 잡았다
([`docs/WORKLOG.md`](docs/WORKLOG.md) 참고).

```bash
.venv/bin/python cli.py 글.md --preview   # 생성된 .preview.html을 브라우저로 연다
```

## 알려진 제약

- `$$...$$`를 **문장 안에** 쓰면 arithmatex가 span을 이중으로 감싼다.
  블로그 파이프라인과 동일한 동작이라 그대로 뒀다 — 블록 수식은 `$$`를 줄 하나로 띄워 쓴다.
- Blogger 테마 CSS가 `!important`로 본문 여백을 강제하면 인라인 스타일도 진다.
- Blogger 실제 화면에서의 최종 확인은 아직 못 했다(계정 접근 필요).
