# Polish Footprints: Istanbul - website

Landing page, privacy policy and support page for the **Polish Footprints: Istanbul** app
(iPhone and iPad; App Store id 6833051676, bundle com.thebarnapp.polishfootprints.istanbul),
served by GitHub Pages. Plain HTML, CSS and one small script; no framework, no cookies, no
trackers, fonts self-hosted. Built from the British Footprints site (`~/Dev/ingilizinistanbul/web`),
same structure and series look, with the white-red sash of the icon instead of the British brass.

Live (after publishing): <https://mgmemik.github.io/polish-footprints-web/>

| Page | Path |
|---|---|
| Home (marketing) | `/` (pre-rendered copies: `/pl/`, `/tr/`) |
| Privacy policy | `/privacy/` |
| Support | `/support/` |
| Places and walks (lists) | `/pl/miejsca/`, `/en/places/`, `/tr/yerler/` |
| One page per place | `/pl/miejsca/<id>/`, `/en/places/<id>/`, `/tr/yerler/<id>/` |
| One page per walk | `/pl/spacery/<id>/`, `/en/walks/<id>/`, `/tr/yuruyusler/<id>/` |

Languages: **Polish, English, Turkish** (PL / EN / TR switch). On `/`, `/privacy/` and `/support/`
English is baked into the HTML and `assets/site.js` swaps in Polish or Turkish; all other pages are
pre-rendered in one language (see "Place and walk pages" below). Which language a visitor sees: `?lang=pl|en|tr` in the
URL, else their saved choice (localStorage `pf_lang`), else the browser (pl → Polish, tr → Turkish,
anything else → English). Links between the three pages keep `?lang=`.

## URLs for App Store Connect

**Do not change these paths later** - the store points at them. `app/tools/asc/listing-extras.mjs`
already uses them (with `?lang=pl` / `?lang=tr` for the Polish and Turkish localizations).

| Field | Value |
|---|---|
| App Information > Privacy Policy URL | `https://mgmemik.github.io/polish-footprints-web/privacy/` (pl: `...privacy/?lang=pl`, tr: `...privacy/?lang=tr`) |
| Version > Support URL | `https://mgmemik.github.io/polish-footprints-web/support/` (`?lang=pl`, `?lang=tr`) |
| Version > Marketing URL (optional) | `https://mgmemik.github.io/polish-footprints-web/` (`?lang=pl`, `?lang=tr`) |

The app's own share link (`kWebsiteUrl` in `app/lib/shared/utils/app_links.dart`) should point at
`https://mgmemik.github.io/polish-footprints-web/` once the site is live.

## Publishing (GitHub Pages)

1. Create the public repo `mgmemik/polish-footprints-web` (empty, no README).
2. `git remote add origin git@github.com:mgmemik/polish-footprints-web.git && git push -u origin main`
3. Repo > Settings > Pages > Source: *Deploy from a branch*, branch `main`, folder `/ (root)`.
   Or: `gh api -X POST repos/mgmemik/polish-footprints-web/pages -f "source[branch]=main" -f "source[path]=/"`
4. After a minute the site is at the URL above. Pages runs Jekyll, which only copies the HTML;
   `_config.yml` keeps `src/`, `tools/`, `README.md`, `RESULT.md` out, and `_screens/` is
   never published (folders starting with `_` are skipped; it is also git-ignored).
5. Check `https://mgmemik.github.io/polish-footprints-web/privacy/?lang=pl` opens before entering
   the URLs in App Store Connect.
6. Optional: Google Search Console > add the URL prefix property and submit `sitemap.xml`.

## When the app is live: the store button

The App Store button is a placeholder (`href="#appstore"` with `data-placeholder`, in
`src/partials/stores.html`, used twice on the landing page) plus the line "Coming soon to the App
Store" (`common.storeSoon`) - the way the British site looked before its launch. When the App
Store page is public:

1. In `src/partials/stores.html` set `href="https://apps.apple.com/app/id6833051676"` and remove
   `data-placeholder="appstore"` and the placeholder comment.
2. Set `common.storeSoon` to `""` in `en.json`, `pl.json` and `tr.json` (an empty line is hidden).
3. Add `"downloadUrl": "https://apps.apple.com/app/id6833051676",` to the `MobileApplication`
   JSON-LD in `src/index.html`.
4. `python3 tools/build.py`, commit, push.

No Android/Google Play mention anywhere until the Play version exists. When it does: add a second
store button (see the British `stores.html`), "iPhone and Android" wording, Google parts in the
privacy policy (Play purchases, Android location path, Play pre-launch robots as test data), and
`"operatingSystem": "iOS, Android"`.

## Adding app screenshots later

The page has a ready screenshot gallery (`src/partials/screens.html`, styles `.gallery`/`.shot`)
that is switched off while there are no screenshots. To switch it on:

1. Export phone screenshots as WebP, about 540 px wide (< 200 KB each), into
   `assets/img/screens/` - e.g. from `../research/store/screenshots/ios/` (raw app screens, not
   the store art with captions; never British screenshots; nothing showing a price or "free" badge).
2. Create `assets/img/screens/screens.json`:
   ```json
   [
     { "file": "01-map.webp", "width": 540, "height": 1171, "key": "home.s1" },
     { "file": "02-place.webp", "width": 540, "height": 1171, "key": "home.s2" }
   ]
   ```
3. Add the caption keys (`home.s1`, `home.s2`, ...) to all three language files.
4. `python3 tools/build.py` - the section appears between "Start free" and the FAQ, with
   "A look inside the app" (`home.screensTitle`/`home.screensLead`, already translated).

## Place and walk pages

`python3 -I tools/build.py` also runs `tools/build_pages.py`, which turns the app's content file
`../app/assets/data/pois.json` (38 places, 8 walks) into static pages, each fully pre-rendered in
its language so that search engines see Polish and Turkish too (no JavaScript needed to read them):

- `/pl/` and `/tr/`: the home page (`src/index.html`) with the Polish / Turkish texts baked in.
  `/` now names them in its hreflang links, and `/?lang=pl` / `/?lang=tr` point their canonical
  at them (the `?lang=` URLs keep working exactly as before).
- the list pages (all places grouped by theme, then the walks), one page per place and one per walk,
  in each language. Place ids and walk ids are the ones from `pois.json`; the folder names are
  `miejsca`/`spacery` (pl), `places`/`walks` (en), `yerler`/`yuruyusler` (tr). `/en/`, `/en/walks/`,
  `/pl/spacery/` and `/tr/yuruyusler/` are small noindex redirects to the right page.
