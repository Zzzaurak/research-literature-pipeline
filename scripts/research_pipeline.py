#!/usr/bin/env python3
"""Lightweight CLI for a Zotero + MinerU literature pipeline.

The CLI only uses the Python standard library. It manages project files and
uses Zotero's local API for optional BibTeX export fallback.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import tomllib
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
PROJECTS_DIR = ROOT / "projects"
TEMPLATES_DIR = ROOT / "templates"
DEFAULT_ZOTERO_BASE = "http://127.0.0.1:23119"


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "research-project"


def now_date() -> str:
    return dt.date.today().isoformat()


def write_new(path: Path, content: str, *, force: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        raise SystemExit(f"Refusing to overwrite existing file: {path}")
    path.write_text(content, encoding="utf-8")


def touch_keep(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    keep = path / ".gitkeep"
    if not keep.exists():
        keep.write_text("", encoding="utf-8")


def load_project(project_dir: Path) -> dict:
    config_path = project_dir / "project.toml"
    if not config_path.exists():
        raise SystemExit(f"Missing project config: {config_path}")
    with config_path.open("rb") as handle:
        return tomllib.load(handle)


def project_config_text(slug: str, title: str, topic: str) -> str:
    collection_name = f"Research - {title}"
    tag = f"project:{slug}"
    return f'''[project]
slug = "{slug}"
title = "{title}"
topic = "{topic}"
created = "{now_date()}"
status = "active"

[zotero]
collection_name = "{collection_name}"
collection_key = ""
tags = ["{tag}"]

[screening]
must_read_target = 5
candidate_target = 40

[mineru]
cache_dir = "papers"
markdown_filename = "paper.md"

[bibtex]
output_path = "refs/project.bib"
prefer_better_bibtex = true
'''


def init_project(args: argparse.Namespace) -> None:
    slug = slugify(args.slug or args.title)
    project_dir = PROJECTS_DIR / slug
    if project_dir.exists() and not args.force:
        raise SystemExit(f"Project already exists: {project_dir}")

    write_new(
        project_dir / "project.toml",
        project_config_text(slug, args.title, args.topic),
        force=args.force,
    )
    write_new(
        project_dir / "data" / "candidates.jsonl",
        "",
        force=args.force,
    )
    write_new(
        project_dir / "data" / "screening.tsv",
        "status\tscore\tyear\ttitle\tdoi\tarxiv_id\treason\n",
        force=args.force,
    )
    write_new(
        project_dir / "maps" / "literature-map.md",
        (TEMPLATES_DIR / "literature-map.md").read_text(encoding="utf-8").replace(
            "{{PROJECT_TITLE}}", args.title
        ),
        force=args.force,
    )
    touch_keep(project_dir / "papers")
    touch_keep(project_dir / "notes")
    touch_keep(project_dir / "refs")
    print(project_dir)


def add_candidate(args: argparse.Namespace) -> None:
    project_dir = Path(args.project_dir).resolve()
    load_project(project_dir)
    record = {
        "status": args.status,
        "score": args.score,
        "title": args.title,
        "year": args.year,
        "doi": args.doi,
        "arxiv_id": args.arxiv_id,
        "url": args.url,
        "pdf_url": args.pdf_url,
        "reason": args.reason,
        "added": now_date(),
    }
    record = {key: value for key, value in record.items() if value not in (None, "")}
    candidates_path = project_dir / "data" / "candidates.jsonl"
    candidates_path.parent.mkdir(parents=True, exist_ok=True)
    with candidates_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    screening_path = project_dir / "data" / "screening.tsv"
    if not screening_path.exists():
        screening_path.write_text(
            "status\tscore\tyear\ttitle\tdoi\tarxiv_id\treason\n",
            encoding="utf-8",
        )
    with screening_path.open("a", encoding="utf-8") as handle:
        handle.write(
            "\t".join(
                [
                    args.status or "",
                    str(args.score or ""),
                    str(args.year or ""),
                    args.title or "",
                    args.doi or "",
                    args.arxiv_id or "",
                    (args.reason or "").replace("\t", " "),
                ]
            )
            + "\n"
        )
    print(f"Added candidate to {candidates_path}")


def paper_id(key: str, title: str | None) -> str:
    if title:
        suffix = slugify(title)[:48]
        return f"{key}-{suffix}"
    return key


def make_paper_dir(args: argparse.Namespace) -> None:
    project_dir = Path(args.project_dir).resolve()
    load_project(project_dir)
    pid = paper_id(args.key, args.title)
    target = project_dir / "papers" / pid
    target.mkdir(parents=True, exist_ok=True)
    metadata = {
        "zotero_key": args.key,
        "title": args.title,
        "doi": args.doi,
        "created": now_date(),
        "pdf_path": "",
        "mineru_markdown": "paper.md",
        "reading_note": f"../../notes/{pid}.md",
    }
    write_new(
        target / "metadata.json",
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        force=args.force,
    )
    note_template = (TEMPLATES_DIR / "reading-note.md").read_text(encoding="utf-8")
    note_text = (
        note_template.replace("{{TITLE}}", args.title or args.key)
        .replace("{{ZOTERO_KEY}}", args.key)
        .replace("{{DOI}}", args.doi or "")
    )
    write_new(project_dir / "notes" / f"{pid}.md", note_text, force=args.force)
    print(target)


def http_get(url: str, timeout: int = 60) -> str:
    request = Request(url, headers={"User-Agent": "research-literature-pipeline/0.1"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", "replace")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise SystemExit(f"HTTP {exc.code}: {body[:1000]}") from exc
    except URLError as exc:
        raise SystemExit(f"Could not reach Zotero local API: {exc.reason}") from exc


def export_bib(args: argparse.Namespace) -> None:
    project_dir = Path(args.project_dir).resolve()
    config = load_project(project_dir)
    output_rel = config.get("bibtex", {}).get("output_path", "refs/project.bib")
    output_path = project_dir / output_rel
    collection_key = args.collection_key or config.get("zotero", {}).get("collection_key", "")
    if collection_key:
        endpoint = f"/api/users/0/collections/{quote(collection_key)}/items"
    else:
        endpoint = "/api/users/0/items"
    params = {"format": "bibtex"}
    if args.limit:
        params["limit"] = str(args.limit)
    base = args.zotero_base.rstrip("/")
    bibtex = http_get(f"{base}{endpoint}?{urlencode(params)}", timeout=120)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(bibtex, encoding="utf-8")
    print(output_path)


def validate_project(args: argparse.Namespace) -> None:
    project_dir = Path(args.project_dir).resolve()
    config = load_project(project_dir)
    expected = [
        project_dir / "data" / "candidates.jsonl",
        project_dir / "data" / "screening.tsv",
        project_dir / "papers",
        project_dir / "notes",
        project_dir / "maps" / "literature-map.md",
        project_dir / "refs",
    ]
    missing = [path for path in expected if not path.exists()]
    if missing:
        for path in missing:
            print(f"missing: {path}", file=sys.stderr)
        raise SystemExit(1)
    print(f"ok: {config['project']['title']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Research literature pipeline CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create a new research project")
    init.add_argument("--slug", default="")
    init.add_argument("--title", required=True)
    init.add_argument("--topic", required=True)
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=init_project)

    candidate = sub.add_parser("add-candidate", help="Append one candidate paper")
    candidate.add_argument("project_dir")
    candidate.add_argument("--title", required=True)
    candidate.add_argument("--doi", default="")
    candidate.add_argument("--arxiv-id", default="")
    candidate.add_argument("--year", type=int)
    candidate.add_argument("--url", default="")
    candidate.add_argument("--pdf-url", default="")
    candidate.add_argument("--status", default="candidate")
    candidate.add_argument("--score", type=int)
    candidate.add_argument("--reason", default="")
    candidate.set_defaults(func=add_candidate)

    paper = sub.add_parser("paper-dir", help="Create cache/note files for one Zotero item")
    paper.add_argument("project_dir")
    paper.add_argument("--key", required=True)
    paper.add_argument("--title", default="")
    paper.add_argument("--doi", default="")
    paper.add_argument("--force", action="store_true")
    paper.set_defaults(func=make_paper_dir)

    export = sub.add_parser("export-bib", help="Export BibTeX through Zotero local API")
    export.add_argument("project_dir")
    export.add_argument("--collection-key", default="")
    export.add_argument("--limit", type=int)
    export.add_argument("--zotero-base", default=DEFAULT_ZOTERO_BASE)
    export.set_defaults(func=export_bib)

    validate = sub.add_parser("validate", help="Validate project structure")
    validate.add_argument("project_dir")
    validate.set_defaults(func=validate_project)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
