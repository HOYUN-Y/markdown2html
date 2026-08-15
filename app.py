"""로컬 웹 UI — 마크다운을 붙여넣으면 Blogger용 HTML을 돌려준다.

Flask는 이 파일에만 있다. 변환 로직은 `converter/` 패키지에 있고 프레임워크를
전혀 모른다 — 나중에 블로그(Django)에 붙일 때 그 폴더만 옮기면 되게 하려는 것이다.

    python app.py   →  http://127.0.0.1:5001
"""

from flask import Flask, jsonify, render_template, request

from converter import convert
from converter.snippet import THEME_SNIPPET
from tools import nav

app = Flask(__name__)

#: 붙여넣기 사고로 브라우저가 멈추는 걸 막는 상한. 글 하나로는 넉넉하다.
MAX_INPUT = 2_000_000


@app.get("/")
def index():
    return render_template("index.html", theme_snippet=THEME_SNIPPET, **nav("convert"))


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
