"use strict";

/* ---------------------------------------------------------------------
 * Config: figure out which repo/branch to read from.
 * Defaults to bigfix/content@master; auto-detects owner/repo when this
 * page is served as a normal GitHub Pages project site
 * (https://<owner>.github.io/<repo>/...), so a fork of this repo works
 * out of the box too.
 * ------------------------------------------------------------------- */
const DEFAULT_OWNER = "jwalker107";
const DEFAULT_REPO = "BigFix";
const DEFAULT_BRANCH = "master";

function detectRepoConfig() {
  const host = location.hostname; // e.g. bigfix.github.io
  const parts = location.pathname.split("/").filter(Boolean); // e.g. ["content", "docs", ...]
  const ghPagesMatch = host.match(/^([^.]+)\.github\.io$/);
  if (ghPagesMatch && parts.length > 0) {
    return { owner: ghPagesMatch[1], repo: parts[0], branch: DEFAULT_BRANCH };
  }
  return { owner: DEFAULT_OWNER, repo: DEFAULT_REPO, branch: DEFAULT_BRANCH };
}

const REPO = detectRepoConfig();
const RAW_BASE = `https://raw.githubusercontent.com/${REPO.owner}/${REPO.repo}/${REPO.branch}/`;
const BLOB_BASE = `https://github.com/${REPO.owner}/${REPO.repo}/blob/${REPO.branch}/`;
// Served alongside this page (same origin), so it always matches the current fork/branch's
// deployment without needing owner/repo in the URL - and isn't subject to the GitHub REST
// API's unauthenticated rate limit the way the old git/trees call was.
const INDEX_URL = "index.json";

const repoLinkEl = document.getElementById("repo-link");
repoLinkEl.href = `https://github.com/${REPO.owner}/${REPO.repo}`;
repoLinkEl.textContent = `github.com/${REPO.owner}/${REPO.repo}`;

const treeRootEl = document.getElementById("tree-root");
const statusTextEl = document.getElementById("status-text");
const refreshBtn = document.getElementById("refresh-btn");
const searchBoxEl = document.getElementById("search-box");
const mainEl = document.getElementById("main");

let allFiles = []; // [{path, name, dir}]
let activePath = null;

/* ---------------------------------------------------------------------
 * File list loading
 * ------------------------------------------------------------------- */

async function loadFileList(forceRefresh) {
  statusTextEl.textContent = "Loading file list…";
  try {
    // no-store on manual refresh so a stale CDN/browser cache doesn't hide a just-published index.
    const res = await fetch(INDEX_URL, forceRefresh ? { cache: "no-store" } : {});
    if (!res.ok) throw new Error(`Could not load index.json (${res.status})`);
    const data = await res.json();
    allFiles = (data.files || []).slice().sort((a, b) => a.path.localeCompare(b.path));
    renderTree(allFiles);
    statusTextEl.textContent = `${allFiles.length} files`;
  } catch (err) {
    statusTextEl.textContent = "Failed to load file list";
    treeRootEl.innerHTML = "";
    const box = document.createElement("div");
    box.className = "error-box";
    box.style.margin = "8px 0";
    box.textContent = err.message || String(err);
    const retry = document.createElement("button");
    retry.textContent = "Retry";
    retry.onclick = () => loadFileList(true);
    box.appendChild(document.createElement("br"));
    box.appendChild(retry);
    treeRootEl.appendChild(box);
  }
}

/* ---------------------------------------------------------------------
 * Sidebar tree rendering + filtering
 * ------------------------------------------------------------------- */

