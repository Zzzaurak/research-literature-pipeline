#!/usr/bin/env python3
"""Lightweight CLI for a Zotero + MinerU literature pipeline.

The CLI only uses the Python standard library. It manages project files and
uses Zotero's local API for optional BibTeX export fallback.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import re
import sys
import tomllib
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlencode, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
PROJECTS_DIR = ROOT / "projects"
TEMPLATES_DIR = ROOT / "templates"
DEFAULT_ZOTERO_BASE = "http://127.0.0.1:23119"
DEFAULT_MINERU_TIMEOUT = 240


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


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


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

[pipeline]
auto_read_selected = true
auto_export_bib = true
default_read_statuses = ["must-read", "method", "background"]
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


def http_get_bytes(url: str, timeout: int = 120) -> bytes:
    request = Request(url, headers={"User-Agent": "research-literature-pipeline/0.1"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise SystemExit(f"HTTP {exc.code}: {body[:1000]}") from exc
    except URLError as exc:
        raise SystemExit(f"Could not fetch URL: {exc.reason}") from exc


def http_get_json(url: str, timeout: int = 60) -> dict | list:
    body = http_get(url, timeout=timeout)
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Expected JSON from {url}, got: {body[:1000]}") from exc


def zotero_item(base: str, key: str) -> dict:
    return http_get_json(f"{base.rstrip('/')}/api/users/0/items/{quote(key)}")


def zotero_children(base: str, key: str) -> list[dict]:
    data = http_get_json(f"{base.rstrip('/')}/api/users/0/items/{quote(key)}/children")
    if not isinstance(data, list):
        raise SystemExit(f"Unexpected Zotero children response for {key}")
    return data


def pick_pdf_attachment(children: list[dict]) -> dict | None:
    for child in children:
        data = child.get("data", {})
        content_type = (data.get("contentType") or "").lower()
        filename = (data.get("filename") or data.get("title") or "").lower()
        if content_type == "application/pdf" or filename.endswith(".pdf"):
            return child
    return None


def file_url_to_path(file_url: str) -> Path:
    parsed = urlparse(file_url)
    if parsed.scheme != "file":
        raise SystemExit(f"Zotero attachment did not resolve to a local file URL: {file_url}")
    return Path(unquote(parsed.path))


def resolve_zotero_pdf(base: str, key: str) -> tuple[Path, str]:
    children = zotero_children(base, key)
    attachment = pick_pdf_attachment(children)
    if not attachment:
        raise SystemExit(
            f"No PDF attachment found for Zotero item {key}. "
            "Attach a PDF in Zotero, or rerun with --pdf or --pdf-url."
        )
    attachment_key = attachment.get("key") or attachment.get("data", {}).get("key")
    if not attachment_key:
        raise SystemExit(f"Could not resolve attachment key for Zotero item {key}")
    url = f"{base.rstrip('/')}/api/users/0/items/{quote(attachment_key)}/file/view/url"
    file_url = http_get(url, timeout=30).strip()
    source = file_url_to_path(file_url)
    if not source.exists():
        raise SystemExit(f"Zotero PDF file does not exist on disk: {source}")
    return source, attachment_key


def find_mineru_plugin_root() -> Path:
    candidates = sorted(
        (Path.home() / ".codex/plugins/cache/ao-local-plugins/mineru-pdf-router").glob("*"),
        reverse=True,
    )
    for root in candidates:
        server = root / "scripts" / "mineru_mcp_server.py"
        if server.exists():
            return root
    raise SystemExit(
        "Could not find mineru-pdf-router MCP server under "
        "~/.codex/plugins/cache/ao-local-plugins/mineru-pdf-router"
    )


def mineru_parse_pdf(pdf_path: Path, args: argparse.Namespace) -> str:
    plugin_root = Path(args.mineru_plugin_root).expanduser() if args.mineru_plugin_root else find_mineru_plugin_root()
    server = plugin_root / "scripts" / "mineru_mcp_server.py"
    if not server.exists():
        raise SystemExit(f"MinerU MCP server not found: {server}")

    call = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "mineru_parse_document",
            "arguments": {
                "source_type": "local_path",
                "source": str(pdf_path),
                "language": args.language,
                "enable_table": True,
                "enable_formula": True,
                "is_ocr": args.ocr,
                "timeout_sec": args.mineru_timeout,
            },
        },
    }
    if args.page_range:
        call["params"]["arguments"]["page_range"] = args.page_range

    proc = subprocess.run(
        [sys.executable, str(server)],
        cwd=plugin_root,
        input=json.dumps(call, ensure_ascii=False) + "\n",
        text=True,
        capture_output=True,
        timeout=args.mineru_timeout + 30,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(
            f"MinerU MCP server failed with exit code {proc.returncode}\n"
            f"stderr:\n{proc.stderr[:2000]}"
        )
    first_line = next((line for line in proc.stdout.splitlines() if line.strip()), "")
    if not first_line:
        raise SystemExit(f"MinerU returned no JSON output. stderr:\n{proc.stderr[:2000]}")
    try:
        obj = json.loads(first_line)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"MinerU returned invalid JSON: {first_line[:1000]}") from exc

    if obj.get("error"):
        raise SystemExit(f"MinerU JSON-RPC error: {obj['error']}")
    result = obj.get("result", {})
    structured = result.get("structuredContent") or {}
    if result.get("isError") or structured.get("is_error"):
        raise SystemExit(
            "MinerU parse failed: "
            + json.dumps(structured or result, ensure_ascii=False)[:2000]
        )
    markdown = (
        structured.get("markdown")
        or structured.get("markdown_text")
        or structured.get("content")
        or ""
    )
    if not markdown.strip():
        raise SystemExit(
            "MinerU succeeded but returned empty Markdown. "
            + json.dumps(structured, ensure_ascii=False)[:2000]
        )
    return markdown


def extract_named_section(markdown: str, names: list[str], max_chars: int = 3500) -> str:
    heading = r"(?im)^(#{1,4})\s*(.+?)\s*$"
    matches = list(re.finditer(heading, markdown))
    lowered = [name.lower() for name in names]
    for index, match in enumerate(matches):
        title = match.group(2).strip().lower()
        if any(name in title for name in lowered):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
            section = markdown[start:end].strip()
            return section[:max_chars].strip()
    return ""


def first_paragraph(markdown: str, max_chars: int = 1800) -> str:
    clean = re.sub(r"(?m)^#+\s*", "", markdown)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", clean) if p.strip()]
    for paragraph in paragraphs:
        if len(paragraph) > 120:
            return paragraph[:max_chars].strip()
    return (paragraphs[0] if paragraphs else "")[:max_chars].strip()


def key_headings(markdown: str, limit: int = 16) -> list[str]:
    headings = []
    for match in re.finditer(r"(?m)^#{1,4}\s+(.+?)\s*$", markdown):
        text = match.group(1).strip()
        if text and text not in headings:
            headings.append(text)
        if len(headings) >= limit:
            break
    return headings


def generate_reading_note(
    *,
    title: str,
    zotero_key: str,
    doi: str,
    project_topic: str,
    pdf_path: Path | str,
    markdown_path: Path,
    markdown: str,
) -> str:
    abstract = extract_named_section(markdown, ["abstract", "摘要"]) or first_paragraph(markdown)
    intro = extract_named_section(markdown, ["introduction", "引言", "background"], max_chars=1800)
    method = extract_named_section(
        markdown,
        ["method", "methods", "methodology", "data", "observations", "sample", "方法", "数据", "观测", "样本"],
        max_chars=2200,
    )
    results = extract_named_section(
        markdown,
        ["result", "results", "analysis", "discussion", "conclusion", "summary", "结果", "讨论", "结论", "总结"],
        max_chars=2600,
    )
    headings = key_headings(markdown)
    heading_lines = "\n".join(f"- {heading}" for heading in headings) or "- 未检测到清晰标题结构"
    word_count = len(re.findall(r"\w+", markdown))

    return f"""# {title}

