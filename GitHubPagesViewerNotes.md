# GitHub Pages Content Viewer — Project Overview

A browser-based viewer for BigFix Fixlets, Tasks, Analyses, and Baselines, served entirely as a static GitHub Pages site published from the repo root. The viewer fetches file content directly from `content/` (the same directory you edit/commit to) — it does **not** call back to the GitHub API, and keeps no duplicate copy of any `.bes` file anywhere in the repo. The only outbound link to the source repo is the explicit "View on GitHub" link.

## Repository Structure

- **`index.html`** (repo root) — the Pages entry point. References `docs/app.js`, `docs/style.css`, and `docs/index.json` explicitly, since it lives at the repo root while its supporting assets stay under `docs/`.
- **`content/`** (repo root) — the canonical set of `.bes` files (Fixlets, Tasks, Analyses, Baselines, ...). This is the thing to edit/commit to when adding or changing content. Served as-is by Pages; nothing copies it anywhere.
- **`docs/`** — supporting assets for the viewer (not the Pages site root itself):
  - `app.js` — all viewer logic: index loading, tree rendering, file fetch/parse/render, description sanitizer.
  - `style.css` — styling.
  - `vendor/` — vendored third-party code:
    - `hljs-bigfix-relevance.js` — highlight.js grammar for BigFix Relevance language.
    - `LICENSE-hljs-bigfix-relevance.txt` — Apache-2.0 license for the vendored grammar.
  - `index.json` — **generated**: the file listing consumed by `app.js` for the sidebar/search. Overwritten by `scripts/generate_index.py`.
- **`scripts/generate_index.py`** — enumerates `content/` and (re)writes `docs/index.json`. See below.
- **`.github/workflows/update-index.yml`** — runs `generate_index.py` on pushes that touch `content/**` and commits the result.

## Index Generation (`scripts/generate_index.py`)

Run from the repo root: `python scripts/generate_index.py`. Every run:

1. **Enumerates** every `content/**/*.bes` file (`find_source_bes_files`).
2. **Writes `docs/index.json`** (`describe` + `main`): for each file, parses the XML root (`Task`/`Fixlet`/`Analysis`/`Baseline`/`TaskCondition`/`ComputerGroup`) and records:
   - `path` — the file's path **in the source repo**, e.g. `content/Analyses/Foo.bes`. Doubles as a path relative to `index.html` (which lives at the repo root, same as `content/`) that resolves directly to the real file — this dual meaning is exactly what lets `app.js` use the same field for both the "View on GitHub" link and the local fetch/download URL, with no copy step in between.
   - `name`, `dir`, `type`, `title`, `source`, `sourceReleaseDate`, `severity`, `domain`, `downloadSize`, `relevanceCount`.

That's it — no file copying, no pruning. The script's only side effect is `docs/index.json`.

**Triggering (`.github/workflows/update-index.yml`):**

- Push to `main` touching `content/**` (paths filter).
- Manual `workflow_dispatch`.
- Concurrency-limited per ref; commits `docs/index.json` back with `[skip ci]` only if something actually changed.
- Requires `contents: write` permission.

## Viewer App (`docs/app.js`, loaded by the root `index.html`)

### Repo/branch config — only for the "View on GitHub" link

`app.js` auto-detects `{owner, repo, branch}` from the page's own URL when served as a normal `<owner>.github.io/<repo>/` project site (falls back to hardcoded `DEFAULT_OWNER`/`DEFAULT_REPO`/`DEFAULT_BRANCH` otherwise, e.g. when run locally). This is used **only** to build `BLOB_BASE` (`https://<GITHUB_SITE>/<owner>/<repo>/blob/<branch>/`) for the "View on GitHub" link in the file header — nothing else in the app depends on it. `GITHUB_SITE` is hardcoded to the enterprise host (`github01.hclpnp.com`).

### Local content fetch — no GitHub API involved, no duplicate files

