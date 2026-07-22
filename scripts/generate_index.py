#!/usr/bin/env python3
"""
Generate docs/index.json: a listing of every content/**/*.bes file (Fixlets,
Tasks, Analyses, Baselines, ...) with metadata parsed from its XML.

GitHub Pages publishes the whole repo root (see index.html there), so
content/ is already served as-is - this script does not copy or duplicate
any .bes file. It only enumerates content/ and writes docs/index.json for
the viewer's (index.html + docs/app.js) file list and search.

Run from the repo root:
    python scripts/generate_index.py
"""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
#SOURCE_ROOT = REPO_ROOT / "Test Content"
SOURCE_ROOT = REPO_ROOT
OUTPUT_PATH = REPO_ROOT / "docs" / "index.json"

KNOWN_ROOT_TAGS = {"Task", "Fixlet", "Analysis", "Baseline", "TaskCondition", "ComputerGroup"}


def find_source_bes_files():
    for path in sorted(SOURCE_ROOT.rglob("*.bes")):
        yield path.relative_to(SOURCE_ROOT)


def child_text(el, tag):
    child = el.find(tag)
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def describe(source_rel_path: Path):
    abs_path = SOURCE_ROOT / source_rel_path
    # This file's path within the repo (content/ lives at the repo root) - doubles as
    # docs/app.js's local fetch/download URL (relative to the published index.html, which
    # lives at the repo root too) and, combined with BLOB_BASE there, the "View on GitHub" link.
    #rel_path = Path("content") / source_rel_path
    rel_path = source_rel_path
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
    rel_paths = list(find_source_bes_files())
    entries = [describe(rel) for rel in rel_paths]
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
