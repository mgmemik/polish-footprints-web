/* Polish Footprints: Istanbul - language switch (PL/EN/TR) and theme toggle.
   English is baked into the HTML by tools/build.py; Polish and Turkish are loaded from
   assets/i18n/<lang>.json and swapped into every [data-i18n] / [data-i18n-attr] element.
   Language order: ?lang= in the URL, then the visitor's saved choice, then the browser
   (pl -> Polish, tr -> Turkish, anything else -> English).
   Pages pre-rendered in one language (place and walk pages, /pl/, /tr/; the script tag has
   data-lang) are left as they are: their PL/EN/TR switch is made of links to the other versions,
   and a click on one only remembers the choice. */
(function () {
  "use strict";
  var SUPPORTED = ["en", "pl", "tr"];
  var LOCALES = { en: "en_GB", pl: "pl_PL", tr: "tr_TR" };
  var script = document.currentScript;
  var root = (script && script.getAttribute("data-root")) || "";
  var page = (script && script.getAttribute("data-page")) || "home";
  var fixedLang = (script && script.getAttribute("data-lang")) || "";
  var siteRoot = new URL(root || "./", location.href).href;
  var cache = {};

  function store(key, value) {
    try { localStorage.setItem(key, value); } catch (e) {}
  }
  function read(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  }
  function textOf(html) {
    var d = document.createElement("div");
    d.innerHTML = html;
    return d.textContent;
  }

  function browserLang() {
    var list = (navigator.languages && navigator.languages.length) ? navigator.languages : [navigator.language || ""];
    for (var i = 0; i < list.length; i++) {
      var code = String(list[i] || "").toLowerCase().slice(0, 2);
      if (SUPPORTED.indexOf(code) >= 0) return code;
    }
    return "en";
  }

  function pickLang() {
    var q = null;
    try { q = new URLSearchParams(location.search).get("lang"); } catch (e) {}
    if (SUPPORTED.indexOf(q) >= 0) return q;
    var saved = read("pf_lang");
    if (SUPPORTED.indexOf(saved) >= 0) return saved;
    return browserLang();
  }

  function load(lang) {
    if (cache[lang]) return Promise.resolve(cache[lang]);
    return fetch(root + "assets/i18n/" + lang + ".json")
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (t) { cache[lang] = t; return t; });
  }

  function apply(t) {
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      var v = t[el.getAttribute("data-i18n")];
      if (v == null) return;
      if (el.tagName === "TITLE") document.title = textOf(v);
      else el.innerHTML = v;
    });
    document.querySelectorAll("[data-i18n-attr]").forEach(function (el) {
      el.getAttribute("data-i18n-attr").split(";").forEach(function (pair) {
        var i = pair.indexOf(":");
        var v = t[pair.slice(i + 1)];
        if (v != null) el.setAttribute(pair.slice(0, i), textOf(v));
      });
    });
  }

  /* Links to the other pages of this site keep the language (?lang=pl / ?lang=tr).
     Links with data-href-pl / data-href-tr go to a page pre-rendered in that language instead. */
  function tagLinks(lang) {
    document.querySelectorAll("a[href]").forEach(function (a) {
      var href = a.getAttribute("href");
      if (a.hasAttribute("data-href-pl") || a.hasAttribute("data-href-tr")) {
        if (!a.hasAttribute("data-href-en")) a.setAttribute("data-href-en", href);
        a.setAttribute("href", a.getAttribute("data-href-" + lang) || a.getAttribute("data-href-en"));
        return;
      }
      if (!href || href.charAt(0) === "#" || /^(mailto:|https?:)/i.test(href)) return;
      var url = new URL(href, location.href);
      if (url.href.indexOf(siteRoot) !== 0) return;
      if (lang === "en") url.searchParams.delete("lang");
      else url.searchParams.set("lang", lang);
      var rel = href.split("?")[0].split("#")[0];
      a.setAttribute("href", rel + url.search + url.hash);
    });
  }

  function reflect(lang) {
    document.documentElement.lang = lang;
    document.querySelectorAll(".lang-btn").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-lang") === lang));
    });
    var url = new URL(location.href);
    if (lang === "en") url.searchParams.delete("lang");
    else url.searchParams.set("lang", lang);
    try { history.replaceState(null, "", url); } catch (e) {}
    var canon = document.querySelector("link[rel=canonical]");
    if (canon) {
      var base = canon.getAttribute("data-canonical-base");
      var own = canon.getAttribute("data-canonical-" + lang);
      canon.href = lang === "en" ? base : (own || base + "?lang=" + lang);
    }
    var loc = document.querySelector("meta[property='og:locale']");
    if (loc) loc.setAttribute("content", LOCALES[lang]);
    tagLinks(lang);
  }

  function setLang(lang, remember) {
    if (SUPPORTED.indexOf(lang) < 0) lang = "en";
    if (remember) store("pf_lang", lang);
    return load(lang).then(function (t) { apply(t); reflect(lang); })
      .catch(function () { reflect("en"); });
  }

  function initTheme() {
    var btn = document.getElementById("theme-btn");
    if (!btn) return;
    btn.addEventListener("click", function () {
      var next = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
      document.documentElement.setAttribute("data-theme", next);
      store("pf_theme", next);
    });
    // Follow system changes while the visitor has not chosen a theme here.
    if (window.matchMedia) {
      var mq = matchMedia("(prefers-color-scheme: light)");
      var onChange = function () {
        var saved = read("pf_theme");
        if (saved !== "light" && saved !== "dark") {
          document.documentElement.setAttribute("data-theme", mq.matches ? "light" : "dark");
        }
      };
      if (mq.addEventListener) mq.addEventListener("change", onChange);
    }
  }

  document.querySelectorAll(".nav-link[data-nav='" + page + "']").forEach(function (a) {
    a.setAttribute("aria-current", "page");
  });
  initTheme();
  if (fixedLang) {
    document.querySelectorAll("a.lang-btn[hreflang]").forEach(function (a) {
      a.addEventListener("click", function () { store("pf_lang", a.getAttribute("hreflang")); });
    });
    return;
  }
  document.querySelectorAll(".lang-btn").forEach(function (b) {
    b.addEventListener("click", function () { setLang(b.getAttribute("data-lang"), true); });
  });
  var initial = pickLang();
  if (initial !== "en") setLang(initial, false);
  else reflect("en");
})();
