"""Static place and walk pages, the language home pages /pl/ and /tr/, and sitemap.xml.

Called by tools/build.py (do not run it on its own). Everything comes from the app's content file
(../app/assets/data/pois.json), the UI texts in src/pages-i18n.json and the site's own
assets/i18n/<lang>.json (header, footer, store button), rendered into src/page.html with the
shared partials. Output is deterministic: the same inputs give byte-identical pages.

URL scheme (folders with index.html):
    /pl/  /tr/                         home page with Polish / Turkish baked in (English stays at /)
    /pl/miejsca/  /en/places/  /tr/yerler/                 all places by theme, plus the walks
    /pl/miejsca/<id>/  /en/places/<id>/  /tr/yerler/<id>/  one page per place
    /pl/spacery/<id>/  /en/walks/<id>/  /tr/yuruyusler/<id>/  one page per walk
"""
import hashlib
import html
import json
import math
import posixpath
import re
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

# ---------------------------------------------------------------------------------------------
# Settings the owner may change
# ---------------------------------------------------------------------------------------------

# The free/premium cut for places marked "premium" in pois.json (places on the free walks are
# never cut). story_fraction: how much of the story is shown, cut at the nearest paragraph or
# sentence end (1.0 = the full story, 0 = no story text, only the teaser and the call to action).
# images: how many of the place's pictures are shown (None = all).
PREMIUM_CUT = {"story_fraction": 0.38, "images": 1}

# App Store link with campaign parameters (App Store Connect > Analytics > Sources > Campaigns).
APP_ID = "6833051676"
PROVIDER_TOKEN = "127856308"
STORE_URL = "https://apps.apple.com/app/apple-store/id{app}?pt={pt}&ct={ct}&mt=8"

# <lastmod> of the generated pages in sitemap.xml; bump it when the pages or the content change.
PAGES_LASTMOD = "2026-11-22"

# Pictures: copied from the app bundle, long edge <= IMAGE_EDGE px, WebP.
IMAGE_EDGE = 960
IMAGE_QUALITY = 72

NEARBY_COUNT = 4

# ---------------------------------------------------------------------------------------------

LANGS = ["pl", "en", "tr"]
SEG = {"pl": ("miejsca", "spacery"), "en": ("places", "walks"), "tr": ("yerler", "yuruyusler")}
WALKS_ANCHOR = {"pl": "spacery", "en": "walks", "tr": "yuruyusler"}
LOCALE = {"pl": "pl_PL", "en": "en_GB", "tr": "tr_TR"}
CITY = {"pl": "Stambuł", "en": "Istanbul", "tr": "İstanbul"}
LICENCES = {
    "CC0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "CC BY 3.0": "https://creativecommons.org/licenses/by/3.0/",
    "CC BY 3.0 pl": "https://creativecommons.org/licenses/by/3.0/pl/deed.en",
    "CC BY 4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC BY-SA 3.0": "https://creativecommons.org/licenses/by-sa/3.0/",
    "CC BY-SA 4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
}
# Words before a full stop that do not end a sentence (from the app's sentences.dart).
ABBREVIATIONS = set("st mr mrs ms dr rev capt col gen lt sgt maj no vol c ca cf vs etc hms jr sr mt ft hz "
                    "prof św ks o ok tzw płk kpt abp bp r w np in tj ul im ur zm pl".split())
SENTENCE_END = re.compile(r"""[.!?]["'”’)\]]?\s+(?=["'“‘„(]?[A-ZÇĞİÖŞÜÂÎÛĄĆĘŁŃÓŚŹŻ0-9])""")


def esc(s):
    return html.escape(s, quote=False)


def att(s):
    return html.escape(s, quote=False).replace('"', "&quot;")


def home_path(lang):
    return "" if lang == "en" else f"{lang}/"


def list_path(lang):
    return f"{lang}/{SEG[lang][0]}/"


def place_path(lang, pid):
    return f"{lang}/{SEG[lang][0]}/{pid}/"


def walk_path(lang, wid):
    return f"{lang}/{SEG[lang][1]}/{wid}/"


def rel(src, dst):
    """Relative link from page folder src to page folder dst (both like "pl/miejsca/x/" or "")."""
    r = posixpath.relpath(dst.rstrip("/") or ".", src.rstrip("/") or ".")
    return "./" if r == "." else r + "/"


def store_url(ct):
    return STORE_URL.format(app=APP_ID, pt=PROVIDER_TOKEN, ct=quote(ct[:40], safe="-"))


def ld(obj):
    text = json.dumps(obj, ensure_ascii=False, indent=2).replace("</", "<\\/")
    return f'    <script type="application/ld+json">\n{text}\n    </script>'


