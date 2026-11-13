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

Every language goes to and from English; other pairs go through English
(two models, as Firefox does). English and 21 languages, 39 directions:

| Language | Code | → English | English → | Download |
|---|---|---|---|---|
| Arabic | `ar` | yes | yes | 51 MB |
| Bulgarian | `bg` | yes | yes | 50 MB |
| Czech | `cs` | yes | yes | 51 MB |
| German | `de` | yes | yes | 51 MB |
| Greek | `el` | yes | yes | 30 MB |
| Spanish | `es` | yes | yes | 52 MB |
| Finnish | `fi` | yes | yes | 51 MB |
| French | `fr` | yes | yes | 52 MB |
| Hungarian | `hu` | yes | yes | 41 MB |
| Italian | `it` | yes | yes | 53 MB |
| Japanese | `ja` | — | yes | 36 MB |
| Dutch | `nl` | yes | yes | 52 MB |
| Polish | `pl` | yes | yes | 50 MB |
| Portuguese | `pt` | yes | yes | 51 MB |
| Romanian | `ro` | yes | yes | 30 MB |
| Russian | `ru` | yes | — | 15 MB |
| Albanian | `sq` | yes | yes | 31 MB |
| Swedish | `sv` | yes | yes | 31 MB |
| Turkish | `tr` | yes | yes | 30 MB |
| Ukrainian | `uk` | yes | yes | 40 MB |
| Chinese (Simplified) | `zh` | — | yes | 37 MB |

Russian has only Russian → English, Chinese and Japanese only English → them:
Mozilla has not released the other direction yet. The folder of each
direction is `translate/<from>-<to>/<Mozilla's folder>/`.

Each folder holds the files exactly as Mozilla publishes them (gzip):
`model.*.intgemm.alphas.bin.gz`, `lex.50.50.*.s2t.bin.gz` and `vocab.*.spm.gz`
(Chinese and Japanese: `srcvocab.*.spm.gz` and `trgvocab.*.spm.gz`).
`translate/index.json` records where they came from (Mozilla's model registry
`models.json` and when it was generated), each file's unpacked size and
SHA-256, and Mozilla's quality scores (flores200-plus).

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
3. Add the direction to `translate/index.json` with each file's unpacked
   size, download size and SHA-256 (the model's must equal Mozilla's
   `uncompressedHash`), and add the row above.
4. In koulaxizis/oros run `node translate/make-models.js <this checkout>`:
   it writes the `MODELS` table of `translate/engine.js` from `index.json`.

GitHub Pages serves up to 1 GB per site: a direction is 15 to 30 MB, all of
them together about 885 MB, so a language more than these needs a second
repository.