function renderTree(files) {
  const query = searchBoxEl.value.trim().toLowerCase();
  const filtered = query ? files.filter((f) => f.path.toLowerCase().includes(query)) : files;

  const groups = new Map();
  for (const f of filtered) {
    if (!groups.has(f.dir)) groups.set(f.dir, []);
    groups.get(f.dir).push(f);
  }

  treeRootEl.innerHTML = "";
  if (filtered.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-note";
    empty.textContent = "No files match.";
    treeRootEl.appendChild(empty);
    return;
  }

  for (const [dir, dirFiles] of [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0]))) {
    const group = document.createElement("div");
    group.className = "tree-group";

    const label = document.createElement("div");
    label.className = "tree-group-label";
    label.innerHTML = `<span class="chevron">▼</span><span></span>`;
    label.querySelector("span:last-child").textContent = `${dir} (${dirFiles.length})`;
    label.onclick = () => group.classList.toggle("collapsed");
    group.appendChild(label);

    const list = document.createElement("div");
    list.className = "tree-files";
    for (const f of dirFiles) {
      const item = document.createElement("div");
      item.className = "tree-file";
      item.dataset.path = f.path;
      if (f.path === activePath) item.classList.add("active");
      const dot = document.createElement("span");
      dot.className = `type-dot ${typeDotClass(f.type)}`;
      const label2 = document.createElement("span");
      label2.textContent = f.name.replace(/\.bes$/i, "");
      item.title = f.title && f.title !== f.name ? `${f.title} (${f.type || "Other"})` : f.type || "";
      item.appendChild(dot);
      item.appendChild(label2);
      item.onclick = () => selectFile(f.path);
      list.appendChild(item);
    }
    group.appendChild(list);
    treeRootEl.appendChild(group);
  }
}

function typeDotClass(type) {
  switch (type) {
    case "Fixlet": return "fixlet";
    case "Task": return "task";
    case "Analysis": return "analysis";
    case "Baseline": return "baseline";
    default: return "other";
  }
}

searchBoxEl.addEventListener("input", () => renderTree(allFiles));
refreshBtn.addEventListener("click", () => loadFileList(true));

/* ---------------------------------------------------------------------
 * File selection + fetch + parse
 * ------------------------------------------------------------------- */

function selectFile(path) {
  activePath = path;
  const url = new URL(location.href);
  url.searchParams.set("file", path);
  history.pushState({ path }, "", url);
  document.querySelectorAll(".tree-file").forEach((el) => {
    el.classList.toggle("active", el.dataset.path === path);
  });
  loadAndRenderFile(path);
}

window.addEventListener("popstate", () => {
  const path = new URL(location.href).searchParams.get("file");
  if (path) {
    activePath = path;
    loadAndRenderFile(path);
  }
});

async function loadAndRenderFile(path) {
  mainEl.innerHTML = `<div class="spinner-line">Loading ${escapeText(path)}…</div>`;
  try {
    const res = await fetch(RAW_BASE + path.split("/").map(encodeURIComponent).join("/"));
    if (!res.ok) throw new Error(`Could not fetch file (${res.status})`);
    const xmlText = await res.text();
    const doc = new DOMParser().parseFromString(xmlText, "application/xml");
    const parserError = doc.querySelector("parsererror");
    if (parserError) throw new Error("This file could not be parsed as XML.");
    renderDocument(doc, path);
  } catch (err) {
    mainEl.innerHTML = "";
    const box = document.createElement("div");
    box.className = "error-box";
    box.textContent = err.message || String(err);
    const retry = document.createElement("button");
    retry.textContent = "Retry";
    retry.onclick = () => loadAndRenderFile(path);
    box.appendChild(document.createElement("br"));
    box.appendChild(retry);
    mainEl.appendChild(box);
  }
}

/* ---------------------------------------------------------------------
 * Rendering a parsed .bes document
 * ------------------------------------------------------------------- */

