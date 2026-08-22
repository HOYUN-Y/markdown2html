/* 다이어그램 편집기 화면 동작.
 *
 * 이 화면에는 서버 API가 없다. mermaid는 브라우저에서 그리는 라이브러리이고,
 * **브라우저에서 그려야 Blogger에 붙여넣었을 때와 같은 그림이 나온다** —
 * Blogger 쪽도 테마 스니펫의 같은 mermaid가 같은 소스를 그리기 때문이다.
 * 주소·테마는 converter/snippet.py가 유일한 출처이고 body의 data-*로 넘어온다.
 *
 * ES 모듈이라 파일 전체가 이미 자기 스코프다 — app.js의 IIFE 껍데기가 없다.
 */

import { mountDocs } from "./docs.js";

var body = document.body;
var src = document.getElementById("src");
var stage = document.getElementById("stage");
var slot = document.getElementById("slot");
var banners = document.getElementById("banners");
var srcStat = document.getElementById("srcStat");
var outStat = document.getElementById("outStat");
var copyBtn = document.getElementById("copyBtn");
var svgBtn = document.getElementById("svgBtn");
var pngBtn = document.getElementById("pngBtn");

var TEMPLATES = JSON.parse(document.getElementById("tplData").textContent);
var STORE_KEY = "md2blogger:mermaid";
var THEME = body.dataset.mermaidTheme;

// PNG 배율. 2배로 그려야 확대했을 때 글자가 뭉개지지 않는다.
var PNG_SCALE = 2;

var mermaid = null;      // 지연 로딩 — 첫 렌더 때 CDN에서 받는다
var loading = null;      // 로딩 Promise. 여러 번 부르지 않게 붙잡아 둔다
var timer = null;
var seq = 0;             // 렌더 id. mermaid는 같은 id를 다시 쓰면 안 된다
var lastSvg = "";        // 마지막으로 성공한 SVG — 내보내기가 이걸 쓴다
var undoSource = null;   // 템플릿을 불러오기 직전의 원고

/* ── mermaid 로딩 ─────────────────────────────────────── */

// 미리보기는 **Blogger와 같은 기본 설정**으로 그린다. PNG 경로만 잠시 바꿨다가
// 이 함수로 되돌린다(아래 toPngBlob 참고).
function applyConfig(extra) {
  var config = { startOnLoad: false, theme: THEME };
  Object.keys(extra || {}).forEach(function (key) { config[key] = extra[key]; });
  mermaid.initialize(config);
}

function loadMermaid() {
  if (loading) return loading;
  loading = import(body.dataset.mermaidSrc)
    .then(function (module) {
      mermaid = module.default;
      applyConfig();
      return mermaid;
    })
    .catch(function (err) {
      loading = null;   // 네트워크가 돌아오면 다시 시도할 수 있게 둔다
      throw new Error("mermaid를 불러오지 못했습니다 (인터넷 연결을 확인하세요): " + err.message);
    });
  return loading;
}

/* ── 렌더 ─────────────────────────────────────────────── */

function schedule() {
  var lines = src.value ? src.value.split("\n").length : 0;
  srcStat.textContent = lines ? lines + "줄" : "";
  save();
  clearTimeout(timer);
  timer = setTimeout(render, 300);
}

function render() {
  var source = src.value.trim();
  if (!source) {
    slot.textContent = "";
    lastSvg = "";
    outStat.textContent = "";
    stage.classList.remove("is-stale");
    setBanners([]);
    refreshButtons();
    return;
  }

  loadMermaid()
    .then(function (m) {
      // parse를 먼저 부른다. render는 문법이 틀리면 화면에 자기 오류 그림을
      // 남기는데, 그러면 직전에 잘 그려진 다이어그램이 사라진다.
      return m.parse(source).then(function () {
        seq += 1;
        return m.render("dgm" + seq, source);
      });
    })
    .then(function (result) {
      slot.innerHTML = result.svg;
      lastSvg = result.svg;
      stage.classList.remove("is-stale");
      var size = svgSize(result.svg);
      outStat.textContent = Math.round(size.w) + "×" + Math.round(size.h);
      setBanners([]);
      refreshButtons();
    })
    .catch(function (err) {
      // 마지막으로 성공한 그림은 지우지 않는다. 한 글자 고치는 중에 화면이
      // 비면 무엇을 고치고 있었는지가 사라진다 — 흐리게 두고 오류만 알린다.
      cleanupStray();
      stage.classList.toggle("is-stale", !!lastSvg);
      setBanners([{ kind: "error", tag: "문법", text: tidyError(err) }]);
      refreshButtons();
    });
}

// 렌더가 실패하면 mermaid가 임시 요소를 body에 남기는 경우가 있다. 쌓이면
// 화면 아래에 빈 자리가 생기므로 그때그때 걷어낸다.
function cleanupStray() {
  ["dgm" + seq, "ddgm" + seq].forEach(function (id) {
    var el = document.getElementById(id);
    if (el && !slot.contains(el)) el.remove();
  });
}