class Strings:
    """src/pages-i18n.json: {key: {en, pl, tr}}; plural entries are lists."""

    def __init__(self, path):
        data = json.loads(path.read_text("utf-8"))
        data.pop("_comment", None)
        self.data = data
        self.used = set()

    def problems(self):
        out = []
        for k, v in self.data.items():
            for lang in LANGS:
                val = v.get(lang)
                if isinstance(val, list):
                    want = 3 if lang == "pl" else 2
                    if len(val) != want or not all(x.strip() for x in val):
                        out.append(f"pages-i18n.json: {k}.{lang} needs {want} plural forms")
                elif not (val or "").strip():
                    out.append(f"pages-i18n.json: missing {k}.{lang}")
        out += [f"pages-i18n.json: unused key {k}" for k in sorted(set(self.data) - self.used)]
        return out

    def get(self, lang, key, **kw):
        self.used.add(key)
        s = self.data[key][lang]
        for k, v in kw.items():
            s = s.replace("{" + k + "}", str(v))
        return s

    def count(self, lang, key, n):
        self.used.add(key)
        forms = self.data[key][lang]
        if lang == "pl":
            if n == 1:
                f = forms[0]
            elif n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
                f = forms[1]
            else:
                f = forms[2]
        else:
            f = forms[0] if n == 1 else forms[1]
        return f.replace("{n}", str(n))


def duration(S, lang, minutes):
    S.used.update({"time.min", "time.h", "time.hmin"})
    h, m = divmod(int(minutes), 60)
    if h and m:
        d = S.get(lang, "time.hmin", h=h, m=m)
    elif h:
        d = S.get(lang, "time.h", h=h)
    else:
        d = S.get(lang, "time.min", m=m)
    return S.get(lang, "time.about", d=d)


def distance_m(a, b):
    r = 6371000.0
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dp, dl = p2 - p1, math.radians(b["lng"] - a["lng"])
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(x))


def fmt_distance(lang, m):
    if m < 950:
        return f"{max(50, int(round(m / 50.0)) * 50)} m"
    km = m / 1000.0
    s = f"{km:.0f}" if km >= 10 else f"{km:.1f}"
    return (s if lang == "en" else s.replace(".", ",")) + " km"


def period_text(p):
    p = p.strip()
    p = re.sub(r"(?<=\d)-$", "–", p)  # "1842-" -> "1842–"
    return p.replace("-", "–")


def paragraphs(text):
    return [p.strip() for p in text.strip().split("\n\n") if p.strip()]


def para_html(text, indent="          "):
    return "\n".join(f"{indent}<p>{esc(p).replace(chr(10), '<br />')}</p>" for p in paragraphs(text))


def cut_story(text, fraction):
    """The opening of a story: about `fraction` of it, ending at a paragraph or sentence end."""
    text = text.strip()
    if fraction >= 1:
        return text, False
    if fraction <= 0:
        return "", True
    total = len(text)
    target = total * fraction
    cands = []  # (score, position)
    for m in re.finditer(r"\n\n", text):
        cands.append((abs(m.start() - target) - 0.05 * total, m.start()))
    for m in SENTENCE_END.finditer(text):
        before = text[:m.start() + 1]
        word = re.search(r"([^\W\d_]+)[.!?][\"'”’)\]]?$", before)
        word = word.group(1) if word else ""
        if word.lower() in ABBREVIATIONS:
            continue
        if len(word) == 1 and word.isupper():
            continue  # an initial
        if re.fullmatch(r"[IVXL]+", word):
            continue  # Roman ordinal ("II. Mehmed")
        nxt = text[m.end():m.end() + 1]
        if not word and nxt.isdigit():
            continue  # "1854. 1855"
        if not word and re.match(r"[IVXL]+\b", text[m.end():]):
            continue  # "lat 60. XIX wieku"
        pos = m.start() + 1 + (1 if text[m.start() + 1:m.start() + 2] in "\"'”’)]" else 0)
        cands.append((abs(pos - target), pos))
    cands = [c for c in cands if 0.15 * total <= c[1] <= 0.7 * total]
    if not cands:
        return paragraphs(text)[0], True
    pos = min(cands)[1]
    return text[:pos].strip(), True


def pretty_url(u):
    s = urlsplit(u)
    host = s.netloc[4:] if s.netloc.startswith("www.") else s.netloc
    path = unquote(s.path).rstrip("/")
    t = host + path
    return t if len(t) <= 64 else t[:61] + "…"


# ---------------------------------------------------------------------------------------------
# Pictures
# ---------------------------------------------------------------------------------------------