function renderDocument(doc, path) {
  const bes = doc.documentElement;
  const root = bes.querySelector(":scope > Task, :scope > Fixlet, :scope > Analysis, :scope > Baseline, :scope > TaskCondition, :scope > ComputerGroup");
  mainEl.innerHTML = "";

  if (!root) {
    renderUnknown(doc, path);
    return;
  }

  const docType = root.tagName;
  const title = textOf(root, "Title") || path.split("/").pop();
  const description = textOf(root, "Description");
  const relevances = [...root.querySelectorAll(":scope > Relevance")].map((el) => el.textContent.trim());
  const source = textOf(root, "Source");
  const sourceDate = textOf(root, "SourceReleaseDate");
  const severity = textOf(root, "SourceSeverity");
  const domain = textOf(root, "Domain");
  const downloadSize = textOf(root, "DownloadSize");

  // Header -----------------------------------------------------------
  const titleRow = document.createElement("div");
  titleRow.className = "title-row";
  const h1 = document.createElement("h1");
  h1.className = "doc-title";
  h1.textContent = title;
  titleRow.appendChild(h1);

  const badges = document.createElement("div");
  badges.className = "badges";
  badges.appendChild(makeBadge(docType, "doctype"));
  if (severity) badges.appendChild(makeBadge(severity, `severity-${severity.toLowerCase()}`));
  if (domain) badges.appendChild(makeBadge(domain, "domain"));
  titleRow.appendChild(badges);
  mainEl.appendChild(titleRow);

  const metaLine = document.createElement("div");
  metaLine.className = "meta-line";
  if (source) metaLine.appendChild(metaSpan("Source", source));
  if (sourceDate) metaLine.appendChild(metaSpan("Released", sourceDate));
  if (downloadSize) metaLine.appendChild(metaSpan("Download size", formatBytes(downloadSize)));
  const ghLink = document.createElement("span");
  ghLink.innerHTML = `<a href="${BLOB_BASE + path.split("/").map(encodeURIComponent).join("/")}" target="_blank" rel="noopener">View on GitHub</a>`;
  metaLine.appendChild(ghLink);

  const indexEntry = allFiles.find((f) => f.path === path);
  if (indexEntry && indexEntry.downloadUrl) {
    const dlSpan = document.createElement("span");
    const dlLink = document.createElement("a");
    dlLink.href = indexEntry.downloadUrl;
    dlLink.textContent = "Download";
    dlLink.setAttribute("download", indexEntry.name);
    dlSpan.appendChild(dlLink);
    metaLine.appendChild(dlSpan);
  }
  mainEl.appendChild(metaLine);

  // Description --------------------------------------------------------
  if (description) {
    mainEl.appendChild(sectionLabel("Description"));
    const card = document.createElement("div");
    card.className = "card description-box";
    card.innerHTML = sanitizeHtml(description);
    mainEl.appendChild(card);
  }

  // Relevance -----------------------------------------------------------
  if (relevances.length) {
    mainEl.appendChild(sectionLabel("Relevance", relevances.length));
    mainEl.appendChild(renderRelevanceList(relevances));
  }

  // Type-specific body ---------------------------------------------------
  if (docType === "Task" || docType === "Fixlet") {
    renderActions(root);
  } else if (docType === "Analysis") {
    renderProperties(root);
  } else if (docType === "Baseline") {
    renderBaselineComponents(root);
  }

  // Raw XML fallback ------------------------------------------------------
  mainEl.appendChild(renderRawXmlDetails(doc));
}