// mermaid 오류 메시지는 줄바꿈과 ASCII 화살표로 여러 줄이다. 배너 한 줄에
// 넣으면 뭉개지므로 첫 두 줄(무엇이·어디서)만 남긴다.
function tidyError(err) {
  var message = (err && err.message) || String(err);
  var lines = message.split("\n").map(function (line) { return line.trim(); })
    .filter(function (line) { return line.length > 0; });
  return lines.slice(0, 2).join(" — ") || "문법을 해석하지 못했습니다.";
}

// 내보내기는 viewBox에서 크기를 얻는다. mermaid는 width를 100%로 두는 경우가
// 있어 속성만 믿으면 0×0짜리 PNG가 나온다.
function svgSize(svg) {
  var box = /viewBox="([\d.\-\s]+)"/.exec(svg);
  if (box) {
    var parts = box[1].trim().split(/\s+/);
    if (parts.length === 4) return { w: parseFloat(parts[2]), h: parseFloat(parts[3]) };
  }
  var el = slot.querySelector("svg");
  if (el) {
    var rect = el.getBoundingClientRect();
    if (rect.width && rect.height) return { w: rect.width, h: rect.height };
  }
  return { w: 800, h: 600 };
}

/* ── 내보내기 ─────────────────────────────────────────── */

// 크기를 픽셀로 박고 xmlns를 보장한다. 파일로 떨어진 SVG는 브라우저가 아니라
// 이미지 뷰어·워드프로세서가 열 수도 있어서, 스스로 크기를 알아야 한다.
//
// **여는 태그의 width/height/style을 먼저 지우고 다시 넣는다.** mermaid는 이미
// width와 style="max-width:…"를 달아서 내놓기 때문에, 앞에 그냥 끼워 넣으면
// 속성이 두 번 나온다 — SVG는 XML이라 `Attribute width redefined`로 **파일 전체가
// 무효가 되고**, 브라우저는 그 그림을 아예 읽지 못한다(내보내기가 조용히 실패한다).
function standalone(svg) {
  var size = svgSize(svg);
  var head = /^<svg[^>]*>/.exec(svg);
  if (!head) return svg;
  var opening = head[0]
    .replace(/\s(?:width|height|style)="[^"]*"/g, "")
    .replace(/^<svg /, '<svg width="' + Math.round(size.w) + '" height="' +
      Math.round(size.h) + '" ');
  if (opening.indexOf("xmlns=") === -1) {
    opening = opening.replace(/^<svg /, '<svg xmlns="http://www.w3.org/2000/svg" ');
  }
  return opening + svg.slice(head[0].length);
}

function download(blob, filename) {
  var url = URL.createObjectURL(blob);
  var link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
}

function saveSvg() {
  if (!lastSvg) return;
  download(new Blob([standalone(lastSvg)], { type: "image/svg+xml;charset=utf-8" }),
           "diagram.svg");
  flash(svgBtn, "저장됨");
}

// PNG는 **미리보기와 다른 설정으로 다시 그린다.**
// mermaid는 기본적으로 라벨을 <foreignObject> 안의 HTML로 그리는데, 그 SVG를
// canvas에 올리면 브라우저가 foreignObject를 래스터화하지 못해 **글자가 통째로
// 빠진 그림**이 나온다. htmlLabels를 끄면 라벨이 <text>가 되어 정상적으로 찍힌다.
// 미리보기까지 끄지 않는 것은, 미리보기는 Blogger에서 보일 모습(기본 설정)과
// 같아야 하기 때문이다. 대신 PNG의 글자 모양이 미리보기와 미세하게 다를 수 있다.
function toPngBlob(source) {
  return loadMermaid()
    .then(function (m) {
      applyConfig({ flowchart: { htmlLabels: false }, class: { htmlLabels: false } });
      seq += 1;
      return m.render("png" + seq, source);
    })
    .then(function (result) {
      applyConfig();               // 미리보기용 설정으로 되돌린다
      return rasterize(standalone(result.svg));
    })
    .catch(function (err) {
      applyConfig();
      throw err;
    });
}

function rasterize(svg) {
  return new Promise(function (resolve, reject) {
    var size = svgSize(svg);
    var url = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml;charset=utf-8" }));
    var image = new Image();
    image.onload = function () {
      var canvas = document.createElement("canvas");
      canvas.width = Math.round(size.w * PNG_SCALE);
      canvas.height = Math.round(size.h * PNG_SCALE);
      var ctx = canvas.getContext("2d");
      // 투명한 채로 두면 어두운 편집기에 올렸을 때 글자가 배경에 묻힌다.
      // 다이어그램 테마(neutral)가 밝은 배경을 전제하므로 흰 바탕을 깐다.
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      canvas.toBlob(function (blob) {
        blob ? resolve(blob) : reject(new Error("PNG로 바꾸지 못했습니다."));
      }, "image/png");
    };
    image.onerror = function () {
      URL.revokeObjectURL(url);
      reject(new Error("SVG를 이미지로 읽지 못했습니다."));
    };
    image.src = url;
  });
}

