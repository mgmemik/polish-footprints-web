#!/usr/bin/env python3
"""Builds the static pages from src/, assets/i18n/*.json and the app's content file.

    python3 -I tools/build.py          # writes every page, the pictures of the place pages and sitemap.xml
    python3 -I tools/build.py --check  # only checks (exit 1 if anything is stale or keys differ)

Pages: index.html, privacy/index.html, support/index.html (English baked in, Polish/Turkish swapped in
by assets/site.js), plus the pages pre-rendered in one language by tools/build_pages.py: /pl/, /tr/,
the places lists, one page per place and per walk (see README "Place and walk pages").

Template syntax (src/*.html):
    {{> name}}      partial from src/partials/name.html (ctx["partials"] may map a name to another file)
    {{root}}        relative path to the site root ("" or "../")
    {{page}}        page id (home, privacy, support)
    {{path}}        page path below the site URL ("", "privacy/", "support/")
    {{site}}        absolute site URL (SITE below)
    {{screens}}     the screenshot section, built from assets/img/screens/screens.json
                    (empty while that file is missing or lists no pictures; see README)
    {{t:key}}       English text (HTML allowed) - pair it with data-i18n="key" on the element
    {{a:key}}       English text for an attribute (tags stripped, quotes escaped)
    {{faqld:prefix:n}}  JSON-LD FAQPage built from keys <prefix>1q/<prefix>1a ... <prefix>nq/<prefix>na

The English text is baked into the HTML (what search engines and no-JS visitors see);
assets/site.js swaps in pl.json or tr.json at runtime. All language files must have the same keys.
"""
import html
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://mgmemik.github.io/polish-footprints-web/"
LANGS = ["en", "pl", "tr"]  # en is baked into the HTML
PAGES = [
    # (template, output, page id, path below SITE)
    ("index.html", "index.html", "home", ""),
    ("privacy.html", "privacy/index.html", "privacy", "privacy/"),
    ("support.html", "support/index.html", "support", "support/"),
]
SCREENS = ROOT / "assets" / "img" / "screens" / "screens.json"
CONTENT = ROOT.parent / "app" / "assets" / "data" / "pois.json"  # the app's content: places and walks
# Generated folders: every file in them that the build did not write is removed.
GENERATED_DIRS = ["pl", "en", "tr"]
# sitemap.xml entries of the pages switched by site.js: (path, lastmod, priority).
JS_SITEMAP = [
    ("", "2026-11-11", "1.0"), ("?lang=pl", "2026-11-11", "1.0"), ("?lang=tr", "2026-11-11", "1.0"),
    ("privacy/", "2026-11-14", "0.5"), ("privacy/?lang=pl", "2026-11-14", "0.5"), ("privacy/?lang=tr", "2026-11-14", "0.5"),
    ("support/", "2026-11-11", "0.6"), ("support/?lang=pl", "2026-11-11", "0.6"), ("support/?lang=tr", "2026-11-11", "0.6"),
]
# Keys only used by the screenshot section; not reported as unused while it is off.
SCREEN_KEYS = re.compile(r"^home\.(screensTitle|screensLead|s\d+)$")

# Store rules: these must not appear in titles, meta tags or headings (any language):
# flags, "children" words, superlatives and prices. Regular expressions, matched case-insensitively.
BANNED = [
    r"flag", r"\bflag[ia]?\b", r"bayrak",
    r"\bkids?\b", r"child", r"dzieci", r"dziecko", r"çocuk",
    r"\bbest\b", r"greatest", r"largest", r"biggest", r"ultimate", r"number one", r"#1",
    r"najlepsz", r"największ", r"najwspanialsz", r"\ben (iyi|büyük|güzel)\b",
    r"[$€£₺]", r"\b(usd|eur|zł|pln|tl|try)\b", r"\d[.,]\d\d\b",
]


def load(lang):
    data = json.loads((ROOT / "assets" / "i18n" / f"{lang}.json").read_text("utf-8"))
    data.pop("_comment", None)
    return data


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)


def attr(s):
    return html.escape(html.unescape(strip_tags(s)), quote=True)


def faq_ld(t, prefix, n):
    items = []
    for i in range(1, n + 1):
        q = html.unescape(strip_tags(t[f"{prefix}{i}q"]))
        a = html.unescape(strip_tags(t[f"{prefix}{i}a"]))
        items.append({"@type": "Question", "name": q,
                      "acceptedAnswer": {"@type": "Answer", "text": a}})
    return json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": items},
                      ensure_ascii=False, indent=2)


def screens_section():
    """The screenshot gallery, or "" while there are no screenshots."""
    if not SCREENS.exists():
        return ""
    shots = json.loads(SCREENS.read_text("utf-8"))
    if not shots:
        return ""
    figures = []
    for s in shots:
        img = ROOT / "assets" / "img" / "screens" / s["file"]
        if not img.exists():
            raise SystemExit(f"screens.json lists a missing file: {img}")
        figures.append(
            '          <figure class="shot">\n'
            f'            <img src="{{{{root}}}}assets/img/screens/{s["file"]}" width="{s["width"]}" height="{s["height"]}"'
            f' loading="lazy" alt="{{{{a:{s["key"]}}}}}" data-i18n-attr="alt:{s["key"]}" />\n'
            f'            <figcaption data-i18n="{s["key"]}">{{{{t:{s["key"]}}}}}</figcaption>\n'
            "          </figure>")
    return (ROOT / "src" / "partials" / "screens.html").read_text("utf-8").replace(
        "{{figures}}", "\n".join(figures))


