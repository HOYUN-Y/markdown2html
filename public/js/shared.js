/* 도구 화면들이 함께 쓰는 조각.
 *
 * `/mermaid`와 `/drawio`는 하는 일이 다르지만 **끝은 같다** — 그린 것을 파일로 떨구고,
 * 클립보드에 넣고, 잘못되면 배너로 알린다. 같은 코드를 두 벌 두면 한쪽만 고쳐진다.
 *
 * 변환 화면(`app.js`)은 서버가 다 하는 구조라 여기에 얹지 않았다. 억지로 합치면
 * 세 화면이 서로를 붙잡아 한 화면만 바꾸기가 어려워진다.
 */

/** Blob을 파일로 떨군다. objectURL은 잠시 뒤 반납한다(바로 지우면 저장이 취소된다). */
export function download(blob, filename) {
  var url = URL.createObjectURL(blob);
  var link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
}

/** 버튼에 '됐다'를 잠깐 띄웠다가 원래 이름으로 돌려놓는다. */
export function flash(button, label) {
  var original = button.textContent;
  button.textContent = label;
  button.classList.add("is-done");
  setTimeout(function () {
    button.textContent = original;
    button.classList.remove("is-done");
  }, 1400);
}

/** 배너를 다시 그린다. `items`: `{kind, tag, text, action?:{label, run}}`. */
export function setBanners(container, items) {
  container.textContent = "";
  (items || []).forEach(function (item) {
    var el = document.createElement("div");
    el.className = "banner banner-" + item.kind;
    var tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = item.tag;
    var text = document.createElement("span");
    // 라이브러리·외부 메시지를 HTML로 해석하지 않는다.
    text.textContent = item.text;
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
    container.appendChild(el);
  });
}
