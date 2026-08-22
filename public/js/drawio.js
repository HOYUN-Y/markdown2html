/* draw.io 편집기 화면 동작.
 *
 * 편집기 자체는 draw.io 공식 임베드(iframe)다. 이 파일이 하는 일은 셋뿐이다.
 *
 *   1. 편집기와 postMessage로 대화한다 (JSON 프로토콜, `proto=json`)
 *   2. 그리던 그림을 브라우저에 보관한다 (autosave → localStorage)
 *   3. 내보낸다 — SVG · PNG · .drawio 원본 · 붙여넣기용 인라인 조각
 *
 * 서버는 부르지 않는다. 그림 내용이 우리 쪽으로 오지 않는 것이 이 구조의 값이다.
 * 어려운 부분은 3번이다 — Blogger가 망가뜨리지 않는 조각으로 다듬는 일(`toFragment`).
 */

import { download, flash, setBanners } from "./shared.js";
import { mountDocs } from "./docs.js";

var body = document.body;
var editor = document.getElementById("editor");
var banners = document.getElementById("banners");
var stat = document.getElementById("stat");
var fileInput = document.getElementById("fileInput");

var openBtn = document.getElementById("openBtn");
var xmlBtn = document.getElementById("xmlBtn");
var pngBtn = document.getElementById("pngBtn");
var svgBtn = document.getElementById("svgBtn");
var copyBtn = document.getElementById("copyBtn");
var ACTIONS = [openBtn, xmlBtn, pngBtn, svgBtn, copyBtn];

var ORIGIN = body.dataset.embedOrigin;
var MAX_INLINE = parseInt(body.dataset.maxInline, 10) || 80000;
var WRAP_STYLE = body.dataset.wrapStyle || "margin:28px 0;text-align:center;";
var STORE_KEY = "md2blogger:drawio";

// 편집기가 뜨기까지 기다려 주는 시간. 넘기면 배너로 알린다 — 빈 iframe을 그냥 두면
// 우리 화면이 고장 난 것처럼 보이고, 실제 원인(차단·네트워크)은 화면에 안 나온다.
var BOOT_TIMEOUT = 20000;
var EXPORT_TIMEOUT = 20000;
// 도형을 끌 때마다 autosave가 온다. 매번 통째로 저장하면 드래그가 끊긴다.
var SAVE_DELAY = 1500;
// 파일 불러오기 상한. 넘는 파일은 읽다가 브라우저가 멎느니 거절하는 편이 낫다.
var MAX_FILE = 5 * 1024 * 1024;

var ready = false;
var pending = null;    // 내보내기는 한 번에 하나만. 겹치면 어느 응답인지 짝짓기 어렵다
var seq = 0;
var lastXml = "";      // autosave가 준 최신 원본
var undoXml = null;    // 불러오기 직전의 그림
var bootTimer = null;
var saveTimer = null;
var storeOff = false;

/* ── 편집기와의 대화 ──────────────────────────────────── */

function send(message) {
  // draw.io는 문자열로 주고받는다. 객체를 그대로 보내면 조용히 무시된다.
  // 목적지도 ORIGIN으로 못 박는다 — "*"로 보내면 사용자의 그림 원본을 아무에게나 준다.
  editor.contentWindow.postMessage(JSON.stringify(message), ORIGIN);
}