**Zotero 条目 Key:** {zotero_key}

**DOI:** {doi}

**状态:** MinerU 自动草稿

**项目主题:** {project_topic}

**PDF / 来源:** {pdf_path}

**Markdown 路径:** {markdown_path}

**来源说明:** 本笔记由 pipeline 基于 MinerU Markdown 自动生成，适合后续让 AI 继续精读和人工复核。MinerU 输出偏语义抽取，不保证版面完全还原。

## 为什么这篇论文重要

- 与项目主题的潜在关系：{project_topic}
- 需要进一步由 AI/人工判断它在文献地图中的角色：核心论文、方法论文、背景论文或可排除论文。

## 研究问题

{intro or "待根据全文进一步提炼。"}

## 摘要 / 核心内容

{abstract or "未能从 Markdown 中自动提取摘要。"}

## 数据 / 样本

{method or "未能自动定位数据、样本或方法段落；请让 AI 基于 paper.md 继续精读。"}

## 方法

{method or "未能自动定位方法段落；请让 AI 基于 paper.md 继续精读。"}

## 主要结果 / 结论

{results or "未能自动定位结果或结论段落；请让 AI 基于 paper.md 继续精读。"}

## 关键图表 / 章节索引

{heading_lines}

## 局限性

- 自动草稿未可靠识别局限性；下一步应检查 discussion、limitations、conclusion 等段落。