function renderActions(root) {
  const actions = [...root.querySelectorAll(":scope > DefaultAction, :scope > Action")];
  if (!actions.length) return;

  mainEl.appendChild(sectionLabel("Action Script", actions.length > 1 ? actions.length : null));

  const tabsWrap = document.createElement("div");
  const tabs = document.createElement("div");
  tabs.className = "tabs";
  const panels = [];

  actions.forEach((action, i) => {
    const id = action.getAttribute("ID") || `Action${i + 1}`;
    const scriptEl = action.querySelector(":scope > ActionScript");
    const mime = scriptEl ? scriptEl.getAttribute("MIMEType") || "" : "";
    const script = scriptEl ? scriptEl.textContent.trim() : "(no ActionScript)";
    const label = actionLabel(action) || id;

    const tabBtn = document.createElement("button");
    tabBtn.className = "tab-btn" + (i === 0 ? " active" : "");
    tabBtn.textContent = label;
    tabBtn.onclick = () => {
      tabs.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      tabBtn.classList.add("active");
      panels.forEach((p, pi) => p.style.display = pi === i ? "" : "none");
    };
    tabs.appendChild(tabBtn);

    const panel = document.createElement("div");
    panel.className = "actionscript-box";
    panel.style.display = i === 0 ? "" : "none";
    panel.innerHTML = `
      <div class="actionscript-titlebar">
        <div class="dot red"></div><div class="dot yellow"></div><div class="dot green"></div>
        <span class="fname"></span>
      </div>`;
    panel.querySelector(".fname").textContent = `${id}${mime ? " · " + mime : ""}`;
    const textarea = document.createElement("textarea");
    textarea.className = "actionscript";
    textarea.readOnly = true;
    textarea.value = script;
    panel.appendChild(textarea);
    panels.push(panel);
  });

  tabsWrap.appendChild(tabs);
  panels.forEach((p) => tabsWrap.appendChild(p));
  mainEl.appendChild(tabsWrap);
}

function actionLabel(action) {
  const desc = action.querySelector(":scope > Description");
  if (!desc) return null;
  const pre = desc.querySelector("PreLink")?.textContent || "";
  const link = desc.querySelector("Link")?.textContent || "";
  const post = desc.querySelector("PostLink")?.textContent || "";
  const combined = (pre + link + post).trim();
  return combined.length > 40 ? combined.slice(0, 37) + "…" : combined || null;
}

function renderProperties(root) {
  const props = [...root.querySelectorAll(":scope > Property")];
  if (!props.length) return;
  mainEl.appendChild(sectionLabel("Properties", props.length));
  const list = document.createElement("div");
  list.className = "property-list";
  props.forEach((prop, i) => {
    const name = prop.getAttribute("Name") || `Property ${i + 1}`;
    list.appendChild(relevanceItem(i + 1, prop.textContent.trim(), name));
  });
  mainEl.appendChild(list);
}

function renderBaselineComponents(root) {
  const components = [...root.querySelectorAll(":scope > BaselineComponent")];
  if (!components.length) return;
  mainEl.appendChild(sectionLabel("Components", components.length));
  const list = document.createElement("div");
  list.className = "property-list";
  components.forEach((c, i) => {
    const name = textOf(c, "Name") || `Component ${i + 1}`;
    const relevance = textOf(c, "Relevance") || "(no relevance)";
    list.appendChild(relevanceItem(i + 1, relevance, name));
  });
  mainEl.appendChild(list);
}

function renderUnknown(doc, path) {
  const box = document.createElement("div");
  box.className = "error-box";
  box.textContent = "This file's structure wasn't recognized (expected a Task, Fixlet, Analysis, or Baseline). Showing raw XML instead.";
  mainEl.appendChild(box);
  mainEl.appendChild(renderRawXmlDetails(doc, true));
}

function renderRawXmlDetails(doc, open) {
  const details = document.createElement("details");
  details.className = "raw-xml";
  if (open) details.open = true;
  const summary = document.createElement("summary");
  summary.textContent = "View raw XML";
  const pre = document.createElement("pre");
  pre.textContent = new XMLSerializer().serializeToString(doc);
  details.appendChild(summary);
  details.appendChild(pre);
  return details;
}

/* ---------------------------------------------------------------------
 * Small render helpers
 * ------------------------------------------------------------------- */

function renderRelevanceList(items) {
  const list = document.createElement("div");
  list.className = "relevance-list";
  items.forEach((text, i) => list.appendChild(relevanceItem(i + 1, text)));
  return list;
}