- Every page has `<html lang>`, a canonical URL, hreflang links to its pl/en/tr versions plus
  x-default (English), its own title and description (place name + teaser), Open Graph tags (the
  place's first picture), the Smart App Banner meta, and JSON-LD: `TouristAttraction` (places),
  `TouristTrip` with an `ItemList` itinerary (walks), `CollectionPage` (lists) and `BreadcrumbList`.
- The header's PL / EN / TR switch on these pages is made of links to the same page in the other
  languages; `site.js` sees `data-lang` on its script tag and leaves the page alone (theme toggle
  only). The "Places" link in the header/footer and the home page's links to the list and the walks
  use `data-href-pl` / `data-href-tr`, so on `/?lang=pl` they lead to the Polish pages.
- Pictures are copied from the app bundle (`../app/assets/images/poi/`, via its manifest) to
  `assets/img/places/<id>-<n>.webp` (long edge 960 px); `src/places-images.json` remembers which
  source each one was made from, so only changed pictures are converted again (needs Pillow only
  then). Each picture shows its credit, licence (linked) and Wikimedia source.
- UI texts of these pages: `src/pages-i18n.json` (en/pl/tr side by side, plural forms as lists).
  Header, footer and store button texts come from `assets/i18n/<lang>.json`.
- `sitemap.xml` is generated too: the old entries (/, /privacy/, /support/ and their `?lang=`
  variants, same lastmod as before) plus every generated page with its hreflang alternates. The
  generated pages' `<lastmod>` is `PAGES_LASTMOD` in `tools/build_pages.py` - bump it when the
  content or the page layout changes.
- The build removes any file under `pl/`, `en/`, `tr/` and `assets/img/places/` that it did not
  write (those folders are build output only), and `--check` reports stale pages.

**Free/premium cut** - one setting at the top of `tools/build_pages.py`:

```python
PREMIUM_CUT = {"story_fraction": 0.38, "images": 1}
```

Places marked `"premium": true` in `pois.json` show about `story_fraction` of their story (cut at the
nearest paragraph or sentence end; today 30-46 %, median 38 %), then a "Read the full story in the
app" box with the store button, and only their first `images` picture(s). Places that are free in the
app (the stops of the two free walks) show everything. `1.0` shows full stories, `0` none; `None`
for images shows all pictures. Walk pages always list all stops (each linking to its place page).

**Store links with campaign parameters** (App Store Connect > App Analytics > Acquisition >
Campaigns):

    https://apps.apple.com/app/apple-store/id6833051676?pt=127856308&ct=<campaign>&mt=8

`ct` (max 40 characters): `web-home` on `/` (any language, it is switched by JavaScript),
`web-pl-home` / `web-tr-home`, `web-<lang>-places` on the lists, `web-<lang>-<place id>` on place
pages, `web-<lang>-w-<walk id>` on walk pages (e.g. `web-pl-mickiewicz-museum`,
`web-tr-w-gold-1939`). The longest one today is 36 characters.

## Editing texts

- All texts live in `assets/i18n/en.json`, `pl.json` and `tr.json` (one file per language, same
  keys; values may contain simple inline HTML). Polish is the main audience - keep it natural.
- Page structure lives in `src/*.html` and `src/partials/*.html`.
- After any change: `python3 tools/build.py` - it bakes the English text into `index.html`,
  `privacy/index.html`, `support/index.html` (what search engines see), checks that the three
  files have the same keys and no empty values, and that no store-banned words appear in titles,
  meta tags, headings or FAQ questions in any language (flags, "kids/children/dzieci/çocuk",
  superlatives, prices). `python3 tools/build.py --check` only checks.
- Do not edit the generated HTML files directly.
- Numbers on the page (38 places, 8 walks, 86 pictures, 6 + 2 free stops) come from
  `../content/pois.json` (2026-11-11); update them when the content changes. The home page's walk
  links follow the order of `routes` in `pois.json` (`home.w1Name` = first walk, ...).
- The place and walk pages are rebuilt from `../app/assets/data/pois.json` (the copy the app
  ships): after a content change, sync the app's copy and its pictures first
  (`app/tools/sync_content.sh`), then run `python3 -I tools/build.py`.

## Checking locally

```bash
python3 -m http.server 8000      # then open http://localhost:8000/ (and ?lang=pl, ?lang=tr, ?theme=light)
python3 -I tools/check_links.py  # every page: local links and #fragments, alt texts, balanced tags,
                                 # JSON-LD parses, lang/canonical/hreflang present and pointing at real pages
python3 tools/shoot.py [filter]  # screenshots (PL/EN/TR x dark/light x desktop/mobile) into _screens/;
                                 # "gen-" = one phone-width shot per generated page type
```

## Images

`python3 tools/make_images.py` rebuilds them from `../research/design/assets/` (icon.svg,
icon-512.png): `assets/img/hero.svg` (cobalt tile, white-red sash, the icon's compass rose),
`icon-32/180/192/512.png`, `favicon.ico`, and `og-image.png` (1200x630, rendered from
`tools/og.html` with headless Chrome). Fonts are Playfair Display and Lora (OFL) subset from the
app's TTFs to Latin + Latin Extended-A (Polish and Turkish letters).