window.addEventListener("message", function (event) {
  // **출처 검증.** 이걸 빼면 아무 페이지나 우리 창에 내보내기 응답을 흉내 내 보낼 수 있다.
  if (event.origin !== ORIGIN) return;
  if (event.source !== editor.contentWindow) return;
  if (typeof event.data !== "string") return;

  var msg;
  // 확장 프로그램이 같은 창에 문자열 메시지를 뿌리는 일이 흔하다 — 형식이 아니라 실제 필요다.
  try { msg = JSON.parse(event.data); } catch (e) { return; }
  if (!msg || !msg.event) return;

  if (msg.event === "init") {
    clearTimeout(bootTimer);
    ready = true;
    setButtons(true);
    // autosave:1 을 함께 넘겨야 편집기가 바뀔 때마다 원본을 보내 준다.
    send({ action: "load", xml: loadStored(), autosave: 1 });
    setBanners(banners, []);
    return;
  }

  // save는 noSaveBtn=1이어도 Ctrl+S로 올 수 있다. 우리 보관만 갱신한다.
  if (msg.event === "autosave" || msg.event === "save") {
    if (typeof msg.xml === "string" && msg.xml) scheduleStore(msg.xml);
    return;
  }

  if (msg.event === "export") {
    if (!pending) return;
    // 응답에 원 요청이 되돌아오면 그것으로 짝짓고, 없으면 '한 번에 하나' 규칙에 기댄다.
    if (msg.message && msg.message.id && msg.message.id !== pending.id) return;
    var waiting = pending;
    pending = null;
    clearTimeout(waiting.timer);
    setButtons(true);
    waiting.resolve(msg);
  }
});

function requestExport(format, extra) {
  if (!ready) return Promise.reject(new Error("편집기가 아직 준비되지 않았습니다."));
  if (pending) return Promise.reject(new Error("내보내는 중입니다. 잠시 뒤 다시 눌러 주세요."));

  return new Promise(function (resolve, reject) {
    var id = "x" + (++seq);
    var message = { action: "export", format: format, id: id };
    Object.keys(extra || {}).forEach(function (key) { message[key] = extra[key]; });

    pending = {
      id: id,
      resolve: resolve,
      reject: reject,
      // 타임아웃이 없으면 응답이 한 번 유실됐을 때 버튼 다섯이 **영원히 잠긴다** —
      // 사용자에게는 '눌러도 아무 일이 없는 화면'으로 보이고 콘솔에도 안 남는다.
      timer: setTimeout(function () {
        pending = null;
        setButtons(true);
        reject(new Error("편집기가 응답하지 않습니다. 새로고침한 뒤 다시 시도해 주세요."));
      }, EXPORT_TIMEOUT)
    };
    setButtons(false);
    send(message);
  });
}

/* ── 내보내기 ─────────────────────────────────────────── */

// 내보낸 데이터는 data URI로 온다. fetch에 태우면 base64 디코딩도, 한글(UTF-8)
// 처리도 브라우저가 해 준다 — atob으로 직접 풀면 한글 라벨만 조용히 깨진다.
function asBlob(dataUri) { return fetch(dataUri).then(function (r) { return r.blob(); }); }
function asText(dataUri) { return fetch(dataUri).then(function (r) { return r.text(); }); }

function saveSvg() {
  // xmlsvg = 그림 + 원본 XML. 이 파일을 다시 불러오면 이어서 편집된다.
  // 확장자를 .drawio.svg로 두는 것이 draw.io 관례이고, 편집 가능한 파일임을 이름이 알린다.
  run(requestExport("xmlsvg")
    .then(function (msg) { return asBlob(msg.data); })
    .then(function (blob) {
      download(blob, "diagram.drawio.svg");
      flash(svgBtn, "저장됨");
      note("SVG를 저장했습니다. 이 파일은 '불러오기'로 다시 열어 편집할 수 있습니다.");
    }));
}

function savePng() {
  // 2배로 뽑아야 확대했을 때 글자가 뭉개지지 않는다(mermaid 쪽 PNG와 같은 기준).
  // 배경을 흰색으로 깔지 않으면 검은 테마 Blogger에서 검은 글자가 배경에 묻힌다.
  run(requestExport("xmlpng", { scale: 2, background: "#ffffff" })
    .then(function (msg) { return asBlob(msg.data); })
    .then(function (blob) {
      download(blob, "diagram.drawio.png");
      flash(pngBtn, "저장됨");
    }));
}

