/* 마크다운 → Blogger 변환기 화면 동작.
 *
 * 변환은 전부 서버(converter 패키지)가 한다. 여기서는 입력을 모아 보내고
 * 결과를 보여주기만 한다 — 브라우저에서 따로 변환하면 서버 결과와 달라져,
 * 미리보기가 실제로 붙여넣을 HTML과 어긋나게 된다.
 */
(function () {
  "use strict";

  var src = document.getElementById("src");
  var out = document.getElementById("out");
  var preview = document.getElementById("preview");
  var banners = document.getElementById("banners");
  var srcStat = document.getElementById("srcStat");
  var outStat = document.getElementById("outStat");
  var baseUrl = document.getElementById("baseUrl");
  var safeLinebreaks = document.getElementById("safeLinebreaks");
  var wrapDiv = document.getElementById("wrapDiv");
  var copyBtn = document.getElementById("copyBtn");

  var dlg = document.getElementById("snippetDlg");
  var snippetCode = document.getElementById("snippetCode");

  var STORE_KEY = "md2blogger:options";
  var timer = null;

  // ── 옵션 저장 — 매번 기준 URL을 다시 치지 않게 ────────────
  function loadOptions() {
    try {
      var saved = JSON.parse(localStorage.getItem(STORE_KEY) || "{}");
      if (saved.baseUrl) baseUrl.value = saved.baseUrl;
      if (typeof saved.safeLinebreaks === "boolean") safeLinebreaks.checked = saved.safeLinebreaks;
      if (typeof saved.wrapDiv === "boolean") wrapDiv.checked = saved.wrapDiv;
    } catch (e) { /* 저장값이 깨졌으면 기본값으로 간다 */ }
  }

  function saveOptions() {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify({
        baseUrl: baseUrl.value,
        safeLinebreaks: safeLinebreaks.checked,
        wrapDiv: wrapDiv.checked
      }));
    } catch (e) { /* 사파리 프라이빗 모드 등 — 저장 실패는 무시 */ }
  }

  // ── 변환 ───────────────────────────────────────────────
  function schedule() {
    srcStat.textContent = src.value.length.toLocaleString("ko-KR") + "자";
    clearTimeout(timer);
    timer = setTimeout(convert, 350);
  }

  function convert() {
    saveOptions();
    if (!src.value.trim()) {
      out.value = "";
      preview.srcdoc = "";
      outStat.textContent = "";
      renderBanners([], []);
      return;
    }
    fetch("/api/convert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        markdown: src.value,
        image_base_url: baseUrl.value,
        safe_linebreaks: safeLinebreaks.checked,
        wrap: wrapDiv.checked
      })
    })
      .then(function (res) { return res.json().then(function (b) { return { ok: res.ok, body: b }; }); })
      .then(function (r) {
        if (!r.ok) { showError(r.body.error || "변환에 실패했습니다."); return; }
        out.value = r.body.html;
        preview.srcdoc = buildPreview(r.body.html);
        outStat.textContent = formatStats(r.body.stats);
        renderBanners(r.body.warnings, r.body.notes);
      })
      .catch(function (err) { showError("서버에 연결하지 못했습니다: " + err.message); });
  }

  function formatStats(s) {
    var parts = [s.characters.toLocaleString("ko-KR") + "자"];
    if (s.code_blocks) parts.push("코드 " + s.code_blocks);
    if (s.images) parts.push("이미지 " + s.images);
    if (s.mermaid) parts.push("다이어그램 " + s.mermaid);
    // 개행이 남아 있으면 Blogger에서 <br>로 변할 수 있다 — 눈에 보이게 둔다.
    parts.push("개행 " + s.newlines);
    return parts.join(" · ");
  }

  // 미리보기는 '스니펫을 넣은 Blogger'와 같은 조건으로 만든다.
  function buildPreview(html) {
    var snippet = snippetCode ? snippetCode.textContent : "";
    return "<!DOCTYPE html><html lang=\"ko\"><head><meta charset=\"utf-8\">" +
      "<style>body{margin:0;padding:30px 34px;background:#fff;}</style>" +
      snippet +
      "</head><body>" + html + "</body></html>";
  }

  // ── 배너 ───────────────────────────────────────────────
  function renderBanners(warnings, notes) {
    banners.textContent = "";
    (warnings || []).forEach(function (m) { banners.appendChild(banner("warn", "확인", m)); });
    (notes || []).forEach(function (m) { banners.appendChild(banner("note", "안내", m)); });
  }

  function showError(message) {
    banners.textContent = "";
    banners.appendChild(banner("error", "오류", message));
  }

  function banner(kind, tag, message) {
    var el = document.createElement("div");
    el.className = "banner banner-" + kind;
    var t = document.createElement("span");
    t.className = "tag";
    t.textContent = tag;
    var body = document.createElement("span");
    body.textContent = message;   // 서버 메시지를 HTML로 해석하지 않는다
    el.appendChild(t);
    el.appendChild(body);
    return el;
  }

  // ── 복사 ───────────────────────────────────────────────
  function copyText(text, button, doneLabel) {
    if (!text) return;
    var original = button.textContent;
    navigator.clipboard.writeText(text).then(function () {
      button.textContent = doneLabel;
      button.classList.add("is-done");
      setTimeout(function () {
        button.textContent = original;
        button.classList.remove("is-done");
      }, 1400);
    }).catch(function () {
      showError("클립보드 복사에 실패했습니다. HTML 탭에서 직접 선택해 복사하세요.");
    });
  }

  // ── 탭 ────────────────────────────────────────────────
  document.querySelectorAll(".tab").forEach(function (tab) {
    tab.addEventListener("click", function () {
      document.querySelectorAll(".tab").forEach(function (t) { t.classList.remove("is-on"); });
      tab.classList.add("is-on");
      var showHtml = tab.dataset.tab === "html";
      out.classList.toggle("hidden", !showHtml);
      preview.classList.toggle("hidden", showHtml);
    });
  });

  // ── 배선 ───────────────────────────────────────────────
  src.addEventListener("input", schedule);
  [baseUrl, safeLinebreaks, wrapDiv].forEach(function (el) {
    el.addEventListener("change", convert);
  });
  copyBtn.addEventListener("click", function () { copyText(out.value, copyBtn, "복사됨"); });

  document.getElementById("snippetBtn").addEventListener("click", function () { dlg.showModal(); });
  document.getElementById("snippetClose").addEventListener("click", function () { dlg.close(); });
  document.getElementById("snippetCopy").addEventListener("click", function (e) {
    copyText(snippetCode.textContent, e.currentTarget, "복사됨");
  });

  loadOptions();
  schedule();
})();
