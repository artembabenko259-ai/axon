#!/usr/bin/env python3
"""
Merge .axon/docs/content/<lang>/*.json chapter files into a single DocsLocale JSON
for the Zenith web portal (zenith-web/locales/{lang}.json).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

SUPPORTED_LANGS = ("en", "ru", "ua")
CHAPTER_PATTERN = re.compile(r"^(\d{2})_.+\.json$")


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def content_dir(workspace: Path | None = None, lang: str = "en") -> Path:
    return (workspace or Path.cwd()) / ".axon" / "docs" / "content" / lang


def list_chapter_files(lang_dir: Path) -> list[Path]:
    if not lang_dir.is_dir():
        return []
    files = [p for p in lang_dir.glob("*.json") if CHAPTER_PATTERN.match(p.name)]
    return sorted(files, key=lambda p: p.name)


def load_chapter(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def merge_lang(workspace: Path, lang: str) -> dict:
    lang_dir = content_dir(workspace, lang)
    chapters = list_chapter_files(lang_dir)

    if not chapters:
        raise FileNotFoundError(
            f"No chapter files in {lang_dir}. Expected NN_name.json files."
        )

    meta: dict | None = None
    sections: list[dict] = []
    page_counter = 0

    for chapter_path in chapters:
        chapter = load_chapter(chapter_path)
        if meta is None:
            meta = chapter.get("meta", {})
        elif chapter.get("meta"):
            # Later chapters may extend meta.stats only
            extra = chapter.get("meta", {})
            if "stats" in extra:
                meta.setdefault("stats", {}).update(extra["stats"])

        for section in chapter.get("sections", []):
            section = dict(section)
            subs = []
            for sub in section.get("subsections", []):
                page_counter += 1
                entry = dict(sub)
                entry.setdefault("page", page_counter)
                subs.append(entry)
            section["subsections"] = subs
            sections.append(section)

    if meta is None:
        meta = {
            "title": "AXON Knowledge Base",
            "lead": "The AXON Bible",
            "bookSubtitle": "Deep-dive manual",
        }

    meta["totalPages"] = page_counter
    meta["chapterCount"] = len(sections)
    meta["mergedFrom"] = [p.name for p in chapters]

    return {"meta": meta, "sections": sections}


def write_merged_locale(workspace: Path, lang: str, output_dir: Path | None = None) -> Path:
    merged = merge_lang(workspace, lang)
    out_root = output_dir or project_root() / "zenith-web" / "locales"
    out_root.mkdir(parents=True, exist_ok=True)
    out_path = out_root / f"{lang}.json"
    out_path.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return out_path


def merge_all(workspace: Path | None = None) -> dict[str, Path]:
    ws = workspace or Path.cwd()
    written: dict[str, Path] = {}
    for lang in SUPPORTED_LANGS:
        lang_dir = content_dir(ws, lang)
        if not list_chapter_files(lang_dir):
            continue
        written[lang] = write_merged_locale(ws, lang)
    return written


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Merge AXON Bible chapter JSON files")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--lang", choices=SUPPORTED_LANGS, default=None)
    args = parser.parse_args()

    if args.lang:
        path = write_merged_locale(args.workspace.resolve(), args.lang)
        print(f"Merged -> {path}")
    else:
        for lang, path in merge_all(args.workspace.resolve()).items():
            print(f"[{lang}] -> {path}")