function saveXml() {
  // 포맷을 가리지 않고 export 응답에는 원본 XML이 함께 온다. autosave가 준 것이
  // 있으면 그걸 먼저 쓴다 — 왕복 한 번을 아낀다.
  var source = lastXml
    ? Promise.resolve(lastXml)
    : requestExport("xmlsvg").then(function (msg) { return msg.xml || ""; });

  run(source.then(function (xml) {
    if (!xml) throw new Error("그림이 비어 있습니다.");
    download(new Blob([xml], { type: "application/xml;charset=utf-8" }), "diagram.drawio");
    flash(xmlBtn, "저장됨");
  }));
}

function copyInline() {
  // 인라인 조각은 원본 XML을 넣지 않은 `svg`로 뽑는다. 붙여넣는 글에 들어갈 것이라
  // 길이가 곧 대가이고, 게다가 `xmlsvg`의 content 속성에 든 이스케이프(&lt;mxfile…)는
  // 우리 변환기를 지나면 풀려 버린다. 다시 편집할 원본은 파일 저장 쪽이 맡는다.
  run(requestExport("svg", { background: "#ffffff" })
    .then(function (msg) { return asText(msg.data); })
    .then(function (svg) {
      var snippet = toFragment(svg);
      return navigator.clipboard.writeText(snippet).then(function () {
        flash(copyBtn, "복사됨");
        stat.textContent = "조각 " + snippet.length.toLocaleString("ko-KR") + "자";
        reportSnippet(snippet);
      });
    })
    .catch(function (err) {
      if (err && err.name === "NotAllowedError") {
        throw new Error("클립보드 복사가 막혔습니다. 주소창의 권한을 확인해 주세요.");
      }
      throw err;
    }));
}

/** 붙여넣어도 깨지지 않는 조각으로 다듬는다. */
function toFragment(svgText) {
  var svg = svgText.replace(/^﻿/, "").trim();

  // XML 선언·DOCTYPE·주석은 글 본문에 필요 없다. 우리 변환기의 `_Inliner`는 주석과
  // 선언을 **그대로 통과시키므로**(handle_comment/handle_decl) 여기서 지워야 없어진다.
  svg = svg.replace(/<\?xml[\s\S]*?\?>/g, "")
           .replace(/<!DOCTYPE[\s\S]*?>/gi, "")
           .replace(/<!--[\s\S]*?-->/g, "")
           .trim();

  // id를 조각마다 다르게 만든다. draw.io SVG는 화살표 머리·그라디언트를 <defs>의 id로
  // 참조하는데, 한 글에 그림을 둘 넣으면 **두 번째가 첫 번째의 정의를 먹어** 화살표가
  // 사라지거나 색이 바뀐다. 오류는 나지 않는다 — 눈으로만 보이는 고장이다.
  svg = uniquifyIds(svg, "dio" + Math.random().toString(36).slice(2, 8) + "-");

  // 본문 폭을 넘는 그림이 잘리지 않게. converter/theme.py의 tag_styles에는 svg가 없어
  // 이 style이 덮어써지지 않는다(img의 width:100%가 작성자 style을 이기는 것과 다르다).
  svg = svg.replace(/^<svg /, '<svg style="max-width:100%;height:auto" ');

  // 개행을 한 글자도 남기지 않는다. Blogger의 '엔터 = 줄바꿈' 설정이 켜져 있으면
  // 개행이 전부 <br>로 바뀌어 그림 아래에 빈 줄이 쌓인다.
  // (converter/blogger.py가 본문에 대해 하는 일과 같고, 이유도 같다.)
  svg = svg.replace(/\r\n?|\n/g, " ").replace(/\s{2,}/g, " ");

  // <div>로 감싼다. 마크다운 원문에 최상위 <svg>를 그냥 넣으면 Python-Markdown이
  // 인라인 raw HTML로 보고 **안쪽 텍스트에까지 마크다운 문법을 적용한다** —
  // <text>*강조*</text>가 <em>이 되어 그림 안에 태그가 박힌다. <div>로 감싸면
  // 블록 raw HTML로 통째 보존되고, <p> 껍데기도 생기지 않는다.
  return '<div style="' + WRAP_STYLE + '">' + svg + "</div>";
}

