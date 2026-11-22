#!/usr/bin/env python3
"""Checks the built pages: every local href/src/srcset target exists (and #fragments point at an id
on the target page), tags are balanced, images have alt text, every JSON-LD block parses as JSON,
pre-rendered pages have <html lang>, a canonical URL and hreflang links, and lists the external links.

    python3 -I tools/check_links.py        # all pages (the site.js pages and every generated page)
    python3 -I tools/check_links.py -v     # also print every external link
"""
import json
import os
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://mgmemik.github.io/polish-footprints-web/"
SKIP = {"_screens", "tools", "src", ".git", "node_modules"}
VOID = {"meta", "link", "img", "br", "input", "source", "hr"}


def all_pages():
    out = []
    for f in sorted(ROOT.rglob("index.html")):
        parts = f.relative_to(ROOT).parts
        if parts[0] in SKIP:
            continue
        out.append(f.relative_to(ROOT).as_posix())
    return out


class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.stack, self.errors, self.ids = [], [], [], []
        self.ld, self.in_ld, self.buf = [], False, []
        self.html_lang, self.canonical, self.hreflang, self.noindex = None, None, {}, False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag not in VOID:
            self.stack.append(tag)
        if tag == "html":
            self.html_lang = a.get("lang")
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href")
        if tag == "link" and a.get("rel") == "alternate" and a.get("hreflang"):
            self.hreflang[a["hreflang"]] = a.get("href")
        if tag == "meta" and a.get("name") == "robots" and "noindex" in (a.get("content") or ""):
            self.noindex = True
        if tag == "script" and a.get("type") == "application/ld+json":
            self.in_ld, self.buf = True, []
        for k in ("href", "src"):
            if a.get(k) and not (tag == "link" and a.get("rel") in ("canonical", "alternate")):
                self.refs.append(a[k])
        if a.get("srcset"):
            self.refs += [p.strip().split()[0] for p in a["srcset"].split(",")]
        if tag == "img" and "alt" not in a:
            self.errors.append(f"img without alt: {a.get('src')}")
        if a.get("id"):
            self.ids.append(a["id"])

    def handle_data(self, data):
        if self.in_ld:
            self.buf.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.in_ld:
            self.ld.append("".join(self.buf))
            self.in_ld = False
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"unbalanced </{tag}> (open: {self.stack[-3:]})")
        else:
            self.stack.pop()


def main():
    verbose = "-v" in sys.argv
    pages = all_pages()
    parsed = {}
    for page in pages:
        p = P()
        p.feed((ROOT / page).read_text("utf-8"))
        parsed[page] = p
    bad, external, ld_count = [], set(), 0
    for page, p in parsed.items():
        path = ROOT / page
        bad += [f"{page}: {e}" for e in p.errors]
        if p.stack:
            bad.append(f"{page}: unclosed {p.stack}")
        if len(p.ids) != len(set(p.ids)):
            bad.append(f"{page}: duplicate ids")
        for block in p.ld:
            ld_count += 1
            try:
                json.loads(block)
            except ValueError as e:
                bad.append(f"{page}: JSON-LD does not parse: {e}")
        if not p.noindex:
            folder = page[: -len("index.html")]
            if not p.html_lang:
                bad.append(f"{page}: no <html lang>")
            if not p.canonical:
                bad.append(f"{page}: no canonical link")
            elif "?" not in p.canonical and p.canonical != SITE + folder:
                bad.append(f"{page}: canonical {p.canonical} is not {SITE + folder}")
            if set(p.hreflang) != {"en", "pl", "tr", "x-default"}:
                bad.append(f"{page}: hreflang links {sorted(p.hreflang)}")
            for lang, href in p.hreflang.items():
                if href.startswith(SITE) and "?" not in href:
                    target = ROOT / href[len(SITE):] / "index.html"
                    if not target.exists():
                        bad.append(f"{page}: hreflang {lang} points at a missing page {href}")
        for ref in p.refs:
            if ref.startswith(("http://", "https://")):
                external.add(ref)
                continue
            if ref.startswith("mailto:"):
                continue
            parts = urlsplit(ref)
            if ref.startswith("#"):
                target, frag = path, parts.fragment
            else:
                target = Path(os.path.normpath(path.parent / unquote(parts.path)))
                if parts.path.endswith("/") or target.is_dir():
                    target = target / "index.html"
                frag = parts.fragment
                if not target.exists():
                    bad.append(f"{page}: missing {ref}")
                    continue
            if frag and target.name == "index.html":
                key = target.relative_to(ROOT).as_posix()
                ids = parsed[key].ids if key in parsed else []
                if frag not in ids and frag != "main":
                    bad.append(f"{page}: {ref} - no id '{frag}' on the target page")
                elif frag == "main" and "main" not in ids:
                    bad.append(f"{page}: skip link target #main missing")
    print(f"{len(pages)} pages, {ld_count} JSON-LD blocks, {len(external)} external links")
    if verbose:
        for e in sorted(external):
            print("  ", e)
    for b in bad:
        print("PROBLEM:", b)
    print("ok" if not bad else f"{len(bad)} problems")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
