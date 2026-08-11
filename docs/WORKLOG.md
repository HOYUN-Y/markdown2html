# WORKLOG

다른 세션이 읽고 바로 이어받을 수 있도록 적는다.
변경 요약만 필요하면 [`CHANGELOG.md`](./CHANGELOG.md)를 본다.

---

## 2026-08-12 — 첫 구현 (브랜치 `feat/blogger-converter`)

### 무엇을 왜 했나

블로그(`blog.devprofessional.xyz`, 레포 `django_blog_Enhanced`)에 쓰던 마크다운 원문을
Blogger에도 올리고 싶은데, **Blogger는 마크다운을 지원하지 않는다**. 그대로 붙여넣으면
`#`이 글자로 찍힌다. 그래서 HTML로 변환하는 도구를 만들었다.

우회로도 검토했다. Blogger 테마에 `marked.js`를 심으면 마크다운 원문을 그대로 붙여넣을 수
있지만, **크롤러·RSS 피드에는 마크다운 원문이 그대로 노출**된다(SEO 손해). 브라우저 확장이나
StackEdit 퍼블리시는 유지보수가 끊긴 서드파티에 블로그 권한을 넘겨야 한다.
→ **정적 HTML 변환**이 유일하게 SEO·피드·아카이빙이 안전한 선택이었다.

### 사전 조사에서 확인한 것 (중요)

블로그 레포를 뜯어서 확인한 사실들이다. 이걸 모르면 결과물이 블로그와 다르게 나온다.

| 확인한 것 | 어디서 | 함의 |
|---|---|---|
| 마크다운 설정 | `posts/views.py:129` | `extra`·`codehilite`·`toc`·`fenced_code`·`pymdownx.arithmatex(generic)` |
| 버전 고정 이유 | `requirements.txt` 주석 | `markdown==3.4.1` + `pymdown-extensions==9.11`. 올리면 블로그 빌드가 깨짐 |
| **실제 코드 색은 서버가 아니라 브라우저가 칠함** | `templates/blog/detail.html:234` | `hljs.highlightElement()`가 codehilite 결과를 덮어씀 |
| 하이라이트 테마 | `static/css/blog.css:435` | highlight.js **github-dark-dimmed** on `--code-bg: #11162A` |
| **본문 조판은 `main.css`가 아니라 `blog.css`** | `blog.css:403~443` | 블로그 서브도메인은 'Slate & Navy'(강조색 남색 `#00215D`). `main.css`의 `.prose`는 포트폴리오용 오렌지 테마다 |
| mermaid 처리 | `detail.html:226` | `code.language-mermaid`를 런타임에 `div.mermaid`로 교체 |
| 수식 감지 | `posts/views.py:168` | `class="arithmatex"` 존재 여부로 KaTeX 로드를 결정 |

> ⚠️ **처음에 `main.css`의 `.prose`를 기준으로 만들었다가 갈아엎었다.** 그건 포트폴리오
> 사이트 스타일이다. 블로그 본문 스타일을 건드릴 일이 생기면 `blog.css`의
> `body.blog .article-body` 블록을 봐야 한다.

### 설계 결정과 근거

1. **`converter/`는 프레임워크를 import하지 않는다.**
   나중에 블로그(Django)에 붙일 때 폴더째 복사하고 뷰에서 `convert()`만 부르면 되게 하려는
   의도적 제약이다. Flask는 `app.py`에만 있다.

2. **codehilite를 뺐다.** codehilite는 CSS 클래스를 뱉는데 Blogger에는 그 CSS를 넣을 데가
   없다. 대신 변환 후 단계에서 Pygments로 직접 칠하고 `noclasses=True`로 색을 span에 박는다.
   블로그도 실제 색은 브라우저의 highlight.js가 칠하므로, 뒤 단계에서 칠하는 쪽이 오히려
   블로그 동작에 가깝다.