function uniquifyIds(svg, prefix) {
  var ids = [];
  svg.replace(/\sid="([^"]+)"/g, function (whole, id) { ids.push(id); return whole; });
  ids.forEach(function (id) {
    var safe = id.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    svg = svg
      .replace(new RegExp('(\\sid=")' + safe + '(")', "g"), "$1" + prefix + id + "$2")
      .replace(new RegExp('(url\\(#)' + safe + '(\\))', "g"), "$1" + prefix + id + "$2")
      .replace(new RegExp('((?:xlink:)?href="#)' + safe + '(")', "g"), "$1" + prefix + id + "$2");
  });
  return svg;
}

/** 조각을 보고 사용자가 알아야 할 것만 말한다. */
function reportSnippet(snippet) {
  var messages = [];

  if (snippet.length > MAX_INLINE) {
    messages.push({
      kind: "warn", tag: "확인",
      text: "조각이 " + snippet.length.toLocaleString("ko-KR") + "자입니다. " +
            "Blogger 편집기가 버거워할 수 있으니 SVG·PNG로 저장해 이미지로 올리는 편이 낫습니다."
    });
  }
  if (snippet.indexOf("<foreignObject") !== -1) {
    // 우리 변환기의 HTML 파서가 태그명을 소문자로 눌러 foreignobject가 된다.
    // 브라우저는 되살리지만 Blogger 편집기가 다시 직렬화하면 장담할 수 없다.
    messages.push({
      kind: "warn", tag: "확인",
      text: "그림에 HTML 라벨(foreignObject)이 들어 있습니다. 붙여넣은 뒤 글자가 " +
            "보이는지 확인하시고, 미덥지 않으면 SVG·PNG 파일 저장을 쓰세요."
    });
  }
  if (!messages.length) {
    messages.push({
      kind: "note", tag: "안내",
      text: "Blogger 글쓰기의 'HTML 보기'에 그대로 붙여넣으세요. 마크다운 원문에 넣어도 됩니다."
    });
  }
  setBanners(banners, messages);
}

/* ── 불러오기 ─────────────────────────────────────────── */

function openFile(file) {
  if (file.size > MAX_FILE) {
    showError("파일이 너무 큽니다 (" + Math.round(file.size / 1024 / 1024) + "MB). 5MB까지 받습니다.");
    return;
  }

  var reader = new FileReader();
  reader.onload = function () {
    var text = String(reader.result || "");
    var xml = text;

    if (text.indexOf("<svg") !== -1 && /^\s*<(\?xml|svg|!DOCTYPE)/i.test(text)) {
      // 편집 가능한 SVG는 원본을 루트의 content 속성에 넣어 둔다. 값 안에는 &quot;가
      // 잔뜩 들어 있어 **정규식으로 뽑으면 잘린다** — 잘린 XML을 넣으면 편집기가
      // 빈 화면이 되고 오류도 안 난다. DOMParser는 실체 참조를 알아서 풀어 준다.
      var doc = new DOMParser().parseFromString(text, "image/svg+xml");
      if (doc.querySelector("parsererror")) {
        showError("SVG를 읽지 못했습니다.");
        return;
      }
      // 파싱한 문서를 화면에 넣지 않는다 — 넣는 순간 안의 스크립트가 살아난다.
      var embedded = doc.documentElement && doc.documentElement.getAttribute("content");
      if (!embedded) {
        warn("이 SVG에는 원본이 들어 있지 않아 이어서 편집할 수 없습니다. " +
             "'SVG 저장'으로 만든 파일이나 .drawio 파일을 넣어 주세요.");
        return;
      }
      xml = embedded;
    } else if (text.indexOf("<mxfile") === -1 && text.indexOf("<mxGraphModel") === -1) {
      showError("draw.io 파일이 아닙니다 (.drawio · .xml · 편집 가능한 .svg 를 받습니다).");
      return;
    }

    undoXml = lastXml;
    send({ action: "load", xml: xml, autosave: 1 });
    scheduleStore(xml);
    setBanners(banners, [{
      kind: "note", tag: "안내", text: "불러왔습니다. 그리던 그림은 덮어썼습니다.",
      action: undoXml ? { label: "되돌리기", run: undoOpen } : null
    }]);
  };
  reader.onerror = function () { showError("파일을 읽지 못했습니다."); };
  reader.readAsText(file);
}

