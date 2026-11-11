# RESULT: Polish Footprints website (2026-11-11)

Static site for **Polish Footprints: Istanbul** (iOS, ASC 6833051676) in `~/Dev/PolandInIstanbul/web/`,
copied from the British Footprints site (`~/Dev/ingilizinistanbul/web`, untouched) and re-targeted.
Local git repo, branch `main`, **no remote, not pushed, no GitHub repo created**.

## Pages (after publishing)
| Page | URL | Contents |
|---|---|---|
| Landing | https://mgmemik.github.io/polish-footprints-web/ | hero (series cobalt tile + white-red sash + compass, CSS/SVG, no photo), H1, lead, App Store button (placeholder) + "Coming soon to the App Store", stats 38 places / 8 walks / 86 pictures / 3 languages; "Nine chapters" (the 9 content themes in the app's category colours); What's inside (6 features); Eight walks (stops, rough time, 2 marked free); Free vs one-time unlock (no price); optional screenshot gallery (off); 9 FAQs incl. "How do I get to Polonezköy"; CTA |
| Privacy | .../privacy/ | summary + 16 sections, effective 11 November 2026 |
| Support | .../support/ | app@save-all.com + 10 FAQs |

Polish and Turkish: same URLs with `?lang=pl` / `?lang=tr`; the default follows the browser
(pl → PL, tr → TR, else EN); the choice is remembered and internal links keep `?lang=`.
hreflang en/pl/tr/x-default on every page and in `sitemap.xml` (9 URLs). JSON-LD
`MobileApplication` (TravelApplication, iOS, pl/en/tr, no downloadUrl until live) + `FAQPage`
on landing and support. OG/Twitter card `assets/img/og-image.png` (1200x630, icon + title +
sash, made by `tools/make_images.py`).

## Numbers checked against content/pois.json (updated 2026-11-11)
38 POIs, 8 routes, 9 categories; 90 picture slots = **86 distinct pictures**, all bundled in the
app (`app/assets/images/poi/manifest.json` covers every URL); every name/teaser/story/visit has
pl, en and tr. Free (premium false): routes `mickiewicz-pera` (6 stops) and
`sadyk-cihangir-dolmabahce` (2 stops) = the 8 free places. Walk names, stop counts and
durations from `routes`. Topics and wording from `research/booklet/KITAPCIK-*.md`; the ASO
texts in `research/aso/metadata/` appeared during the work and are echoed (opening line
"Istanbul has a Polish story…", "where a story rests on tradition… the text says so",
"Apple Account").

## Privacy facts confirmed in the app code
- Location: geolocator, `NSLocationWhenInUseUsageDescription` (no background mode); never asked
  at launch, only when the user taps (`LocationCubit.start(from: card|button|nearest)`);
  coordinates stay on the device; only `inIstanbul` true/false/unknown (30 km from 41.02, 28.98)
  is sent.
- TelemetryDeck app F38BB074-…, Flutter SDK 4.0.0 → Swift SDK 2.14.2; closed vocabulary in
  `lib/core/telemetry/telemetry.dart`; context keys `channel, entitled, uiLanguage, theme,
  inIstanbul, storeCheck, storeDiag`; user id = identifierForVendor, SHA-256 on the phone
  (no custom salt); opt-out switch sends one last `Settings.analyticsChanged` and stops the SDK;
  not started while off.
- Test mode: everything except real App Store installs (dev, TestFlight, App Review detected by
  sandbox AppTransaction / originalAppVersion "1.0" / iPhone99 model / running version newer than
  the iTunes lookup) — `release_channel.dart`.
- Purchases: in_app_purchase, product `polish_full_unlock`; StoreKit transaction `environment`
  decides real vs test; `TelemetryDeck.Purchase.completed` with the fixed USD list price only for
  production purchases. The page does not state the price.
- Network: OSM tiles (`tile.openstreetmap.org`), iTunes lookup
  `itunes.apple.com/lookup?id=6833051676&country=us` (App Store copies only), maps hand-off
  (Apple Maps / Google Maps / browser), Rate (App Store page) and Share (share sheet with
  `kWebsiteUrl`) only on tap. Pictures bundled; `CachedNetworkImage` is only a fallback for
  URLs missing from the bundle (none today).
- Stored on device (shared_preferences): language, theme, maps app, visited, favourites,
  analytics switch, unlock flag, free-hint flag, first-launch flag. No account, no ads, no IDFA.

## Differences from the British policy
- iOS only: no Google Play, Android or Play-robot text (app has no Play record yet).
- New: location is asked only on tap (the British text does not say so); location-permission
  signals (`Location.promptShown`, `Location.permissionAsked`); Settings signals for Rate/Share;
  context keys `storeCheck` and `storeDiag` (the British table lists only 5 keys although its
  app sends them too); section 8 "Other connections" (iTunes version lookup, Rate/links, Share).
- Identifier described as the iOS identifier-for-vendor hashed on the phone (British text says
  "random identifier … hashed with a salt"; the SDK uses an empty salt).
- The purchase price is not written in the policy (British text says 0.99).
- "Children" section renamed "Age of users" (banned word in headings); UODO named for Poland.
- Image licences: CC BY/CC BY-SA 3.0 and 4.0 (+ CC0/PD), as in the content.
- Support: version is shown at the top of Settings (not "Settings › About"); location path
  ends in "Footprints" (CFBundleDisplayName); "Apple Account" wording.

## Checks
- `python3 tools/build.py` and `--check`: ok, 227 keys, en/pl/tr in sync; banned-word check
  (flags, kids/children/dzieci/çocuk, superlatives, prices/currencies) over titles, meta,
  headings and FAQ questions in all three languages.
- `python3 tools/check_links.py`: ok. External links in the three JSON files answered HTTP 200.
- Headless Chrome: `?lang=pl` / `?lang=tr` swap title, canonical, `<html lang>`, PL/EN/TR button
  state and tag internal links; browser language pl → Polish, tr → Turkish, de → English.
- Screenshots looked at: landing PL dark desktop + mobile, EN light desktop, TR light mobile;
  privacy PL dark desktop; support TR light mobile. Screenshot drop-in tested on a scratch copy.
- Not tested: real Safari/iOS; Lighthouse not run.

## Open points for A / the owner
1. Publish (README): create public repo `mgmemik/polish-footprints-web`, push `main`, Pages from
   `main` / root, then enter the URLs in ASC (`listing-extras.mjs` already has them).
2. App: `kWebsiteUrl` in `app/lib/shared/utils/app_links.dart` is still `https://mgmemik.github.io/`
   (TODO) – the Share button sends that link. Set it to the new site (app agent's job).
3. IAP texts in `app/tools/asc/iap.mjs` still say "36 stories, 7 walks" – content is now 38/8.
4. Family Sharing: support says the unlock supports it (`familySharable: true` in `iap.mjs`;
   local Products.storekit says false). Verify in ASC.
5. The Polish ASO description calls the app "Polskie ślady: Stambuł"; the site uses the app
   name "Polish Footprints: Istanbul" (JSON-LD alternateName lists the Polish one). Align once the
   Polish store name is decided.
6. Screenshots: none used yet (only 2 PNGs in progress under research/store). README explains how
   to switch the gallery on.
7. When live: store button + JSON-LD downloadUrl (README steps).