3. **개행을 한 글자도 남기지 않는다.** Blogger의 '엔터 = 줄바꿈' 설정이 켜져 있으면 붙여넣은
   HTML의 개행이 전부 `<br>`이 된다. 설정을 끄라고 안내하는 것보다, 설정과 무관하게 같은
   결과가 나오게 만드는 편이 안전하다.
   - 코드블록 줄바꿈 → `<br>` (`<pre>` 안에서 정상 렌더)
   - 다이어그램 줄바꿈 → `&#10;` (아래 함정 참고)
   - 그 외 → 공백 하나로 접음

4. **인라인화는 `html.parser`로 한다.** BeautifulSoup을 새로 들이지 않았다. 입력이 우리가
   만든 HTML이라 파서 견고성이 크게 필요하지 않다. `convert_charrefs=False`가 **필수**다 —
   기본값(True)이면 `&lt;`가 문자로 풀려 코드블록의 `<`가 다시 태그로 해석된다.

### 실제 문서로 테스트하다 잡은 버그 2개

테스트는 26개 전부 통과했는데도, 실제 글(수원시 주차 문제 분석, 21KB)을 브라우저에 띄우니
바로 두 개가 보였다. **단위 테스트만으로는 못 잡는 종류였다.**

1. **코드블록에 `&quot;`가 글자 그대로 찍혔다.**
   Python-Markdown은 코드블록에서 `"`도 `&quot;`로 바꾼다. 되돌리는 코드에 `&lt;`·`&gt;`·
   `&amp;`만 넣고 `"`를 빠뜨렸다. → `html.unescape`로 교체(한 번만 훑으므로 원문의
   `&lt;`는 그대로 보존된다).

2. **mermaid가 'Syntax error in text'.**
   개행 제거 과정에서 다이어그램 소스가 한 줄로 뭉쳤다. Mermaid는 textContent를 줄 단위로
   파싱한다. `<br>`은 답이 아니다 — textContent에 아무것도 기여하지 않아 줄이 그대로 붙는다.
   → `&#10;`(개행 실체 참조). HTML 소스에는 개행 문자로 존재하지 않아 Blogger의 줄바꿈
   변환에 안 걸리고, 브라우저가 DOM 텍스트로 만들 때는 진짜 개행이 된다.

> **교훈**: 이 프로젝트는 "실제 글을 넣고 눈으로 본다"를 건너뛰면 안 된다.
> 변환 결과가 문법적으로 멀쩡해도 렌더 결과가 깨질 수 있다.

### 검증 방법 (다음 세션이 그대로 쓰면 된다)

```bash
.venv/bin/python -m unittest discover -s tests -v      # 26개
.venv/bin/python cli.py 글.md --preview                # 눈으로 확인할 HTML 생성
```

브라우저 확인은 **헤드리스 Chrome**으로 했다. Claude in Chrome 확장은 `127.0.0.1`/`localhost`
사이트 권한이 없어 요청이 서버까지 오지 않는다(Flask 로그에 아무것도 안 남는다).

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --disable-gpu --hide-scrollbars \
  --window-size=900,1000 --virtual-time-budget=9000 \
  --screenshot=out.png "file:///경로/글.preview.html"
```

### 남은 일 · 주의점

- **블로그 쪽 적용은 손대지 않았다.** 사용자가 "그쪽 세션과 나중에 공유해서 고민하겠다"고
  했다. `django_blog_Enhanced`는 한 줄도 수정하지 않았다.
- 블로그 글 상세 화면에 'Blogger용 복사' 버튼을 다는 건 범위 밖으로 뒀다.
- Blogger 실제 화면에서의 최종 확인은 **아직 못 했다.** 계정 접근이 필요하다.
  붙여넣은 뒤 무너지는 곳이 있으면 그 지점이 `converter/blogger.py`에 추가할 다음 대응이다.
- `$$...$$`를 문장 중간에 쓰면 arithmatex가 span을 이중으로 감싼다. 블로그도 같은 동작이라
  건드리지 않았다. 고치려면 블로그와 함께 고쳐야 한다.
