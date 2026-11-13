# orOS models

Model files that [orOS](https://useoros.online) downloads on the person's
device, only when the person asks for them. Nothing here is built into orOS,
and nothing here is changed: each file is an exact copy of its upstream
release, so orOS checks it by SHA-256 before it keeps it.

Served from GitHub Pages: `https://koulaxizis.github.io/oros-models/`.

## translate/

Mozilla's [Firefox Translations](https://github.com/mozilla/translations)
models (the ones Firefox's own page translation uses), for orOS's translation
on the device (`translate/engine.js` in [koulaxizis/oros](https://github.com/koulaxizis/oros):
Text Tools › Translate, and Writer's suggestions later).

| Direction | Model | Release |
|---|---|---|
| Greek → English | `translate/el-en/spring-2024_RJucgx7LRMKB9E4oSSzdtA/` | tiny, Release |
| English → Greek | `translate/en-el/spring-2024_Y3ThG3XkTxG4ROUQK2LpVg/` | tiny, Release |

Each folder holds the three files exactly as Mozilla publishes them (gzip):
`model.*.intgemm.alphas.bin.gz`, `lex.50.50.*.s2t.bin.gz` and `vocab.*.spm.gz`.
`translate/index.json` records where they came from (Mozilla's model registry
`models.json` and the date it was read) and Mozilla's quality scores.

Licence: [MPL-2.0](LICENSE), © Mozilla Corporation and contributors.

### Why a copy

Mozilla's storage does not allow downloads from other web sites (no CORS),
and its addresses change with each training round. A copy here keeps orOS
working offline-first, on a static site, with files whose hashes are written
into orOS itself.

### Adding or updating a direction

1. Read `https://storage.googleapis.com/moz-fx-translations-data--303e-prod-translations-data/db/models.json`
   and take the entry of the direction with `"releaseStatus": "Release"`.
2. Download its three files from the registry's `baseUrl` + `path`, unchanged,
   into `translate/<from>-<to>/<folder>/`.
3. Unpack each one, write its byte size and SHA-256 into `MODELS` in
   `translate/engine.js` (koulaxizis/oros), and add the row above.

GitHub Pages serves up to 1 GB per site; one direction is about 15 MB.