def store_url(ct):
    return ("https://apps.apple.com/app/apple-store/id6833051676?pt=127856308&ct=" + ct + "&mt=8").replace("&", "&amp;")


def js_ctx(dst, page, path):
    """Context of the pages whose language is switched by assets/site.js (see src/partials/head.html)."""
    root = "../" * dst.count("/")
    ctx = {
        "root": root, "page": page, "path": path, "site": SITE,
        "html_lang": "en", "html_attrs": "",
        "canonical": SITE + path, "canonical_attrs": f' data-canonical-base="{SITE}{path}"',
        "alt_en": SITE + path, "alt_pl": SITE + path + "?lang=pl", "alt_tr": SITE + path + "?lang=tr",
        "og_type": "website", "og_image": SITE + "assets/img/og-image.png", "og_image_w": "1200", "og_image_h": "630",
        "og_locale": "en_GB", "og_locale_alt1": "pl_PL", "og_locale_alt2": "tr_TR",
        "home_href": root + "./", "places_href": root + "en/places/",
        "places_attrs": f' data-href-pl="{root}pl/miejsca/" data-href-tr="{root}tr/yerler/"',
        "privacy_href": root + "privacy/", "support_href": root + "support/",
        "script_lang": "", "store_url": store_url("web-home"),
        "partials": {"langswitch": "lang-buttons"},
        "walks_anchor": "#walks",
        "walks_attrs": f' data-href-pl="{root}pl/miejsca/#spacery" data-href-tr="{root}tr/yerler/#yuruyusler"',
    }
    if page == "home":
        # The home page also exists pre-rendered in Polish and Turkish (/pl/, /tr/): point search engines
        # there, and let site.js use them as the canonical URL of /?lang=pl and /?lang=tr.
        ctx["alt_pl"], ctx["alt_tr"] = SITE + "pl/", SITE + "tr/"
        ctx["canonical_attrs"] += f' data-canonical-pl="{SITE}pl/" data-canonical-tr="{SITE}tr/"'
        routes = json.loads(CONTENT.read_text("utf-8"))["routes"]
        for i, r in enumerate(routes, 1):
            ctx[f"walk_link_{i}"] = (f'href="{root}en/walks/{r["id"]}/" data-href-pl="{root}pl/spacery/{r["id"]}/"'
                                     f' data-href-tr="{root}tr/yuruyusler/{r["id"]}/"')
    return ctx


def render(text, t, ctx, used):
    def partial(m):
        name = ctx.get("partials", {}).get(m.group(1), m.group(1))
        return render((ROOT / "src" / "partials" / f"{name}.html").read_text("utf-8"), t, ctx, used)

    text = re.sub(r"\{\{>\s*([\w-]+)\s*\}\}", partial, text)
    text = text.replace("{{screens}}", screens_section())

    def var(m):
        kind, key = m.group(1), m.group(2)
        if kind is None:
            return ctx[key]
        if kind == "faqld":
            prefix, n = key.rsplit(":", 1)
            for i in range(1, int(n) + 1):
                used.update({f"{prefix}{i}q", f"{prefix}{i}a"})
            return faq_ld(t, prefix, int(n))
        used.add(key)
        if key not in t:
            raise SystemExit(f"missing key in en.json: {key}")
        return t[key] if kind == "t" else attr(t[key])

    return re.sub(r"\{\{(?:(t|a|faqld):)?([\w.:-]+)\}\}", var, text)


def check_banned(where, zones):
    bad = []
    for z in zones:
        low = html.unescape(strip_tags(z)).lower()
        for w in BANNED:
            if re.search(w, low):
                bad.append(f"{where}: /{w}/ in title/meta/heading: {strip_tags(z).strip()[:80]}")
    return bad


def zones_of(out):
    zones = re.findall(r"<title[^>]*>(.*?)</title>", out, re.S)
    zones += re.findall(r'<meta[^>]+content="([^"]*)"', out)
    zones += re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", out, re.S)
    zones += re.findall(r"<summary[^>]*>(.*?)</summary>", out, re.S)
    return zones


