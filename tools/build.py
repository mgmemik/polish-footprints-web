#!/usr/bin/env python3
"""Builds the static pages from src/ and assets/i18n/en.json.

    python3 tools/build.py          # writes index.html, privacy/index.html, support/index.html
    python3 tools/build.py --check  # only checks (exit 1 if the built pages are stale or keys differ)

Template syntax (src/*.html):
    {{> name}}      partial from src/partials/name.html
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
            f'            <img src="assets/img/screens/{s["file"]}" width="{s["width"]}" height="{s["height"]}"'
            f' loading="lazy" alt="{{{{a:{s["key"]}}}}}" data-i18n-attr="alt:{s["key"]}" />\n'
            f'            <figcaption data-i18n="{s["key"]}">{{{{t:{s["key"]}}}}}</figcaption>\n'
            "          </figure>")
    return (ROOT / "src" / "partials" / "screens.html").read_text("utf-8").replace(
        "{{figures}}", "\n".join(figures))


def render(text, t, ctx, used):
    def partial(m):
        return render((ROOT / "src" / "partials" / f"{m.group(1)}.html").read_text("utf-8"), t, ctx, used)

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


def main():
    check_only = "--check" in sys.argv
    texts = {lang: load(lang) for lang in LANGS}
    en = texts["en"]
    problems = []
    for lang in LANGS[1:]:
        other = texts[lang]
        problems += [f"only in en.json: {k} (missing in {lang}.json)" for k in sorted(set(en) - set(other))]
        problems += [f"only in {lang}.json: {k}" for k in sorted(set(other) - set(en))]
        problems += [f"{lang}.json: empty value for {k}" for k, v in other.items() if not str(v).strip()]
    used = set()
    stale = []
    title_keys = set()
    for src, dst, page, path in PAGES:
        ctx = {"root": "../" if "/" in dst else "", "page": page, "path": path, "site": SITE}
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
        target = ROOT / dst
        if check_only:
            if not target.exists() or target.read_text("utf-8") != out:
                stale.append(dst)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(out, "utf-8")
            print("wrote", dst)
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
    print("ok:", len(en), "keys,", "/".join(LANGS), "in sync; screenshots", "on" if screens_on else "off")


if __name__ == "__main__":
    main()