function relevanceItem(index, text, name) {
  const item = document.createElement("div");
  item.className = "relevance-item";
  const idx = document.createElement("div");
  idx.className = "idx";
  idx.textContent = String(index);
  const body = document.createElement("div");
  body.className = "item-body";
  if (name) {
    const nameEl = document.createElement("div");
    nameEl.className = "item-name";
    nameEl.textContent = name;
    body.appendChild(nameEl);
  }
  const textarea = document.createElement("textarea");
  textarea.readOnly = true;
  textarea.value = text;
  textarea.rows = Math.min(8, Math.max(1, Math.ceil(text.length / 90)));
  body.appendChild(textarea);
  item.appendChild(idx);
  item.appendChild(body);
  return item;
}

function sectionLabel(text, count) {
  const label = document.createElement("div");
  label.className = "section-label";
  label.appendChild(document.createTextNode(text));
  if (count) {
    const span = document.createElement("span");
    span.className = "count";
    span.textContent = String(count);
    label.appendChild(span);
  }
  return label;
}

function makeBadge(text, cls) {
  const span = document.createElement("span");
  span.className = `badge ${cls}`;
  span.textContent = text;
  return span;
}

function metaSpan(label, value) {
  const span = document.createElement("span");
  const b = document.createElement("b");
  b.textContent = label + ": ";
  span.appendChild(b);
  span.appendChild(document.createTextNode(value));
  return span;
}

function textOf(root, tag) {
  const el = root.querySelector(`:scope > ${tag}`);
  return el ? el.textContent.trim() : "";
}

function formatBytes(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return value;
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function escapeText(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

/* ---------------------------------------------------------------------
 * Minimal allowlist HTML sanitizer for <Description> content.
 * Descriptions come from files in the repo (or any fork/PR of it), so
 * they are treated as untrusted input and never injected as raw innerHTML.
 * ------------------------------------------------------------------- */

const ALLOWED_TAGS = new Set([
  "P", "A", "STRONG", "B", "EM", "I", "U", "BR", "UL", "OL", "LI", "SPAN",
  "H1", "H2", "H3", "H4", "H5", "H6", "BLOCKQUOTE", "CODE", "PRE",
  "TABLE", "THEAD", "TBODY", "TR", "TD", "TH", "IMG",
]);

function sanitizeHtml(html) {
  const template = document.createElement("template");
  template.innerHTML = html;
  sanitizeNode(template.content);
  return template.innerHTML;
}

function sanitizeNode(parent) {
  const walker = [...parent.childNodes];
  for (const node of walker) {
    if (node.nodeType === Node.COMMENT_NODE) {
      node.remove();
      continue;
    }
    if (node.nodeType !== Node.ELEMENT_NODE) continue;

    if (!ALLOWED_TAGS.has(node.tagName)) {
      // Unwrap: keep children (usually just text) but drop the disallowed tag itself.
      const parentNode = node.parentNode;
      while (node.firstChild) parentNode.insertBefore(node.firstChild, node);
      parentNode.removeChild(node);
      continue;
    }

    for (const attr of [...node.attributes]) {
      const name = attr.name.toLowerCase();
      if (node.tagName === "A" && name === "href") {
        if (!/^(https?:|mailto:)/i.test(attr.value)) node.removeAttribute(attr.name);
      } else if (node.tagName === "IMG" && (name === "src" || name === "alt" || name === "width" || name === "height")) {
        if (name === "src" && !/^https?:/i.test(attr.value)) node.removeAttribute(attr.name);
      } else {
        node.removeAttribute(attr.name);
      }
    }
    if (node.tagName === "A" && node.hasAttribute("href")) {
      node.setAttribute("target", "_blank");
      node.setAttribute("rel", "noopener noreferrer");
    }

    sanitizeNode(node);
  }
}

/* ---------------------------------------------------------------------
 * Boot
 * ------------------------------------------------------------------- */

(async function init() {
  await loadFileList(false);
  const initialPath = new URL(location.href).searchParams.get("file");
  if (initialPath) {
    activePath = initialPath;
    renderTree(allFiles);
    loadAndRenderFile(initialPath);
  }
})();
