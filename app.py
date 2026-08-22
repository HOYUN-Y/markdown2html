"""로컬 웹 UI — 마크다운을 붙여넣으면 Blogger용 HTML을 돌려준다.

Flask는 이 파일에만 있다. 변환 로직은 `converter/` 패키지에 있고 프레임워크를
전혀 모른다 — 나중에 블로그(Django)에 붙일 때 그 폴더만 옮기면 되게 하려는 것이다.

    python app.py   →  http://127.0.0.1:5001
"""

from flask import Flask, jsonify, redirect, render_template, request, url_for

import auth
import diagrams
import drawio
from converter import convert
from converter.snippet import MERMAID_SRC, MERMAID_THEME, THEME_SNIPPET
from tools import nav

# static_folder를 `public`으로 둔 것은 **Vercel 배포 때문이다.**
# Vercel은 `public/**`을 CDN에서 직접 내보내고 함수까지 오지 않게 한다
# (공식 문서: Flask의 static_folder를 쓰지 말고 public/을 쓰라고 못 박고 있다).
# static_url_path=""로 두면 로컬에서도 같은 주소(`/css/app.css`)로 열리므로,
# 템플릿의 url_for('static', …)를 그대로 쓸 수 있고 두 환경이 갈라지지 않는다.
app = Flask(__name__, static_folder="public", static_url_path="")

# 로그인. 화면마다 데코레이터를 붙이지 않고 **모든 요청 앞에** 세운다 —
# 도구를 새로 만들 때 빠뜨리면 그 화면만 공개되기 때문이다(auth.guard 주석 참고).
app.secret_key = auth.secret_key()
app.permanent_session_lifetime = auth.SESSION_LIFETIME
app.before_request(auth.guard)

# 쿠키를 조인다. Secure는 **배포본에서만** 켠다 — 로컬은 http라 켜면 브라우저가
# 쿠키를 아예 안 보내서 로그인이 안 된다(원인이 화면에 안 나와 한참 헤맨다).
app.config["SESSION_COOKIE_SECURE"] = auth.is_hosted()
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True


@app.context_processor
def auth_state():
    """템플릿이 로그아웃 버튼을 보일지 정하는 데 쓴다."""
    return {"auth_on": auth.is_enabled(), "logged_in": auth.is_logged_in()}

#: 붙여넣기 사고로 브라우저가 멈추는 걸 막는 상한.
#:
#: 글자 수로 세지만 **바이트로도 안전해야 한다** — Vercel 함수의 요청 본문 한도가
#: 4.5MB인데, 한글은 UTF-8에서 한 자에 3바이트라 50만 자면 약 1.5MB다. 넉넉히 들어간다.
#: (예전 200만 자는 한글로 6MB라 Vercel이 413으로 막았을 것이다.)
#: 실측: 50만 자 변환에 정방향 1초·역방향 3초 — 기본 타임아웃 안에 들어온다.
MAX_INPUT = 500_000


@app.route("/login", methods=["GET", "POST"])
def login():
    """비밀번호 하나로 들어온다. 쓰는 사람이 한 명이라 계정 테이블이 없다."""
    if not auth.is_enabled():
        return redirect(url_for("index"))
    if auth.is_logged_in():
        return redirect(url_for("index"))

    error = ""
    if request.method == "POST":
        if auth.check(request.form.get("password") or ""):
            auth.log_in()
            # 로그인 전에 열려던 화면으로 돌려보낸다. **바깥 주소로는 보내지 않는다** —
            # 열린 리다이렉트가 되면 이 화면이 피싱 발판이 된다.
            target = request.form.get("next") or ""
            return redirect(target if target.startswith("/") and not target.startswith("//")
                            else url_for("index"))
        error = "비밀번호가 맞지 않습니다."

    return render_template("login.html", error=error,
                           next=request.args.get("next", "")), (401 if error else 200)


@app.post("/logout")
def logout():
    auth.log_out()
    return redirect(url_for("login"))


@app.get("/")
def index():
    return render_template("index.html", theme_snippet=THEME_SNIPPET, **nav("convert"))


@app.get("/mermaid")
def mermaid():
    """다이어그램 편집기.

    **API가 없는 첫 화면이다.** mermaid는 브라우저에서 그리는 라이브러리이고
    (배포처가 Vercel의 Python 함수라 서버에서 Node를 돌릴 수도 없다), 그렇게 그려야
    Blogger에 붙여넣었을 때와 같은 그림이 나온다. 서버는 화면과 템플릿 목록만 준다.
    """
    return render_template(
        "mermaid.html",
        templates=diagrams.TEMPLATES,
        default_source=diagrams.DEFAULT_SOURCE,
        mermaid_src=MERMAID_SRC,
        mermaid_theme=MERMAID_THEME,
        **nav("mermaid"),
    )


@app.get("/drawio")
def drawio_page():
    """draw.io 편집기.

    `/mermaid`와 같이 **API가 없다.** 편집기는 draw.io 공식 임베드(iframe)이고
    그림은 브라우저 안에서만 오간다 — 서버는 화면과 임베드 주소만 준다.
    함수 이름을 `drawio`로 하지 않은 것은 같은 이름의 모듈을 가리기 때문이다.
    """
    return render_template(
        "drawio.html",
        embed_url=drawio.embed_url(),
        embed_origin=drawio.EMBED_ORIGIN,
        max_inline_chars=drawio.MAX_INLINE_CHARS,
        wrap_style=drawio.WRAP_STYLE,
        **nav("drawio"),
    )


@app.post("/api/convert")
def api_convert():
    payload = request.get_json(silent=True) or {}
    text = payload.get("markdown") or ""
    if len(text) > MAX_INPUT:
        return jsonify(error=f"입력이 너무 깁니다 ({len(text):,}자). {MAX_INPUT:,}자까지 처리합니다."), 413

    try:
        result = convert(
            text,
            image_base_url=payload.get("image_base_url") or "",
            safe_linebreaks=bool(payload.get("safe_linebreaks", True)),
            wrap=bool(payload.get("wrap", True)),
            palette=payload.get("palette") or "light",
            output=payload.get("output") or "inline",
        )
    except Exception as exc:  # 변환 실패를 조용히 삼키지 않는다 — 화면에 그대로 띄운다.
        app.logger.exception("변환 실패")
        return jsonify(error=f"변환 중 오류가 발생했습니다: {exc}"), 500

    return jsonify(
        html=result.html,
        warnings=result.warnings,
        notes=result.notes,
        stats=result.stats,
    )


@app.post("/api/to-markdown")
def api_to_markdown():
    """역방향 — HTML을 마크다운으로 되돌린다.

    bs4는 이 경로에서만 필요하다. 위쪽에서 import하면 정방향만 쓰는 쪽
    (블로그가 converter/를 복사해 간다)에도 의존성이 강제된다.
    """
    from converter.to_markdown import to_markdown

    payload = request.get_json(silent=True) or {}
    html = payload.get("html") or ""
    if len(html) > MAX_INPUT:
        return jsonify(error=f"입력이 너무 깁니다 ({len(html):,}자). {MAX_INPUT:,}자까지 처리합니다."), 413

    try:
        result = to_markdown(html, base_url=payload.get("base_url") or "")
    except Exception as exc:
        app.logger.exception("역변환 실패")
        return jsonify(error=f"변환 중 오류가 발생했습니다: {exc}"), 500

    return jsonify(
        text=result.markdown,
        warnings=result.warnings,
        notes=result.notes,
        stats=result.stats,
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