class Images:
    def __init__(self, root, app_dir, check_only):
        self.root = root
        self.out_dir = root / "assets" / "img" / "places"
        self.index_path = root / "src" / "places-images.json"
        self.index = json.loads(self.index_path.read_text("utf-8")) if self.index_path.exists() else {}
        manifest = app_dir / "assets" / "images" / "poi" / "manifest.json"
        self.manifest = json.loads(manifest.read_text("utf-8"))["images"]
        self.app_dir = app_dir
        self.check_only = check_only
        self.wanted = {}
        self.stale = []

    def get(self, pid, n, url):
        """(published path below the site root, width, height) of picture n of place pid."""
        entry = self.manifest.get(url)
        if not entry:
            raise SystemExit(f"picture not in the app bundle (run app/tools/fetch_images.py): {url}")
        name = f"{pid}-{n}.webp"
        src = self.app_dir / entry["asset"]
        sha = hashlib.sha1(src.read_bytes()).hexdigest()
        key = f"{sha}:{IMAGE_EDGE}:{IMAGE_QUALITY}"
        known = self.index.get(name)
        target = self.out_dir / name
        if not known or known["key"] != key or not target.exists():
            if self.check_only:
                self.stale.append(f"assets/img/places/{name}")
                w, h = entry["width"], entry["height"]
            else:
                w, h = self._convert(src, target)
            known = {"key": key, "width": w, "height": h}
        self.wanted[name] = known
        return f"assets/img/places/{name}", known["width"], known["height"]

    def _convert(self, src, target):
        from PIL import Image  # only needed when a picture is (re)made

        target.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(src) as im:
            im = im.convert("RGB")
            im.thumbnail((IMAGE_EDGE, IMAGE_EDGE), Image.LANCZOS)
            im.save(target, "WEBP", quality=IMAGE_QUALITY, method=6)
            print("picture", target.name, im.size)
            return im.size

    def finish(self):
        problems = list(self.stale)
        for f in sorted(self.out_dir.glob("*")) if self.out_dir.exists() else []:
            if f.name not in self.wanted:
                if self.check_only:
                    problems.append(f"stale picture: {f.name}")
                else:
                    f.unlink()
                    print("removed", f.relative_to(self.root))
        new_index = {k: self.wanted[k] for k in sorted(self.wanted)}
        text = json.dumps({**new_index}, indent=1) + "\n"
        if self.check_only:
            if not self.index_path.exists() or self.index_path.read_text("utf-8") != text:
                problems.append("stale: src/places-images.json")
        else:
            self.index_path.write_text(text, "utf-8")
        return problems


# ---------------------------------------------------------------------------------------------
# Page context and shell
# ---------------------------------------------------------------------------------------------

def static_ctx(B, lang, path, page, alts, og_type="website", og_image=None, ct="web"):
    """Context for a page pre-rendered in one language (see src/partials/head.html)."""
    root = "../" * path.count("/")
    others = [LOCALE[x] for x in ("en", "pl", "tr") if x != lang]
    img = og_image or (B.SITE + "assets/img/og-image.png", 1200, 630)
    ctx = {
        "root": root, "page": page, "path": path, "site": B.SITE,
        "html_lang": lang, "html_attrs": " data-fixed-lang",
        "canonical": B.SITE + path, "canonical_attrs": "",
        "alt_en": B.SITE + alts["en"], "alt_pl": B.SITE + alts["pl"], "alt_tr": B.SITE + alts["tr"],
        "og_type": og_type, "og_image": img[0], "og_image_w": str(img[1]), "og_image_h": str(img[2]),
        "og_locale": LOCALE[lang], "og_locale_alt1": others[0], "og_locale_alt2": others[1],
        "home_href": rel(path, home_path(lang)), "places_href": rel(path, list_path(lang)), "places_attrs": "",
        "privacy_href": root + "privacy/" + ("" if lang == "en" else f"?lang={lang}"),
        "support_href": root + "support/" + ("" if lang == "en" else f"?lang={lang}"),
        "script_lang": f' data-lang="{lang}"', "store_url": att(store_url(ct)),
        "partials": {"langswitch": "lang-links"},
    }
    for x in LANGS:
        ctx[f"lang_href_{x}"] = rel(path, alts[x])
        ctx[f"lang_cur_{x}"] = ' aria-current="page"' if x == lang else ""
    return ctx


def strip_i18n(out):
    """Pre-rendered pages do not need the runtime translation hooks."""
    return re.sub(r' data-i18n(?:-attr)?="[^"]*"', "", out)


