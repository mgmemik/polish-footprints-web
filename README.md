# Polish Footprints: Istanbul - website

Landing page, privacy policy and support page for the **Polish Footprints: Istanbul** app
(iPhone and iPad; App Store id 6833051676, bundle com.thebarnapp.polishfootprints.istanbul),
served by GitHub Pages. Plain HTML, CSS and one small script; no framework, no cookies, no
trackers, fonts self-hosted. Built from the British Footprints site (`~/Dev/ingilizinistanbul/web`),
same structure and series look, with the white-red sash of the icon instead of the British brass.

Live (after publishing): <https://mgmemik.github.io/polish-footprints-web/>

| Page | Path |
|---|---|
| Home (marketing) | `/` |
| Privacy policy | `/privacy/` |
| Support | `/support/` |

Languages: **Polish, English, Turkish** (PL / EN / TR switch). English is baked into the HTML;
`assets/site.js` swaps in Polish or Turkish. Which language a visitor sees: `?lang=pl|en|tr` in the
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
  `../content/pois.json` (2026-11-11); update them when the content changes.

## Checking locally

```bash
python3 -m http.server 8000      # then open http://localhost:8000/ (and ?lang=pl, ?lang=tr, ?theme=light)
python3 tools/check_links.py     # local links, alt texts, balanced tags
python3 tools/shoot.py [filter]  # screenshots (PL/EN/TR x dark/light x desktop/mobile) into _screens/
```

## Images

`python3 tools/make_images.py` rebuilds them from `../research/design/assets/` (icon.svg,
icon-512.png): `assets/img/hero.svg` (cobalt tile, white-red sash, the icon's compass rose),
`icon-32/180/192/512.png`, `favicon.ico`, and `og-image.png` (1200x630, rendered from
`tools/og.html` with headless Chrome). Fonts are Playfair Display and Lora (OFL) subset from the
app's TTFs to Latin + Latin Extended-A (Polish and Turkish letters).
