/* 서버에 저장한 문서 — 세 도구가 함께 쓰는 저장·불러오기 막대.
 *
 * 도구마다 다루는 것이 다르지만(마크다운 원문·mermaid 소스·.drawio XML) 저장하는
 * 모양은 '제목 붙은 원본 한 덩어리'로 같다. 그래서 화면 조각도 하나만 둔다.
 *
 * 부르는 쪽은 **무엇을 저장하고 무엇을 되돌려 놓을지**만 알려 준다.
 *
 *     mountDocs({
 *       tool: "mermaid",
 *       getContent: function () { return src.value; },
 *       setContent: function (text) { src.value = text; render(); }
 *     });
 *
 * 자동 저장은 여전히 localStorage가 맡는다. 여기는 **사용자가 저장을 누를 때만**
 * 움직인다 — draw.io는 도형을 끌 때마다 autosave가 와서, 그걸 매번 서버로 보내면
 * 요청이 폭주한다. 로컬은 '작업 중', 서버는 '남겨 둘 것'으로 역할을 나눈다.
 */

import { flash, setBanners } from "./shared.js";

export function mountDocs(options) {
  var mount = document.getElementById("docsMount");
  if (!mount) return null;      // db_on이 아니면 화면에 자리 자체가 없다

  var banners = document.getElementById("banners");
  var tool = options.tool;
  var openId = null;            // 지금 열어 둔 문서. 있으면 저장이 덮어쓴다

  var title = el("input", "ed-input docs-title");
  title.type = "text";
  title.placeholder = "제목 없이 저장하면 '제목 없음'이 됩니다";
  title.setAttribute("aria-label", "문서 제목");

  var saveBtn = el("button", "b-btn b-btn-line", "저장");
  var newBtn = el("button", "b-btn b-btn-line", "새로");
  var listBtn = el("button", "b-btn b-btn-line", "불러오기 ▾");
  var menu = el("div", "docs-menu hidden");

  var bar = el("div", "docs-bar");
  bar.appendChild(el("span", "ed-label docs-label", "저장한 문서"));
  bar.appendChild(title);
  bar.appendChild(saveBtn);
  bar.appendChild(newBtn);
  var listWrap = el("div", "docs-list-wrap");
  listWrap.appendChild(listBtn);
  listWrap.appendChild(menu);
  bar.appendChild(listWrap);
  mount.appendChild(bar);

  /* ── 서버 ───────────────────────────────────────────── */

  function call(path, init) {
    return fetch(path, init).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (body) {
        if (!res.ok) throw new Error(body.error || "요청에 실패했습니다.");
        return body;
      });
    });
  }

  function save() {
    var content = options.getContent();
    if (!content || !content.trim()) {
      warn("저장할 내용이 없습니다.");
      return;
    }
    saveBtn.disabled = true;
    call("/api/docs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tool: tool, id: openId, title: title.value, content: content
      })
    })
      .then(function (body) {
        openId = body.doc.id;
        title.value = body.doc.title;
        flash(saveBtn, "저장됨");
        setBanners(banners, []);
      })
      .catch(fail)
      .then(function () { saveBtn.disabled = false; });
  }

  function toggleList() {
    if (!menu.classList.contains("hidden")) {
      menu.classList.add("hidden");
      return;
    }
    refreshList();
  }

  function refreshList() {
    menu.textContent = "";
    menu.appendChild(el("div", "docs-empty", "불러오는 중…"));
    menu.classList.remove("hidden");

    call("/api/docs?tool=" + encodeURIComponent(tool))
      .then(function (body) { render(body.docs || []); })
      .catch(function (err) { menu.classList.add("hidden"); fail(err); });
  }

  function render(docs) {
    menu.textContent = "";
    if (!docs.length) {
      menu.appendChild(el("div", "docs-empty", "저장한 문서가 없습니다."));
      return;
    }
    docs.forEach(function (doc) {
      var row = el("div", "docs-row");
      var open = el("button", "docs-open", doc.title);
      open.type = "button";
      open.appendChild(el("span", "docs-when", when(doc.updated_at)));
      open.addEventListener("click", function () { load(doc.id); });

      var remove = el("button", "docs-del", "삭제");
      remove.type = "button";
      remove.title = doc.title + " 삭제";
      // 대화상자로 흐름을 끊지 않는다. 대신 한 번 더 누르게 한다 —
      // 지운 것은 되돌릴 수 없으므로 실수로 한 번에 지워지면 안 된다.
      remove.addEventListener("click", function () {
        if (remove.dataset.armed !== "1") {
          remove.dataset.armed = "1";
          remove.textContent = "정말?";
          setTimeout(function () {
            remove.dataset.armed = "";
            remove.textContent = "삭제";
          }, 3000);
          return;
        }
        destroy(doc.id);
      });

      row.appendChild(open);
      row.appendChild(remove);
      menu.appendChild(row);
    });
  }

  function load(id) {
    call("/api/docs/" + id)
      .then(function (body) {
        openId = body.doc.id;
        title.value = body.doc.title;
        options.setContent(body.doc.content);
        menu.classList.add("hidden");
        note("'" + body.doc.title + "'을(를) 불러왔습니다. 저장을 누르면 이 문서에 덮어씁니다.");
      })
      .catch(fail);
  }

  function destroy(id) {
    call("/api/docs/" + id, { method: "DELETE" })
      .then(function () {
        if (openId === id) openId = null;   // 지운 문서를 계속 덮어쓰려 하지 않게
        refreshList();
        note("삭제했습니다.");
      })
      .catch(fail);
  }

  function startNew() {
    openId = null;
    title.value = "";
    menu.classList.add("hidden");
    note("새 문서로 저장됩니다. 지금 편집 중인 내용은 그대로 있습니다.");
  }

  /* ── 잔심부름 ───────────────────────────────────────── */

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    if (tag === "button") node.type = "button";
    return node;
  }

  function when(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    return (d.getMonth() + 1) + "/" + d.getDate();
  }

  function note(text) { setBanners(banners, [{ kind: "note", tag: "안내", text: text }]); }
  function warn(text) { setBanners(banners, [{ kind: "warn", tag: "확인", text: text }]); }
  function fail(err) {
    setBanners(banners, [{ kind: "error", tag: "오류",
      text: (err && err.message) || String(err) }]);
  }

  saveBtn.addEventListener("click", save);
  newBtn.addEventListener("click", startNew);
  listBtn.addEventListener("click", toggleList);
  // 바깥을 누르면 목록을 닫는다. 열어 둔 채로 편집하면 화면을 가린다.
  document.addEventListener("click", function (event) {
    if (!listWrap.contains(event.target)) menu.classList.add("hidden");
  });

  return { save: save, current: function () { return openId; } };
}