`INDEX_URL` is `"docs/index.json"` and `localContentUrl(path)` URL-encodes each path segment of `path` (e.g. `content/Analyses/Foo.bes`) and returns it as-is — both are **relative** URLs resolved against wherever `index.html` itself is being served from (the repo root). Since `content/` and `docs/` are real, live directories at that same root, these relative URLs land on the actual files with no intermediate copy:

- `loadAndRenderFile(path)` does a plain `fetch(localContentUrl(path))` — no headers, no auth, no CORS concerns.
- The "Download" link sets `href`/`download` directly to `localContentUrl(path)` — same-origin URLs get the native `download` attribute honored by the browser, so no fetch-to-blob workaround is needed.

**If `index.html` ever moves again** (e.g. back under `docs/`, or into a different subdirectory), every one of these relative paths needs re-deriving relative to its new location - they aren't rooted with a leading `/`, so they resolve against the *document's* URL, not any fixed site root.

### File list (sidebar)

- `loadFileList()` fetches `docs/index.json`, sorts by `path`, and renders a collapsible tree grouped by `dir`.
- Search box does a case-insensitive substring filter over `path`.
- Refresh button re-fetches `docs/index.json` with `cache: "no-store"`.
- Selecting a file updates `?file=<path>` via `history.pushState` (so links/back-forward work) and calls `loadAndRenderFile`.

### File rendering (`renderDocument` + helpers)

- Header: title, type/severity/domain badges, source/release-date/download-size meta line, "View on GitHub" link, "Download" link.
- **Description**: rendered as sanitized HTML (see below), not plain text.
- **Relevance**: syntax-highlighted via the vendored `bigfix-relevance` highlight.js grammar.
- **Task/Fixlet**: tabbed ActionScript viewer (plain read-only `<textarea>` per action, no syntax highlighting).
- **Analysis**: Property list (name + highlighted relevance).
- **Baseline**: Component list (name + highlighted relevance).
- Unrecognized/unparseable documents fall back to a raw-XML `<details>` view.

### Description HTML sanitizer (`renderSanitizedHtml`/`sanitizeNode`)

Descriptions can contain HTML (possibly from a CDATA section) and are treated as untrusted input — parsed via a `<template>` (inert DOM, nothing executes) and walked node-by-node:

- **Allowed tags**: `P A STRONG B EM I U BR UL OL LI SPAN H1-H6 BLOCKQUOTE CODE PRE TABLE THEAD TBODY TR TD TH IMG INPUT TEXTAREA`. Anything else is unwrapped (tag dropped, children kept).
- **`<SCRIPT>`/`<STYLE>`**: never executed or applied. Replaced with a collapsed "SCRIPT"/"STYLE" toggle button (`makeEmbeddedCodeBlock`) that expands into a read-only, syntax-highlighted (`javascript`/`css`) code panel on click.
- **`<INPUT>`**: only rendered live if its `type` is in a safe/inert allowlist (`text password checkbox radio number date datetime-local time email tel url range color search month week`). Anything else (`file image submit button reset hidden ...`) is replaced with a highlighted, inert snippet of the original tag (`describeUnsupportedElement`) instead of being silently dropped.
- **Attribute allowlist per tag** (`TAG_ATTR_ALLOWLIST`): only specific attributes survive (e.g. `A`→`href`, `IMG`→`src/alt/width/height`, `INPUT`→`type/value/placeholder/checked/disabled/readonly/maxlength/min/max/step/size`, `TEXTAREA`→`rows/cols/placeholder/disabled/readonly/maxlength`). This is what blocks `onclick`/`onfocus`-style attribute-based script execution even with no `<script>` tag involved.
- Rendered `<INPUT>` elements always get `autocomplete="off"` forced on, regardless of the original markup, so they can't get silently populated from the browser's saved autofill data.
- `<A>` hrefs are restricted to `http(s):`/`mailto:` and get `target="_blank" rel="noopener noreferrer"`; `<IMG>` `src` restricted to `http(s):`.