def crumbs(S, lang, path, items):
    """items: [(name, page path or None)]; returns (visible HTML, JSON-LD dict)."""
    lis, ld_items = [], []
    for i, (name, target) in enumerate(items, 1):
        if target is None:
            lis.append(f'            <li aria-current="page">{esc(name)}</li>')
            url = None
        else:
            lis.append(f'            <li><a href="{rel(path, target)}">{esc(name)}</a></li>')
            url = target
        ld_items.append({"@type": "ListItem", "position": i, "name": name,
                         "item": SITE_HOLDER + (url if url is not None else path)})
    nav = (f'        <nav class="crumbs" aria-label="{att(S.get(lang, "crumb.label"))}">\n'
           f'          <ol>\n' + "\n".join(lis) + "\n          </ol>\n        </nav>")
    return nav, {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": ld_items}


SITE_HOLDER = "\x00SITE\x00"  # replaced by the site URL in JSON-LD (keeps crumbs() free of B)


def fix_site(obj, site):
    if isinstance(obj, dict):
        return {k: fix_site(v, site) for k, v in obj.items()}
    if isinstance(obj, list):
        return [fix_site(v, site) for v in obj]
    if isinstance(obj, str):
        return obj.replace(SITE_HOLDER, site)
    return obj


def cta_block(B, t, ctx, used, title, body, cls="cta-card folio page-cta"):
    stores = B.render((B.ROOT / "src" / "partials" / "stores.html").read_text("utf-8"), t, ctx, used)
    icon = "" if "story-cta" in cls else (
        f'          <img src="{ctx["root"]}assets/img/icon-180.png" width="72" height="72" alt="" class="cta-icon" loading="lazy" />\n')
    return (f'        <aside class="{cls}">\n'
            f'{icon}'
            f'          <h2>{esc(title)}</h2>\n'
            f'          <p>{esc(body)}</p>\n'
            f'{stores}'
            f'        </aside>')


def shell(B, t, ctx, used, title, desc, jsonld, body):
    ctx = dict(ctx, title=att(title), desc=att(desc), jsonld="\n".join(ld(fix_site(x, B.SITE)) for x in jsonld),
               body=body)
    out = B.render((B.ROOT / "src" / "page.html").read_text("utf-8"), t, ctx, used)
    return strip_i18n(out)


# ---------------------------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------------------------

def generate(B, texts, used, check_only):
    """Returns ({output path: html}, [problems], [notes], sitemap entries)."""
    content_path = B.ROOT.parent / "app" / "assets" / "data" / "pois.json"
    content = json.loads(content_path.read_text("utf-8"))
    S = Strings(B.ROOT / "src" / "pages-i18n.json")
    images = Images(B.ROOT, B.ROOT.parent / "app", check_only)
    pois = content["pois"]
    by_id = {p["id"]: p for p in pois}
    cats = {c["id"]: c for c in content["categories"]}
    routes = content["routes"]
    outputs, problems, notes, sitemap = {}, [], [], []

    for r in routes:
        for pid in r["poiIds"]:
            if pid not in by_id:
                problems.append(f"walk {r['id']} lists an unknown place {pid}")

    def alts_for(fn, *a):
        return {x: fn(x, *a) for x in LANGS}

    def add(path, out, alts, priority):
        outputs[path + "index.html"] = out
        sitemap.append({"loc": path, "lastmod": PAGES_LASTMOD, "priority": priority, "alts": alts})
        for b in dict.fromkeys(B.check_banned("generated", B.zones_of(out))):
            notes.append(f"{path}: {b}")

    # pictures per place
    pics = {}
    for p in pois:
        imgs = p["images"]
        limit = PREMIUM_CUT["images"] if p["premium"] else None
        if limit is not None:
            imgs = imgs[:limit]
        pics[p["id"]] = [(img, *images.get(p["id"], n, img["url"])) for n, img in enumerate(imgs, 1)]

    walks_of = {p["id"]: [] for p in pois}
    for r in routes:
        for i, pid in enumerate(r["poiIds"], 1):
            walks_of.setdefault(pid, []).append((r, i))

    for lang in LANGS:
        t = texts[lang]

        # ---------------- place pages ----------------
        for p in pois:
            pid = p["id"]
            path = place_path(lang, pid)
            alts = alts_for(place_path, pid)
            name, teaser = p["name"][lang], p["teaser"][lang]
            cat = cats[p["category"]]
            plist = pics[pid]
            og = (B.SITE + plist[0][1], plist[0][2], plist[0][3]) if plist else None
            ctx = static_ctx(B, lang, path, "places", alts, "article", og, f"web-{lang}-{pid}")
            crumb_html, crumb_ld = crumbs(S, lang, path, [
                (S.get(lang, "crumb.home"), home_path(lang)),
                (S.get(lang, "crumb.places"), list_path(lang)),
                (name, None)])

            def figure(item, eager):
                img, src, w, h = item
                lazy = "" if eager else ' loading="lazy"'
                lic = img["license"]
                lic_html = f'<a href="{att(LICENCES[lic])}" rel="noopener license">{esc(lic)}</a>' if lic in LICENCES else esc(lic)
                return (f'          <figure class="place-figure">\n'
                        f'            <img src="{ctx["root"]}{src}" width="{w}" height="{h}" alt="{att(name)}"'
                        f'{lazy} decoding="async" />\n'
                        f'            <figcaption>{esc(img["credit"])} · {lic_html} · '
                        f'<a href="{att(img["source"])}" rel="noopener">{esc(S.get(lang, "place.pictureSource"))}</a></figcaption>\n'
                        f'          </figure>')

            story = p["story"][lang]
            premium = p["premium"]
            if premium:
                shown, was_cut = cut_story(story, PREMIUM_CUT["story_fraction"])
            else:
                shown, was_cut = story, False
            facts = [
                (S.get(lang, "place.theme"), f'<a href="{rel(path, list_path(lang))}#{cat["id"]}">{esc(cat["name"][lang])}</a>'),
                (S.get(lang, "place.district"), esc(p["district"])),
                (S.get(lang, "place.period"), esc(period_text(p["period"]))),
                (S.get(lang, "place.access"), esc(S.get(lang, "visitable." + p["visitable"]))),
            ]
            parts = [crumb_html, '        <article class="place">',
                     '          <header class="page-head">',
                     f'            <p class="eyebrow cat-label" style="--cat:{cat["color"]}">{esc(cat["name"][lang])}</p>',
                     f'            <h1>{esc(name)}</h1>',
                     '            <div class="tile-rule" aria-hidden="true"><i></i><i></i><i></i></div>',
                     f'            <p class="lead">{esc(teaser)}</p>',
                     '          </header>']
            if plist:
                parts.append(figure(plist[0], True))
            parts.append(f'          <dl class="facts place-facts" aria-label="{att(S.get(lang, "place.facts"))}">')
            parts += [f'            <div><dt>{esc(k)}</dt><dd>{v}</dd></div>' for k, v in facts]
            parts.append('          </dl>')
            parts.append('          <section class="art-section story" aria-labelledby="story-title">')
            parts.append(f'          <h2 id="story-title">{esc(S.get(lang, "place.story"))}</h2>')
            if shown:
                parts.append(para_html(shown))
            parts.append('          </section>')
            if was_cut:
                parts.append(cta_block(B, t, ctx, used, S.get(lang, "place.ctaTitle"), S.get(lang, "place.ctaBody"),
                                       "card story-cta"))
            for item in plist[1:]:
                parts.append(figure(item, False))
            parts += ['          <section class="art-section" aria-labelledby="visit-title">',
                      f'          <h2 id="visit-title">{esc(S.get(lang, "place.visit"))}</h2>',
                      para_html(p["visit"][lang]),
                      '          </section>']
            if p["people"]:
                parts += ['          <section class="art-section" aria-labelledby="people-title">',
                          f'          <h2 id="people-title">{esc(S.get(lang, "place.people"))}</h2>',
                          '          <ul class="people">']
                parts += [f'            <li>{esc(x)}</li>' for x in p["people"]]
                parts += ['          </ul>', '          </section>']
            lat, lng = p["lat"], p["lng"]
            ll = f"{lat:.5f},{lng:.5f}"
            osm = f"https://www.openstreetmap.org/?mlat={lat:.5f}&mlon={lng:.5f}#map=17/{lat:.5f}/{lng:.5f}"
            gmaps = f"https://www.google.com/maps/search/?api=1&query={quote(ll)}"
            amaps = f"https://maps.apple.com/?ll={ll}&q={quote(name)}"
            parts += ['          <section class="art-section" aria-labelledby="loc-title">',
                      f'          <h2 id="loc-title">{esc(S.get(lang, "place.location"))}</h2>',
                      f'          <p>{esc(p["district"])}, {esc(CITY[lang])} · {esc(S.get(lang, "place.coords"))}: '
                      f'<span class="coords">{lat:.5f}, {lng:.5f}</span></p>']
            if not p.get("coordsVerified", True):
                parts.append(f'          <p class="small">{esc(S.get(lang, "place.coordsApprox"))}</p>')
            parts += ['          <ul class="map-links">',
                      f'            <li><a href="{att(osm)}" rel="noopener">{esc(S.get(lang, "place.osm"))}</a></li>',
                      f'            <li><a href="{att(gmaps)}" rel="noopener">{esc(S.get(lang, "place.google"))}</a></li>',
                      f'            <li><a href="{att(amaps)}" rel="noopener">{esc(S.get(lang, "place.apple"))}</a></li>',
                      '          </ul>', '          </section>']
            if walks_of.get(pid):
                parts += ['          <section class="art-section" aria-labelledby="walks-title">',
                          f'          <h2 id="walks-title">{esc(S.get(lang, "place.walks"))}</h2>',
                          '          <ul class="link-list">']
                for r, i in walks_of[pid]:
                    stop = S.get(lang, "place.stopOf", n=i, total=len(r["poiIds"]))
                    parts.append(f'            <li><a href="{rel(path, walk_path(lang, r["id"]))}">{esc(r["name"][lang])}</a>'
                                 f' <span class="meta">– {esc(stop)}</span></li>')
                parts += ['          </ul>', '          </section>']
            near = sorted((distance_m(p, q), q["id"]) for q in pois if q["id"] != pid)[:NEARBY_COUNT]
            parts += ['          <section class="art-section" aria-labelledby="near-title">',
                      f'          <h2 id="near-title">{esc(S.get(lang, "place.nearby"))}</h2>',
                      '          <ul class="link-list">']
            for d, qid in near:
                q = by_id[qid]
                parts.append(f'            <li><a href="{rel(path, place_path(lang, qid))}">{esc(q["name"][lang])}</a>'
                             f' <span class="meta">– {esc(q["district"])} · {fmt_distance(lang, d)}</span></li>')
            parts += ['          </ul>', '          </section>']
            if p["sources"]:
                parts += ['          <section class="art-section" aria-labelledby="src-title">',
                          f'          <h2 id="src-title">{esc(S.get(lang, "place.sources"))}</h2>',
                          '          <ol class="sources">']
                parts += [f'            <li><a href="{att(u)}" rel="noopener">{esc(pretty_url(u))}</a></li>' for u in p["sources"]]
                parts += ['          </ol>', '          </section>']
            parts.append('        </article>')
            if was_cut:
                parts.append(cta_block(B, t, ctx, used, t["home.ctaTitle"], B.strip_tags(t["home.ctaLead"])))
            else:
                parts.append(cta_block(B, t, ctx, used, S.get(lang, "place.appTitle"), S.get(lang, "place.appBody")))
            body = '      <div class="container narrow">\n' + "\n".join(parts) + "\n      </div>"
            place_ld = {
                "@context": "https://schema.org", "@type": "TouristAttraction",
                "name": name, "description": teaser, "url": SITE_HOLDER + path, "inLanguage": lang,
                "geo": {"@type": "GeoCoordinates", "latitude": lat, "longitude": lng},
                "address": {"@type": "PostalAddress", "addressLocality": f'{p["district"]}, {CITY[lang]}',
                            "addressRegion": "İstanbul", "addressCountry": "TR"},
                "isAccessibleForFree": p["visitable"] in ("open", "exterior_only"),
            }
            if plist:
                place_ld["image"] = [SITE_HOLDER + x[1] for x in plist]
            title = S.get(lang, "place.metaTitle", name=name)
            add(path, shell(B, t, ctx, used, title, teaser, [place_ld, crumb_ld], body), alts, "0.7")

        # ---------------- walk pages ----------------
        for r in routes:
            wid = r["id"]
            path = walk_path(lang, wid)
            alts = alts_for(walk_path, wid)
            name, desc = r["name"][lang], r["description"][lang]
            stops = [by_id[x] for x in r["poiIds"]]
            first = next((pics[s["id"]][0] for s in stops if pics[s["id"]]), None)
            og = (B.SITE + first[1], first[2], first[3]) if first else None
            ctx = static_ctx(B, lang, path, "places", alts, "article", og, f"web-{lang}-w-{wid}")
            crumb_html, crumb_ld = crumbs(S, lang, path, [
                (S.get(lang, "crumb.home"), home_path(lang)),
                (S.get(lang, "crumb.places"), list_path(lang)),
                (name, None)])
            mode = S.get(lang, "walk.mode." + ("ferry" if r["travelMode"] == "ferry" else "walking"))
            meta = f'{S.count(lang, "count.stops", len(stops))} · {duration(S, lang, r["durationMin"])} · {mode}'
            free = not r["premium"]
            parts = [crumb_html, '        <article class="walk-page">',
                     '          <header class="page-head">',
                     f'            <p class="eyebrow">{esc(S.get(lang, "walk.eyebrow"))}'
                     + (f' <span class="tag">{esc(S.get(lang, "walk.free"))}</span>' if free else "") + '</p>',
                     f'            <h1>{esc(name)}</h1>',
                     '            <div class="tile-rule" aria-hidden="true"><i></i><i></i><i></i></div>',
                     f'            <p class="walk-facts">{esc(meta)}</p>',
                     '          </header>',
                     para_html(desc),
                     '          <section class="art-section" aria-labelledby="stops-title">',
                     f'          <h2 id="stops-title">{esc(S.get(lang, "walk.stops"))}</h2>',
                     '          <ol class="stops">']
            ferry = set(r.get("ferryBefore") or [])
            for s in stops:
                note = f'<p class="stop-note">{esc(S.get(lang, "walk.ferryBefore"))}</p>' if s["id"] in ferry else ""
                parts.append(f'            <li class="stop">{note}<p class="stop-name"><a href="{rel(path, place_path(lang, s["id"]))}">'
                             f'{esc(s["name"][lang])}</a></p><p class="stop-meta">{esc(s["district"])} · '
                             f'{esc(period_text(s["period"]))}</p><p class="stop-teaser">{esc(s["teaser"][lang])}</p></li>')
            parts += ['          </ol>', '          </section>',
                      '          <section class="art-section" aria-labelledby="map-title">',
                      f'          <h2 id="map-title">{esc(S.get(lang, "walk.map"))}</h2>']
            if r["travelMode"] == "walking" and not ferry and len(stops) >= 2:
                pts = [f'{s["lat"]:.5f},{s["lng"]:.5f}' for s in stops]
                url = (f"https://www.google.com/maps/dir/?api=1&origin={quote(pts[0])}&destination={quote(pts[-1])}"
                       + (f"&waypoints={quote('|'.join(pts[1:-1]))}" if len(pts) > 2 else "") + "&travelmode=walking")
                parts.append(f'          <ul class="map-links"><li><a href="{att(url)}" rel="noopener">'
                             f'{esc(S.get(lang, "walk.route"))}</a></li></ul>')
            else:
                parts.append(f'          <p>{esc(S.get(lang, "walk.transitNote"))}</p>')
            parts += [f'          <p class="small">{esc(S.get(lang, "walk.routeNote"))}</p>', '          </section>',
                      '        </article>',
                      cta_block(B, t, ctx, used, S.get(lang, "walk.ctaTitle"), S.get(lang, "walk.ctaBody"))]
            body = '      <div class="container narrow">\n' + "\n".join(parts) + "\n      </div>"
            trip_ld = {
                "@context": "https://schema.org", "@type": "TouristTrip",
                "name": name, "description": desc, "url": SITE_HOLDER + path, "inLanguage": lang,
                "itinerary": {"@type": "ItemList", "numberOfItems": len(stops), "itemListElement": [
                    {"@type": "ListItem", "position": i, "item": {
                        "@type": "TouristAttraction", "name": s["name"][lang], "url": SITE_HOLDER + place_path(lang, s["id"]),
                        "geo": {"@type": "GeoCoordinates", "latitude": s["lat"], "longitude": s["lng"]}}}
                    for i, s in enumerate(stops, 1)]},
            }
            if first:
                trip_ld["image"] = SITE_HOLDER + first[1]
            title = S.get(lang, "walk.metaTitle", name=name)
            add(path, shell(B, t, ctx, used, title, desc, [trip_ld, crumb_ld], body), alts, "0.7")

        # ---------------- list page ----------------
        path = list_path(lang)
        alts = alts_for(lambda x: list_path(x))
        ctx = static_ctx(B, lang, path, "places", alts, "website", None, f"web-{lang}-places")
        n_places = S.count(lang, "count.places", len(pois))
        n_walks = S.count(lang, "count.walks", len(routes))
        crumb_html, crumb_ld = crumbs(S, lang, path, [(S.get(lang, "crumb.home"), home_path(lang)),
                                                      (S.get(lang, "crumb.places"), None)])
        wa = WALKS_ANCHOR[lang]
        parts = [crumb_html, '        <header class="page-head">',
                 f'          <h1>{esc(S.get(lang, "list.h1"))}</h1>',
                 '          <div class="tile-rule" aria-hidden="true"><i></i><i></i><i></i></div>',
                 f'          <p class="lead">{esc(S.get(lang, "list.lead", places=n_places, walks=n_walks))}</p>',
                 '        </header>',
                 f'        <nav class="toc" aria-label="{att(S.get(lang, "list.themes"))}">',
                 '          <ul>']
        for c in content["categories"]:
            parts.append(f'            <li><a href="#{c["id"]}" style="--cat:{c["color"]}">{esc(c["name"][lang])}</a></li>')
        parts += [f'            <li><a href="#{wa}">{esc(S.get(lang, "list.walksTitle"))}</a></li>', '          </ul>', '        </nav>']
        item_ld = []
        for c in content["categories"]:
            members = [p for p in pois if p["category"] == c["id"]]
            if not members:
                continue
            parts += [f'        <section class="cat-group" id="{c["id"]}" style="--cat:{c["color"]}" aria-labelledby="{c["id"]}-title">',
                      f'          <h2 id="{c["id"]}-title">{esc(c["name"][lang])}</h2>',
                      '          <ul class="place-list">']
            for p in members:
                item_ld.append({"@type": "ListItem", "position": len(item_ld) + 1, "name": p["name"][lang],
                                "url": SITE_HOLDER + place_path(lang, p["id"])})
                parts.append(f'            <li><p class="pl-name"><a href="{rel(path, place_path(lang, p["id"]))}">{esc(p["name"][lang])}</a></p>'
                             f'<p class="pl-meta">{esc(p["district"])} · {esc(period_text(p["period"]))}</p>'
                             f'<p class="pl-teaser">{esc(p["teaser"][lang])}</p></li>')
            parts += ['          </ul>', '        </section>']
        parts += [f'        <section class="cat-group walks-group" id="{wa}" aria-labelledby="{wa}-title">',
                  f'          <h2 id="{wa}-title">{esc(S.get(lang, "list.walksTitle"))}</h2>',
                  f'          <p class="section-lead">{esc(S.get(lang, "list.walksLead"))}</p>',
                  '          <ol class="walks">']
        for r in routes:
            free = not r["premium"]
            mode = S.get(lang, "walk.mode." + ("ferry" if r["travelMode"] == "ferry" else "walking"))
            meta = f'{S.count(lang, "count.stops", len(r["poiIds"]))} · {duration(S, lang, r["durationMin"])} · {mode}'
            tag = f' <span class="tag">{esc(S.get(lang, "walk.free"))}</span>' if free else ""
            parts.append(f'            <li class="walk{" free" if free else ""}"><p class="walk-name"><a class="walk-link" '
                         f'href="{rel(path, walk_path(lang, r["id"]))}">{esc(r["name"][lang])}</a>{tag}</p>'
                         f'<p class="walk-meta">{esc(meta)}</p></li>')
        parts += ['          </ol>', '        </section>',
                  cta_block(B, t, ctx, used, t["home.ctaTitle"], B.strip_tags(t["home.ctaLead"]))]
        body = '      <div class="container narrow">\n' + "\n".join(parts) + "\n      </div>"
        title = S.get(lang, "list.metaTitle", places=n_places, walks=n_walks)
        desc = S.get(lang, "list.metaDesc")
        coll_ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": S.get(lang, "list.h1"),
                   "description": desc, "url": SITE_HOLDER + path, "inLanguage": lang,
                   "mainEntity": {"@type": "ItemList", "numberOfItems": len(item_ld), "itemListElement": item_ld}}
        add(path, shell(B, t, ctx, used, title, desc, [coll_ld, crumb_ld], body), alts, "0.8")

    # ---------------- /pl/ and /tr/ home pages ----------------
    home_alts = {x: home_path(x) for x in LANGS}
    for lang in ("pl", "tr"):
        path = home_path(lang)
        t = dict(texts[lang])
        for k, v in t.items():  # links inside texts written for the site root
            t[k] = v.replace('href="privacy/"', f'href="../privacy/?lang={lang}"')
        ctx = static_ctx(B, lang, path, "home", home_alts, "website", None, f"web-{lang}-home")
        for i, r in enumerate(routes, 1):
            ctx[f"walk_link_{i}"] = f'href="{rel(path, walk_path(lang, r["id"]))}"'
        ctx["walks_anchor"] = "#" + WALKS_ANCHOR[lang]
        ctx["walks_attrs"] = ""
        out = B.render((B.ROOT / "src" / "index.html").read_text("utf-8"), t, ctx, used)
        out = strip_i18n("<!-- Generated by tools/build.py from src/index.html and assets/i18n/"
                         f"{lang}.json. Do not edit. -->\n" + out)
        outputs[path + "index.html"] = out
        sitemap.append({"loc": path, "lastmod": PAGES_LASTMOD, "priority": "1.0", "alts": home_alts})
        problems.extend(B.check_banned(f"{path} home", B.zones_of(out)))

    # ---------------- folders without a page of their own: point to the right one ----------------
    for lang, folder, target in [("en", "en/", ""), ("en", walk_path("en", "x")[:-2], list_path("en") + "#walks"),
                                 ("pl", walk_path("pl", "x")[:-2], list_path("pl") + "#spacery"),
                                 ("tr", walk_path("tr", "x")[:-2], list_path("tr") + "#yuruyusler")]:
        link = rel(folder, target.split("#")[0]) + ("#" + target.split("#")[1] if "#" in target else "")
        outputs[folder + "index.html"] = (
            f'<!doctype html>\n<html lang="{lang}">\n  <head>\n    <meta charset="utf-8" />\n'
            f'    <meta name="viewport" content="width=device-width, initial-scale=1" />\n'
            f'    <title>Polish Footprints: Istanbul</title>\n    <meta name="robots" content="noindex" />\n'
            f'    <link rel="canonical" href="{B.SITE}{target.split("#")[0]}" />\n'
            f'    <meta http-equiv="refresh" content="0; url={link}" />\n  </head>\n'
            f'  <body>\n    <p>{esc(S.get(lang, "redirect.text"))} <a href="{link}">{B.SITE}{target}</a></p>\n  </body>\n</html>\n')

    problems += S.problems()
    problems += images.finish()
    return outputs, problems, notes, sitemap