def sitemap(entries):
    """sitemap.xml: the site.js pages (kept as they were) plus every generated page, with hreflang."""
    def url(loc, lastmod, priority, alts):
        lines = ["  <url>", f"    <loc>{SITE}{loc}</loc>", f"    <lastmod>{lastmod}</lastmod>",
                 f"    <priority>{priority}</priority>"]
        for lang in ("en", "pl", "tr"):
            lines.append(f'    <xhtml:link rel="alternate" hreflang="{lang}" href="{SITE}{alts[lang]}"/>')
        lines.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE}{alts["en"]}"/>')
        return "\n".join(lines + ["  </url>"])

    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for loc, lastmod, priority in JS_SITEMAP:
        base = loc.split("?")[0]
        if base == "":
            alts = {"en": "", "pl": "pl/", "tr": "tr/"}
        else:
            alts = {"en": base, "pl": base + "?lang=pl", "tr": base + "?lang=tr"}
        parts.append(url(loc, lastmod, priority, alts))
    for e in entries:
        parts.append(url(e["loc"], e["lastmod"], e["priority"], {k: e["alts"][k] for k in ("en", "pl", "tr")}))
    return "\n".join(parts + ["</urlset>"]) + "\n"


def main():
    check_only = "--check" in sys.argv
    texts = {lang: load(lang) for lang in LANGS}
    en = texts["en"]
    problems = []
    for lang in LANGS[1:]:
        other = texts[lang]
        problems += [f"only in en.json: {k} (missing in {lang}.json)" for k in sorted(set(en) - set(other))]
        problems += [f"only in {lang}.json: {k}" for k in sorted(set(other) - set(en))]
        problems += [f"{lang}.json: empty value for {k}" for k, v in other.items() if not str(v).strip() and str(en.get(k, "")).strip()]
    used = set()
    stale = []
    title_keys = set()
    outputs = {}
    for src, dst, page, path in PAGES:
        ctx = js_ctx(dst, page, path)
        out = render((ROOT / "src" / src).read_text("utf-8"), en, ctx, used)
        out = "<!-- Generated by tools/build.py from src/" + src + " and assets/i18n/en.json. Do not edit. -->\n" + out
        problems += check_banned(f"{page} (en)", zones_of(out))
        # every data-i18n key must exist; remember the keys used in titles/meta/headings
        for m in re.finditer(r'<(title|h[1-3]|summary)[^>]*data-i18n="([^"]+)"', out):
            title_keys.add(m.group(2))
        for k in re.findall(r'<meta[^>]+data-i18n-attr="content:([^"]+)"', out):
            title_keys.add(k)
        for k in re.findall(r'data-i18n(?:-attr)?="([^"]+)"', out):
            for part in k.split(";"):
                key = part.split(":")[-1]
                if key not in en:
                    problems.append(f"{page}: data-i18n key not in en.json: {key}")
                used.add(key)
        outputs[dst] = out
    # pages pre-rendered in one language (places, walks, /pl/, /tr/) and the sitemap
    spec = importlib.util.spec_from_file_location("build_pages", ROOT / "tools" / "build_pages.py")
    build_pages = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build_pages)
    pages, page_problems, notes, entries = build_pages.generate(sys.modules[__name__], texts, used, check_only)
    problems += page_problems
    outputs.update(pages)
    outputs["sitemap.xml"] = sitemap(entries)
    for dst, out in sorted(outputs.items()):
        target = ROOT / dst
        if check_only:
            if not target.exists() or target.read_text("utf-8") != out:
                stale.append(dst)
        elif not target.exists() or target.read_text("utf-8") != out:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(out, "utf-8")
            print("wrote", dst)
    for d in GENERATED_DIRS:
        for f in sorted((ROOT / d).rglob("*")) if (ROOT / d).exists() else []:
            relp = f.relative_to(ROOT).as_posix()
            if f.is_file() and relp not in outputs:
                if check_only:
                    stale.append(f"{relp} (not generated any more)")
                else:
                    f.unlink()
                    print("removed", relp)
        if not check_only and (ROOT / d).exists():
            for sub in sorted((ROOT / d).rglob("*"), reverse=True):
                if sub.is_dir() and not any(sub.iterdir()):
                    sub.rmdir()
    for n in notes:
        print("NOTE (content wording in a title/heading, check it is fine for the store rules):", n)
    # the other languages: same banned-word check on what they put into titles/meta/headings
    for lang in LANGS[1:]:
        t = texts[lang]
        problems += check_banned(lang, [t[k] for k in sorted(title_keys) if k in t])
    screens_on = bool(screens_section())
    unused = sorted(k for k in set(en) - used if screens_on or not SCREEN_KEYS.match(k))
    if unused:
        problems += [f"unused key: {k}" for k in unused]
    for s in stale:
        problems.append(f"stale (run tools/build.py): {s}")
    for p in problems:
        print("PROBLEM:", p)
    if problems:
        sys.exit(1)
    counts = {}
    for dst in outputs:
        if dst.endswith("index.html") and dst.split("/")[0] in GENERATED_DIRS and "noindex" not in outputs[dst]:
            counts[dst.split("/")[0]] = counts.get(dst.split("/")[0], 0) + 1
    print("ok:", len(en), "keys,", "/".join(LANGS), "in sync; screenshots", "on" if screens_on else "off",
          "; generated pages:", ", ".join(f"{k} {v}" for k, v in sorted(counts.items())),
          "; sitemap:", len(entries) + len(JS_SITEMAP), "URLs")


if __name__ == "__main__":
    main()