### Styling notes (`style.css`)

- Dark "code box" look (`--code-bg`/`--code-text`) shared by the ActionScript panels and the embedded SCRIPT/STYLE code panels.
- `vs2015` highlight.js theme is loaded from cdnjs (`index.html`) for full JS/CSS token coverage; the app's own `.hljs-comment/-keyword/-string/-number` overrides (for the BigFix Relevance grammar) are declared after it in `style.css` so they still win for that language.

## Removed Functionality (do not resurrect without a reason)

An earlier iteration of this viewer fetched file content live from a GitHub Enterprise Server instance instead of from the repo's own published content. All of that has been deliberately removed:

- **PAT-based authentication**: "Connect"/"Disconnect" button, "Generate Token" button/row, the `<dialog>` sign-in form, `localStorage`-backed token (`bf-gh-token`), and the `authFetch` wrapper (401/403 retry-with-token logic).
- **GitHub REST API usage**: the `/api/v3/repos/.../contents/...` calls (`contentsApiUrl`), including the `application/vnd.github.v3.raw` media-type trick used to get raw bytes back.
- **Direct `raw.<host>` fetches and their CORS workaround**: the enterprise raw-content host doesn't implement CORS preflight (`OPTIONS` → 405, no `Access-Control-*` headers), which is *why* the API-based fetch existed in the first place. Moot now — nothing fetches from GitHub at all except the plain-navigation "View on GitHub" link, which isn't subject to CORS.
- **Blob-download workaround**: `downloadAsFile()` (fetch → `Blob` → `URL.createObjectURL` → synthetic `<a click>`) existed only because the `download` attribute doesn't work cross-origin. Content is same-origin now, so the plain `href`/`download` attributes work natively.
- **`docs/content/` copy step**: an intermediate iteration copied `content/` into `docs/content/` (via `generate_index.py`) so a `docs/`-rooted Pages site could serve file bytes same-origin. Once Pages was switched to publish the whole repo root instead of just `docs/`, this copy became unnecessary — `content/` is already served as-is, so it was removed along with the sync/prune logic in `generate_index.py` and the directory itself was deleted.

If GitHub API/auth-related code, or a `docs/content`-style copy step, reappears in a future change, make sure it's for a genuinely new reason - not by accident.

## Deployment

- **Pages settings**: Settings → Pages → Deploy from a branch → `main` / `/ (root)`. Must be the repo root, not `/docs` — `index.html` lives at the root and references `docs/app.js` etc. by relative path.
- **Publishing new/changed content**: edit files under `content/`, push to `main`, and the workflow regenerates `docs/index.json` automatically. Or run `python scripts/generate_index.py` locally and commit the result yourself.
- **Local testing**: serve the repo root with any static file server (e.g. `python -m http.server` from the repo root) and open `index.html`. No token/config needed for content to load — only `DEFAULT_OWNER`/`DEFAULT_REPO`/`DEFAULT_BRANCH`/`GITHUB_SITE` in `app.js` affect anything, and only the "View on GitHub" link.
- **Forks**: cloning and enabling Pages works out of the box; `detectRepoConfig()` in `app.js` auto-detects owner/repo from the Pages URL for the "View on GitHub" link when served as `<owner>.github.io/<repo>/`.

## Future Considerations

- ActionScript syntax highlighting isn't implemented (plain read-only `<textarea>`); could reuse the same `javascript`/`css`-style highlight.js treatment used for embedded SCRIPT/STYLE blocks if a BigFix ActionScript grammar were vendored.
- File list is loaded all-at-once from `index.json`; fine at current content volume, would need pagination/virtualization at much larger scale.
- No offline/service-worker support; every load re-fetches `index.json` (browser-cached unless "Refresh" is clicked) and each file's content on selection.
