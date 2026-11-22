# Static place and walk pages - result (2026-11-22)

Built and checked locally only. Nothing committed, pushed or deployed.

## What was generated

`python3 -I tools/build.py` now also runs `tools/build_pages.py`, which builds from
`../app/assets/data/pois.json` (38 places, 8 walks, version 1, updated 2026-11-11):

| | pl | en | tr |
|---|---|---|---|
| Home pre-rendered in the language | `/pl/` | `/` (unchanged, JS-switched) | `/tr/` |
| List (places by theme + walks) | `/pl/miejsca/` | `/en/places/` | `/tr/yerler/` |
| Place pages | 38 | 38 | 38 |
| Walk pages | 8 | 8 | 8 |
| **Indexable pages** | **48** | **47** | **48** |

That is 143 new indexable pages, plus 4 small noindex redirects (`/en/`, `/en/walks/`, `/pl/spacery/`,
`/tr/yuruyusler/`) and 48 WebP pictures in `assets/img/places/` (4.3 MB in total).
`sitemap.xml` (now generated) lists 152 URLs: the 9 old entries, with the same lastmod as before, plus
the 143 new ones, each with pl/en/tr + x-default alternates.

Each page: `<html lang>`, canonical, hreflang (pl/en/tr + x-default = en), its own title and
description, Open Graph (the place's first picture), `apple-itunes-app` meta, JSON-LD
(TouristAttraction / TouristTrip with ItemList / CollectionPage, plus BreadcrumbList), a visible
breadcrumb, and a PL/EN/TR switch made of real links. Place pages contain: category, name, teaser,
picture(s) with credit + licence link + source, facts (theme, district, period, access), the story,
"How to visit" in full, people, location (coordinates + OpenStreetMap / Google Maps / Apple Maps
links), the walks that include the place (with stop number), the 4 nearest places, sources, and a
store button. No embedded maps, no third-party scripts, no cookies.

- **Free/premium cut**: `PREMIUM_CUT = {"story_fraction": 0.38, "images": 1}` in
  `tools/build_pages.py`. The 30 premium places show 30-46 % of the story (median 38 %, cut at a
  paragraph or sentence end), then a "Read the full story in the app" box, and their first picture
  only. The 8 free places (the stops of the 2 free walks) show everything.
- **Store links**: `https://apps.apple.com/app/apple-store/id6833051676?pt=127856308&ct=...&mt=8`,
  `ct` = `web-home` (`/`), `web-pl-home`/`web-tr-home`, `web-<lang>-places`, `web-<lang>-<place id>`,
  `web-<lang>-w-<walk id>` (longest: 36 characters).

## Changes to existing files

- `/`, `/privacy/`, `/support/` keep their URLs and their `?lang=` behaviour. New: a "Places" link
  in the header and footer (all pages), on the home page a link to the list after the themes, the
  8 walk names link to their walk pages, and a link to all walks. Those links have
  `data-href-pl`/`data-href-tr`, so `site.js` sends `/?lang=pl` visitors to the Polish pages.
- Home `/`: hreflang pl/tr now point at `/pl/` and `/tr/`; on `/?lang=pl|tr` site.js sets the
  canonical to `/pl/` or `/tr/`. The store buttons on `/` carry `ct=web-home`.
- Partials now take context values (canonical, hreflang, og, nav links, store URL, language switch:
  `lang-buttons.html` for the JS pages, `lang-links.html` for the pre-rendered ones). The existing
  pages' output is the same apart from the points above.
- `assets/site.js`: pre-rendered pages (`data-lang` on the script tag) are left as they are;
  `data-href-<lang>` links; `data-canonical-<lang>`.
- New i18n keys: `common.navPlaces`, `home.placesLink`, `home.walksLink` (pl/en/tr). The page UI texts
  are in `src/pages-i18n.json`.
- CSS: article/list styles, link-style language switch, and a tighter nav at <= 480 px (with the
  new "Places" link it would otherwise wrap to two lines on phones).
- `tools/check_links.py` now checks all 150 HTML files: local links and #fragments, alt texts,
  balanced tags, JSON-LD parsing, lang/canonical/hreflang present and pointing at existing pages.
- `tools/shoot.py gen-` takes one phone-width screenshot per generated page type.
- `_config.yml`: `RESULT-pages.md` excluded. `pl/`, `en/`, `tr/` contain no `_` folders, so Pages
  publishes them. Files without front matter are copied as-is.

## Verification

- `python3 -I tools/build.py` ok. A second run writes nothing. A clean rebuild (generated folders,
  pictures and index deleted) gave byte-identical output for all 198 files. `--check` ok.
- `python3 -I tools/check_links.py`: 150 pages, 289 JSON-LD blocks, all parse, 0 problems.
- Local server (`python3 -m http.server`): 19 URLs fetched (3+ per language, plus `/`, `?lang=`
  variants, privacy, support, redirects), all 200 with the right lang, title, canonical and hreflang.
- Headless Chrome on `/?lang=pl`, `/privacy/?lang=tr` and a Polish place page: link swap,
  canonical and `<html lang>` are correct at runtime.
- Screenshots (390 px, dark and light) in `_screens/gen-*.png`, which is git-ignored: place
  (premium, pl), place (free, en), walk (tr), list (pl), home (tr). No horizontal scroll was visible.

## Not done / to note

- Build NOTEs (not errors): 4 teasers contain words from the store-banned list ("dzieci/child/çocuk"
  in the Częstochowa church teaser, "best-loved" in the en Sublime Porte teaser). This is fine on a
  website, but these words should stay out of store metadata.
- Walk pages list all stops, including those of premium walks. This is public information and the
  stories stay cut. Change it in `build_pages.py` if wanted.
- Picture credits are shown as written in `pois.json` (mostly English), on all language pages.
- The `/?lang=pl` and `/?lang=tr` home entries stay in the sitemap as asked, but their canonical is
  now `/pl/` and `/tr/`, so Search Console may report them as "alternate page with proper canonical".
  This is harmless.
- Not validated with Google's Rich Results Test (needs the live site).

## How to publish

1. Review, then commit the `web/` repo (new: `pl/ en/ tr/ assets/img/places/ src/page.html
   src/pages-i18n.json src/partials/lang-*.html src/places-images.json tools/build_pages.py`).
2. `git push` to `mgmemik/polish-footprints-web` (main). Pages redeploys in about a minute.
3. Check `https://mgmemik.github.io/polish-footprints-web/pl/miejsca/mickiewicz-museum/` and
   `/privacy/?lang=pl` (App Store Connect URL, unchanged).
4. Search Console: resubmit `sitemap.xml`. Optionally request indexing for `/pl/`, `/pl/miejsca/`,
   `/tr/yerler/`.
5. After a content change: sync the app content (`app/tools/sync_content.sh`), bump `PAGES_LASTMOD`,
   run `python3 -I tools/build.py` and `python3 -I tools/check_links.py`, then commit.