function undoOpen() {
  if (undoXml === null) return;
  send({ action: "load", xml: undoXml, autosave: 1 });
  scheduleStore(undoXml);
  undoXml = null;
  note("되돌렸습니다.");
}

/* ── 보관 — 새로고침으로 그리던 것을 잃지 않게 ─────────── */

function scheduleStore(xml) {
  lastXml = xml;
  stat.textContent = xml.length.toLocaleString("ko-KR") + "자";
  clearTimeout(saveTimer);
  saveTimer = setTimeout(function () { store(xml); }, SAVE_DELAY);
}

function store(xml) {
  if (storeOff) return;
  try {
    localStorage.setItem(STORE_KEY, xml);
  } catch (e) {
    // **조용히 넘기지 않는다.** draw.io XML은 그림 안에 이미지가 들어가면 MB 단위가
    // 되어 실제로 한도를 넘는다. 삼키면 사용자는 저장되는 줄 알다가 새로고침에서 잃는다.
    storeOff = true;
    warn("그림이 커서 자동 저장을 멈췄습니다. '.drawio 저장'으로 파일을 남겨 두세요.");
  }
}

function loadStored() {
  try { return localStorage.getItem(STORE_KEY) || ""; }
  catch (e) { return ""; }
}

/* ── 화면 ─────────────────────────────────────────────── */

function setButtons(enabled) {
  ACTIONS.forEach(function (button) { button.disabled = !enabled; });
}

function note(text) { setBanners(banners, [{ kind: "note", tag: "안내", text: text }]); }
function warn(text) { setBanners(banners, [{ kind: "warn", tag: "확인", text: text }]); }
function showError(text) { setBanners(banners, [{ kind: "error", tag: "오류", text: text }]); }

/** 내보내기 약속 하나를 태우고, 실패는 전부 배너로 보낸다. */
function run(promise) {
  promise.catch(function (err) {
    setButtons(true);
    showError((err && err.message) || String(err));
  });
}

function watchBoot() {
  clearTimeout(bootTimer);
  bootTimer = setTimeout(function () {
    if (ready) return;
    setBanners(banners, [{
      kind: "error", tag: "오류",
      text: "편집기를 불러오지 못했습니다. 네트워크나 차단 프로그램이 " + ORIGIN +
            " 접근을 막고 있는지 확인해 주세요.",
      action: { label: "다시 시도", run: reloadEditor }
    }]);
  }, BOOT_TIMEOUT);
}

function reloadEditor() {
  ready = false;
  setButtons(false);
  setBanners(banners, [{ kind: "note", tag: "안내", text: "편집기를 다시 불러오는 중입니다…" }]);
  editor.src = editor.src;
  watchBoot();
}

/* ── 배선 ─────────────────────────────────────────────── */

setButtons(false);
watchBoot();

openBtn.addEventListener("click", function () { fileInput.click(); });
fileInput.addEventListener("change", function () {
  if (fileInput.files && fileInput.files[0]) openFile(fileInput.files[0]);
  fileInput.value = "";     // 같은 파일을 다시 골라도 change가 뜨게
});
svgBtn.addEventListener("click", saveSvg);
pngBtn.addEventListener("click", savePng);
xmlBtn.addEventListener("click", saveXml);
copyBtn.addEventListener("click", copyInline);

// 서버 저장. 저장하는 것은 **.drawio 원본 XML**이다 — 그림(SVG·PNG)은 이걸로 다시 만든다.
mountDocs({
  tool: "drawio",
  getContent: function () { return lastXml; },
  setContent: function (xml) {
    undoXml = lastXml;
    scheduleStore(xml);
    // 편집기가 아직 안 떴으면 넣을 곳이 없다. init이 오면 저장해 둔 것을 싣는다.
    if (ready) send({ action: "load", xml: xml, autosave: 1 });
  }
});
