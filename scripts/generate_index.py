#!/usr/bin/env python3
"""
Generate docs/index.json: a static listing of every .bes file in the repo
(Fixlets, Tasks, Analyses, Baselines, ...) with basic metadata.

The GitHub Pages viewer (docs/app.js) reads this file directly instead of
calling the GitHub REST API to list the repo tree, which avoids the
unauthenticated API's low rate limit (60 requests/hour/IP). Full file
content (ActionScript, relevance, etc.) is still fetched on demand from
raw.githubusercontent.com only when a user opens a specific file.

Run from the repo root:
    python scripts/generate_index.py
"""
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "docs" / "index.json"

# Directories that are never content to list (viewer app, schemas, git internals, API samples/scripts).
EXCLUDED_DIR_PARTS = {".git", "docs", "schema"}

KNOWN_ROOT_TAGS = {"Task", "Fixlet", "Analysis", "Baseline", "TaskCondition", "ComputerGroup"}

# Same fallback repo/branch docs/app.js uses when it can't detect a fork from the page URL.
DEFAULT_OWNER = "jwalker107"
DEFAULT_REPO = "BigFix"
DEFAULT_BRANCH = "master"


def resolve_raw_base():
    """Build the raw.githubusercontent.com base URL for this run.

    GITHUB_REPOSITORY / GITHUB_REF_NAME are set automatically inside GitHub
    Actions, so a fork's own workflow run produces download links pointing at
    the fork - not this upstream repo. Falls back to the same defaults
    docs/app.js uses when run locally, outside of Actions.
    """
    owner_repo = os.environ.get("GITHUB_REPOSITORY", "")
    owner, _, repo = owner_repo.partition("/")
    if not owner or not repo:
        owner, repo = DEFAULT_OWNER, DEFAULT_REPO
    branch = os.environ.get("GITHUB_REF_NAME") or DEFAULT_BRANCH
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/"


RAW_BASE = resolve_raw_base()


def find_bes_files():
    for path in sorted(REPO_ROOT.rglob("*.bes")):
        rel = path.relative_to(REPO_ROOT)
        if EXCLUDED_DIR_PARTS.intersection(rel.parts):
            continue
        yield rel


def child_text(el, tag):
    child = el.find(tag)
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def describe(rel_path: Path):
    abs_path = REPO_ROOT / rel_path
    posix_path = rel_path.as_posix()
    entry = {
        "path": posix_path,
        "name": rel_path.name,
        "dir": rel_path.parent.as_posix() if rel_path.parent != Path(".") else "(root)",
        "type": "Other",
        "title": rel_path.stem,
        "source": "",
        "sourceReleaseDate": "",
        "severity": "",
        "domain": "",
        "downloadSize": "",
        "relevanceCount": 0,
        "downloadUrl": RAW_BASE + "/".join(quote(part) for part in rel_path.parts),
    }

    try:
        tree = ET.parse(abs_path)
    except ET.ParseError as e:
        print(f"warning: skipping unparsable file {posix_path}: {e}", file=sys.stderr)
        return entry

    bes = tree.getroot()
    root = None
    for tag in KNOWN_ROOT_TAGS:
        root = bes.find(tag)
        if root is not None:
            break
    if root is None:
        return entry

    entry["type"] = root.tag
    entry["title"] = child_text(root, "Title") or entry["title"]
    entry["source"] = child_text(root, "Source")
    entry["sourceReleaseDate"] = child_text(root, "SourceReleaseDate")
    entry["severity"] = child_text(root, "SourceSeverity")
    entry["domain"] = child_text(root, "Domain")
    entry["downloadSize"] = child_text(root, "DownloadSize")
    entry["relevanceCount"] = len(root.findall("Relevance"))
    return entry


def main():
    entries = [describe(rel) for rel in find_bes_files()]
    payload = {
        "files": entries,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {len(entries)} entries to {OUTPUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
