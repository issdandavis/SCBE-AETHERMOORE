(function () {
  "use strict";
  if (document.getElementById("aether-source-map-host")) return;
  var script = document.currentScript;
  var sourcePath = script && script.dataset ? script.dataset.aetherSource : "docs/index.html";
  var repo = "https://github.com/issdandavis/SCBE-AETHERMOORE";
  var sourceUrl = repo + "/blob/main/" + sourcePath.split("/").map(encodeURIComponent).join("/");
  var scriptUrl = script && script.src ? new URL(script.src, document.baseURI) : new URL("assets/source-map.js", document.baseURI);
  var mapUrl = new URL("../github-map.html", scriptUrl).href;
  var host = document.createElement("div");
  host.id = "aether-source-map-host";
  host.setAttribute("data-source-path", sourcePath);
  var root = host.attachShadow ? host.attachShadow({ mode: "open" }) : host;
  root.innerHTML = [
    "<style>",
    ":host{all:initial}",
    ".map{position:fixed;left:14px;bottom:14px;z-index:2147483000;display:flex;align-items:center;gap:2px;padding:4px;border:1px solid rgba(244,239,228,.18);border-radius:999px;background:rgba(8,10,12,.9);box-shadow:0 18px 60px rgba(0,0,0,.38);backdrop-filter:blur(16px);font:700 11px/1.1 ui-monospace,SFMono-Regular,Cascadia Mono,Consolas,monospace}",
    ".map:before{content:'GH';display:grid;place-items:center;width:28px;height:28px;border-radius:50% 44% 48% 42%;color:#17100d;background:#d9825b;font-weight:950;transform:rotate(-5deg)}",
    "a{display:inline-flex;align-items:center;min-height:28px;padding:0 9px;border-radius:999px;color:#f4efe4;text-decoration:none;white-space:nowrap}",
    "a:hover,a:focus-visible{color:#ffd0b9;background:rgba(217,130,91,.13);outline:none}",
    ".path{max-width:0;overflow:hidden;color:#a8b3ad;opacity:0;transition:max-width .18s ease,opacity .18s ease}",
    ".map:hover .path,.map:focus-within .path{max-width:240px;opacity:1}",
    "@media(max-width:560px){.map{left:8px;bottom:8px}.path{display:none}a{padding:0 7px}}",
    "@media(prefers-reduced-motion:reduce){.path{transition:none}}",
    "</style>",
    "<nav class='map' aria-label='Page source map'>",
    "<a href='" + sourceUrl + "' target='_blank' rel='noreferrer'>Source <span class='path'>&nbsp;/ " + sourcePath + "</span></a>",
    "<a href='" + mapUrl + "'>All pages</a>",
    "</nav>"
  ].join("");
  document.documentElement.appendChild(host);
})();