## 和本项目的关系

- 待 AI 结合项目目标进一步判断。

## 可引用的论断

- 待 AI 精读后从 `paper.md` 中提取具体 claim，并绑定到论文题名和 Zotero 条目 Key。

## 后续需要追踪的论文

- 待从 introduction、related work 和 reference list 中提取。

## 阅读日志

- 创建日期: {now_date()}
- Markdown 近似词元数: {word_count}
"""


def read_paper(args: argparse.Namespace) -> None:
    project_dir = Path(args.project_dir).resolve()
    config = load_project(project_dir)
    title = args.title
    doi = args.doi
    zotero_key = args.key or "manual"
    zotero_attachment_key = ""

    if args.key and (not title or not doi):
        try:
            item = zotero_item(args.zotero_base, args.key)
            data = item.get("data", {})
            title = title or data.get("title", "")
            doi = doi or data.get("DOI", "")
        except SystemExit:
            if not title:
                raise

    pid = paper_id(zotero_key, title or args.pdf_url or args.pdf or "paper")
    paper_dir_path = project_dir / "papers" / pid
    paper_dir_path.mkdir(parents=True, exist_ok=True)
    pdf_target = paper_dir_path / "paper.pdf"
    markdown_target = paper_dir_path / "paper.md"
    note_target = project_dir / "notes" / f"{pid}.md"
    metadata_target = paper_dir_path / "metadata.json"

    if args.markdown:
        markdown_source = Path(args.markdown).expanduser().resolve()
        if not markdown_source.exists():
            raise SystemExit(f"Markdown source does not exist: {markdown_source}")
        markdown = markdown_source.read_text(encoding="utf-8")
        write_text(markdown_target, markdown)
        pdf_source_text = args.pdf or args.pdf_url or ""
        markdown_source_text = str(markdown_source)
    else:
        markdown_source_text = "mineru"
        if args.pdf:
            pdf_source = Path(args.pdf).expanduser().resolve()
            if not pdf_source.exists():
                raise SystemExit(f"PDF does not exist: {pdf_source}")
            shutil.copy2(pdf_source, pdf_target)
            pdf_source_text = str(pdf_source)
        elif args.pdf_url:
            pdf_target.write_bytes(http_get_bytes(args.pdf_url, timeout=180))
            pdf_source_text = args.pdf_url
        elif args.key:
            pdf_source, zotero_attachment_key = resolve_zotero_pdf(args.zotero_base, args.key)
            shutil.copy2(pdf_source, pdf_target)
            pdf_source_text = str(pdf_source)
        else:
            raise SystemExit("Provide --pdf, --pdf-url, --markdown, or --key with a Zotero PDF attachment.")

        if not args.skip_mineru:
            markdown = mineru_parse_pdf(pdf_target, args)
            write_text(markdown_target, markdown)
        else:
            raise SystemExit("--skip-mineru requires --markdown, because read-paper must produce paper.md")

    if not markdown_target.exists() or not markdown_target.read_text(encoding="utf-8").strip():
        raise SystemExit(f"Missing non-empty Markdown after read-paper: {markdown_target}")

    metadata = {
        "zotero_key": args.key,
        "zotero_attachment_key": zotero_attachment_key,
        "title": title,
        "doi": doi,
        "created": now_date(),
        "pdf_path": str(pdf_target) if pdf_target.exists() else "",
        "pdf_source": pdf_source_text,
        "markdown_source": markdown_source_text,
        "mineru_markdown": "paper.md",
        "reading_note": f"../../notes/{pid}.md",
        "status": "read-with-mineru",
    }
    write_json(metadata_target, metadata)

    note = generate_reading_note(
        title=title or pid,
        zotero_key=args.key or "",
        doi=doi or "",
        project_topic=config.get("project", {}).get("topic", ""),
        pdf_path=str(pdf_target) if pdf_target.exists() else (pdf_source_text or "项目中未缓存 PDF"),
        markdown_path=markdown_target,
        markdown=markdown_target.read_text(encoding="utf-8"),
    )
    write_text(note_target, note)
    print(f"paper_dir: {paper_dir_path}")
    print(f"markdown: {markdown_target}")
    print(f"note: {note_target}")


def audit_project(args: argparse.Namespace) -> None:
    project_dir = Path(args.project_dir).resolve()
    load_project(project_dir)
    paper_dirs = sorted(path for path in (project_dir / "papers").iterdir() if path.is_dir())
    if not paper_dirs:
        print("No paper directories found.")
        return
    problems = 0
    for paper_dir_path in paper_dirs:
        if paper_dir_path.name.startswith("."):
            continue
        metadata_path = paper_dir_path / "metadata.json"
        markdown_path = paper_dir_path / "paper.md"
        pdf_path = paper_dir_path / "paper.pdf"
        note_path = None
        if metadata_path.exists():
            metadata = read_json(metadata_path)
            note_rel = metadata.get("reading_note", "")
            if note_rel:
                note_path = (paper_dir_path / note_rel).resolve()
        if note_path is None:
            note_path = project_dir / "notes" / f"{paper_dir_path.name}.md"

        missing = []
        if not metadata_path.exists():
            missing.append("metadata.json")
        if not markdown_path.exists() or not markdown_path.read_text(encoding="utf-8").strip():
            missing.append("paper.md")
        if not note_path.exists() or len(note_path.read_text(encoding="utf-8").strip()) < 300:
            missing.append("structured note")

        if missing:
            problems += 1
            print(f"MISSING {paper_dir_path.name}: {', '.join(missing)}")
        else:
            print(f"OK {paper_dir_path.name}")
    if problems:
        raise SystemExit(1)


def load_candidates(project_dir: Path) -> list[dict]:
    path = project_dir / "data" / "candidates.jsonl"
    if not path.exists():
        raise SystemExit(f"Missing candidates file: {path}")
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSON in {path}:{line_number}") from exc
    return records


def arxiv_pdf_url(record: dict) -> str:
    arxiv_id = record.get("arxiv_id") or ""
    doi = record.get("doi") or ""
    if not arxiv_id and "arxiv" in doi.lower():
        arxiv_id = doi.rsplit("/", 1)[-1]
    arxiv_id = re.sub(r"(?i)^arxiv:", "", arxiv_id).strip()
    if not arxiv_id:
        return ""
    return f"https://arxiv.org/pdf/{arxiv_id}.pdf"


def read_selected(args: argparse.Namespace) -> None:
    project_dir = Path(args.project_dir).resolve()
    load_project(project_dir)
    statuses = {status.strip() for status in args.statuses.split(",") if status.strip()}
    candidates = [
        record for record in load_candidates(project_dir)
        if (record.get("status") or "") in statuses
    ]
    if args.limit:
        candidates = candidates[:args.limit]
    if not candidates:
        print("No selected candidates found.")
        return

    failures = []
    for record in candidates:
        title = record.get("title") or ""
        key = record.get("zotero_key") or ""
        pdf_url = record.get("pdf_url") or arxiv_pdf_url(record)
        print(f"\n== {title or key or record.get('doi', 'untitled')} ==")

        if args.dry_run:
            source = "zotero-key" if key else "pdf-url" if pdf_url else "missing-pdf"
            print(f"DRY RUN source={source} status={record.get('status', '')}")
            continue

        if not key and not pdf_url:
            failures.append((title, "missing zotero_key, pdf_url, or arXiv identifier"))
            print("SKIP missing zotero_key, pdf_url, or arXiv identifier")
            continue

        ns = argparse.Namespace(
            project_dir=str(project_dir),
            key=key,
            title=title,
            doi=record.get("doi") or "",
            pdf="",
            pdf_url=pdf_url,
            markdown="",
            zotero_base=args.zotero_base,
            mineru_plugin_root=args.mineru_plugin_root,
            mineru_timeout=args.mineru_timeout,
            language=args.language,
            page_range=args.page_range,
            ocr=args.ocr,
            skip_mineru=False,
        )
        try:
            read_paper(ns)
        except SystemExit as exc:
            failures.append((title or key, str(exc)))
            print(f"FAILED {exc}")
            if args.stop_on_error:
                break

    if failures:
        print("\nFailures:")
        for title, reason in failures:
            print(f"- {title}: {reason}")
        raise SystemExit(1)


def run_pipeline(args: argparse.Namespace) -> None:
    project_dir = Path(args.project_dir).resolve()
    config = load_project(project_dir)

    print("== validate ==")
    validate_project(argparse.Namespace(project_dir=str(project_dir)))

    read_failed = False
    if not args.skip_reading:
        print("\n== read selected papers ==")
        default_statuses = ",".join(
            config.get("pipeline", {}).get(
                "default_read_statuses", ["must-read", "method", "background"]
            )
        )
        read_args = argparse.Namespace(
            project_dir=str(project_dir),
            statuses=args.statuses or default_statuses,
            limit=args.limit,
            zotero_base=args.zotero_base,
            mineru_plugin_root=args.mineru_plugin_root,
            mineru_timeout=args.mineru_timeout,
            language=args.language,
            page_range=args.page_range,
            ocr=args.ocr,
            dry_run=False,
            stop_on_error=False,
        )
        try:
            read_selected(read_args)
        except SystemExit as exc:
            read_failed = True
            print(f"\nread-selected completed with failures: {exc}")
    else:
        print("\n== read selected papers ==\nskipped by --skip-reading")

    export_failed = False
    if not args.skip_bib:
        print("\n== export bibtex ==")
        export_args = argparse.Namespace(
            project_dir=str(project_dir),
            collection_key=args.collection_key,
            limit=None,
            zotero_base=args.zotero_base,
        )
        try:
            export_bib(export_args)
        except SystemExit as exc:
            export_failed = True
            print(f"\nexport-bib failed: {exc}")
    else:
        print("\n== export bibtex ==\nskipped by --skip-bib")

    print("\n== audit ==")
    try:
        audit_project(argparse.Namespace(project_dir=str(project_dir)))
    except SystemExit as exc:
        print(f"audit reported incomplete reading artifacts: {exc}")
        read_failed = True

    if read_failed or export_failed:
        raise SystemExit(1)


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

    read = sub.add_parser(
        "read-paper",
        help="Fetch/copy a paper PDF, convert it with MinerU, and write a structured note",
    )
    read.add_argument("project_dir")
    read.add_argument("--key", default="", help="Zotero item key")
    read.add_argument("--title", default="")
    read.add_argument("--doi", default="")
    read.add_argument("--pdf", default="", help="Local PDF path")
    read.add_argument("--pdf-url", default="", help="Remote PDF URL")
    read.add_argument("--markdown", default="", help="Existing Markdown path to use instead of MinerU")
    read.add_argument("--zotero-base", default=DEFAULT_ZOTERO_BASE)
    read.add_argument("--mineru-plugin-root", default="")
    read.add_argument("--mineru-timeout", type=int, default=DEFAULT_MINERU_TIMEOUT)
    read.add_argument("--language", default="en")
    read.add_argument("--page-range", default="")
    read.add_argument("--ocr", action="store_true")
    read.add_argument("--skip-mineru", action="store_true")
    read.set_defaults(func=read_paper)

    audit = sub.add_parser("audit", help="Check whether paper directories have PDF, Markdown, and notes")
    audit.add_argument("project_dir")
    audit.set_defaults(func=audit_project)

    selected = sub.add_parser(
        "read-selected",
        help="Run read-paper for selected candidates from data/candidates.jsonl",
    )
    selected.add_argument("project_dir")
    selected.add_argument("--statuses", default="must-read,method,background")
    selected.add_argument("--limit", type=int)
    selected.add_argument("--zotero-base", default=DEFAULT_ZOTERO_BASE)
    selected.add_argument("--mineru-plugin-root", default="")
    selected.add_argument("--mineru-timeout", type=int, default=DEFAULT_MINERU_TIMEOUT)
    selected.add_argument("--language", default="en")
    selected.add_argument("--page-range", default="")
    selected.add_argument("--ocr", action="store_true")
    selected.add_argument("--dry-run", action="store_true")
    selected.add_argument("--stop-on-error", action="store_true")
    selected.set_defaults(func=read_selected)

    run = sub.add_parser(
        "run",
        help="Run the default pipeline stage: validate, read selected papers, export BibTeX, audit",
    )
    run.add_argument("project_dir")
    run.add_argument("--statuses", default="")
    run.add_argument("--limit", type=int)
    run.add_argument("--collection-key", default="")
    run.add_argument("--zotero-base", default=DEFAULT_ZOTERO_BASE)
    run.add_argument("--mineru-plugin-root", default="")
    run.add_argument("--mineru-timeout", type=int, default=DEFAULT_MINERU_TIMEOUT)
    run.add_argument("--language", default="en")
    run.add_argument("--page-range", default="")
    run.add_argument("--ocr", action="store_true")
    run.add_argument("--skip-reading", action="store_true")
    run.add_argument("--skip-bib", action="store_true")
    run.set_defaults(func=run_pipeline)

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