function savePng() {
  var source = src.value.trim();
  if (!source || !lastSvg) return;
  pngBtn.disabled = true;
  toPngBlob(source)
    .then(function (blob) {
      download(blob, "diagram.png");
      flash(pngBtn, "저장됨");
    })
    .catch(function (err) {
      setBanners([{ kind: "error", tag: "오류", text: tidyError(err) }]);
    })
    .then(function () { refreshButtons(); });
}

function codeBlock() {
  return "```mermaid\n" + src.value.trim() + "\n```";
}

function copyCode() {
  if (!src.value.trim()) return;
  navigator.clipboard.writeText(codeBlock())
    .then(function () { flash(copyBtn, "복사됨"); })
    .catch(function () {
      setBanners([{ kind: "error", tag: "오류",
        text: "클립보드 복사에 실패했습니다. 왼쪽 소스를 직접 선택해 복사하세요." }]);
    });
}

/* ── 화면 ─────────────────────────────────────────────── */

function flash(button, label) {
  var original = button.textContent;
  button.textContent = label;
  button.classList.add("is-done");
  setTimeout(function () {
    button.textContent = original;
    button.classList.remove("is-done");
  }, 1400);
}

function refreshButtons() {
  var ready = !!lastSvg;
  svgBtn.disabled = !ready;
  pngBtn.disabled = !ready;
  copyBtn.disabled = !src.value.trim();
}

function setBanners(items) {
  banners.textContent = "";
  items.forEach(function (item) {
    var el = document.createElement("div");
    el.className = "banner banner-" + item.kind;
    var tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = item.tag;
    var text = document.createElement("span");
    text.textContent = item.text;     // 라이브러리 메시지를 HTML로 해석하지 않는다
    el.appendChild(tag);
    el.appendChild(text);
    if (item.action) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "banner-act";
      button.textContent = item.action.label;
      button.addEventListener("click", item.action.run);
      el.appendChild(button);
    }
    banners.appendChild(el);
  });
}

function setSurface(name) {
  stage.classList.toggle("is-dark", name === "dark");
  document.querySelectorAll("#surfaceChips .b-chip").forEach(function (chip) {
    chip.classList.toggle("is-on", chip.dataset.surface === name);
  });
  save();
}

// 템플릿은 원고를 통째로 갈아치운다. 물어보는 대화상자로 흐름을 끊는 대신
// **되돌릴 수 있게** 두었다 — 배너의 되돌리기가 직전 원고를 돌려놓는다.
// (textarea의 값을 코드로 바꾸면 브라우저의 Ctrl+Z가 듣지 않는다.)
function useTemplate(slug) {
  var found = TEMPLATES.filter(function (t) { return t.slug === slug; })[0];
  if (!found) return;
  var previous = src.value;
  src.value = found.source;
  schedule();
  render();
  if (previous.trim() && previous.trim() !== found.source.trim()) {
    undoSource = previous;
    setBanners([{
      kind: "note", tag: "안내", text: "'" + found.name + "' 템플릿을 불러왔습니다.",
      action: { label: "되돌리기", run: undoTemplate }
    }]);
  }
}

function undoTemplate() {
  if (undoSource === null) return;
  src.value = undoSource;
  undoSource = null;
  schedule();
  render();
}

/* ── 저장 — 새로고침으로 원고를 잃지 않게 ──────────────── */

function save() {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify({
      source: src.value,
      surface: stage.classList.contains("is-dark") ? "dark" : "light"
    }));
  } catch (e) { /* 사파리 프라이빗 모드 등 — 저장 실패는 무시 */ }
}

function load() {
  try {
    var saved = JSON.parse(localStorage.getItem(STORE_KEY) || "{}");
    // 저장된 원고가 있으면 그것을 쓴다. 없으면 템플릿에서 채워 온 기본값이
    // 이미 textarea에 들어 있다 — 빈 화면으로 시작하지 않게.
    if (typeof saved.source === "string" && saved.source.trim()) src.value = saved.source;
    if (saved.surface) setSurface(saved.surface);
  } catch (e) { /* 저장값이 깨졌으면 기본값으로 간다 */ }
}

/* ── 배선 ─────────────────────────────────────────────── */

src.addEventListener("input", function () {
  undoSource = null;       // 직접 고치기 시작하면 템플릿 되돌리기는 의미가 없다
  schedule();
});
document.querySelectorAll("#tplChips .b-chip").forEach(function (chip) {
  chip.addEventListener("click", function () { useTemplate(chip.dataset.slug); });
});
document.querySelectorAll("#surfaceChips .b-chip").forEach(function (chip) {
  chip.addEventListener("click", function () { setSurface(chip.dataset.surface); });
});
copyBtn.addEventListener("click", copyCode);
svgBtn.addEventListener("click", saveSvg);
pngBtn.addEventListener("click", savePng);

load();
schedule();
render();

// 서버 저장. 저장하는 것은 **소스 텍스트**다 — SVG·PNG는 여기서 다시 만들 수 있다.
mountDocs({
  tool: "mermaid",
  getContent: function () { return src.value; },
  setContent: function (text) {
    src.value = text;
    undoSource = null;
    schedule();
    render();
  }
});
