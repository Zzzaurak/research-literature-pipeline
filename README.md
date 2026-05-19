# Research Literature Pipeline

This is a project-start literature workflow for Codex + Zotero + MinerU PDF Router + Better BibTeX.

The repository is a **project template + lightweight CLI + Codex skill draft**, not a full plugin. Zotero remains the source of truth for metadata, collections, tags, PDFs, and citation keys. This repository stores workflow state, screening tables, AI-readable Markdown caches, reading notes, literature maps, prompts, and exported BibTeX.

## What Gets Stored Where

- **Zotero**: metadata, collections, tags, PDF attachments, notes when desired, Better BibTeX citation keys.
- **This repo**: project configs, candidate lists, screening results, MinerU Markdown caches, reading notes, literature maps, exported `.bib`.
- **MinerU**: converts a local or remote PDF into semantic Markdown for AI reading.
- **Better BibTeX**: provides stable citation keys and preferred `.bib` export.

## Pipeline

1. **Project start**
   - Create a project directory.
   - Define topic, scope, search terms, Zotero collection name, tags, and output paths.

2. **Literature discovery and screening**
   - Collect candidate metadata first.
   - Rank papers before importing everything into Zotero.
   - Use statuses such as `must-read`, `method`, `background`, `maybe`, and `exclude`.

3. **Automatic reading**
   - Import selected papers into Zotero.
   - Ensure each paper to be read has a PDF attachment or a local PDF path.
   - Convert the PDF to Markdown with MinerU.
   - Save the Markdown as `papers/<paper-id>/paper.md`.
   - Generate a structured reading note in `notes/<paper-id>.md`.

4. **Literature map**
   - Write the literature map in Chinese by default.
   - Summarize core papers, methods, timeline, controversies, open questions, and citation plans.

5. **Better BibTeX export**
   - Prefer Better BibTeX auto-export for stable citation keys.
   - Use the local Zotero export fallback when Better BibTeX is not installed or configured.

## Important: PDF And Markdown Are Required For Auto-Reading

Zotero can store only metadata for a paper. That is enough for screening, but not enough for full automatic reading.

For every paper that should be read by AI, the project should have:

```text
projects/<slug>/papers/<paper-id>/
  metadata.json
  paper.md
notes/<paper-id>.md
```

`paper.md` is not downloaded automatically from Zotero. It must be created by converting a PDF through MinerU. The source PDF can be:

- a PDF attachment already stored in Zotero,
- a PDF downloaded from arXiv, publisher pages, ADS, Semantic Scholar, or another source,
- a local PDF you provide manually.

If `paper.md` is missing, the AI should not claim to have read the paper. It should first find or download the PDF, run MinerU, save the Markdown, and then generate the reading note.

For arXiv papers, TeX source can sometimes be more readable than PDF; use it when available, otherwise use PDF + MinerU.

## Directory Layout

```text
research-literature-pipeline/
  README.md
  README.zh-CN.md
  scripts/research_pipeline.py
  templates/
  prompts/
  skills/research-literature-pipeline/SKILL.md
  projects/
```

Each project created by the CLI uses:

```text
projects/<slug>/
  project.toml
  data/candidates.jsonl
  data/screening.tsv
  papers/
  notes/
  maps/literature-map.md
  refs/
```

By default, `.gitignore` ignores `projects/*`, because real project files may contain private research topics, candidate judgments, notes, PDFs, MinerU Markdown, and `.bib` files. For public GitHub repositories, commit the pipeline itself and keep concrete research projects private unless you intentionally choose otherwise.

## Quick Start

Create a new project:

```bash
python3 scripts/research_pipeline.py init \
  --slug supernova-companion \
  --title "Type Ia Supernova Companion Constraints" \
  --topic "early light curve constraints on Type Ia supernova companion interaction"
```

Add a candidate paper:

```bash
python3 scripts/research_pipeline.py add-candidate projects/supernova-companion \
  --doi 10.1038/nphys1170 \
  --title "Measured measurement" \
  --year 2009 \
  --status must-read \
  --reason "Smoke-test paper for Zotero import and note generation"
```

Create a cache directory and reading-note template for a Zotero item:

```bash
python3 scripts/research_pipeline.py paper-dir projects/supernova-companion \
  --key TTWH7MG8 \
  --title "Measured measurement" \
  --doi 10.1038/nphys1170
```

Run the full reading step for a Zotero item that already has a PDF attachment:

```bash
python3 scripts/research_pipeline.py read-paper projects/supernova-companion \
  --key TTWH7MG8 \
  --language en
```

Run the full reading step from a local PDF:

```bash
python3 scripts/research_pipeline.py read-paper projects/supernova-companion \
  --title "Measured measurement" \
  --doi 10.1038/nphys1170 \
  --pdf /absolute/path/to/paper.pdf \
  --language en
```

If MinerU Markdown already exists, import it directly:

```bash
python3 scripts/research_pipeline.py read-paper projects/supernova-companion \
  --key TTWH7MG8 \
  --title "Measured measurement" \
  --markdown /absolute/path/to/paper.md
```

Audit whether papers have been fully prepared for AI reading:

```bash
python3 scripts/research_pipeline.py audit projects/supernova-companion
```

Run the reading step for selected candidates from `data/candidates.jsonl`:

```bash
python3 scripts/research_pipeline.py read-selected projects/supernova-companion \
  --statuses must-read,method,background \
  --limit 5
```

Validate project structure:

```bash
python3 scripts/research_pipeline.py validate projects/supernova-companion
```

Export BibTeX through Zotero local API fallback:

```bash
python3 scripts/research_pipeline.py export-bib projects/supernova-companion
```

## Recommended Workflow

### 1. Project Start

Ask Codex to start from a research question:

```text
Start a literature project for Type Ia supernova early light curve constraints on companion interaction. Generate search terms, screening criteria, Zotero collection/tag plan, and the project directory.
```

Expected outputs:

- `project.toml`
- search terms
- screening rubric
- Zotero collection/tag plan

### 2. Literature Screening

Collect metadata first and avoid importing every result into Zotero.

Use statuses:

- `must-read`: essential paper
- `method`: method paper
- `background`: useful for introduction/background
- `maybe`: possibly useful
- `exclude`: excluded, with a reason

Screening files:

```text
data/candidates.jsonl
data/screening.tsv
```

### 3. PDF To Markdown With MinerU

After a selected paper is imported into Zotero, make sure it has a PDF attachment or a local PDF path. Then use `mineru-pdf-router` to convert the PDF to Markdown.

The CLI can run this step directly for one paper:

```bash
python3 scripts/research_pipeline.py read-paper projects/<slug> --key <ZOTERO_ITEM_KEY>
```

Or for selected candidates:

```bash
python3 scripts/research_pipeline.py read-selected projects/<slug> --statuses must-read,method
```

This command creates or updates:

```text
papers/<paper-id>/metadata.json
papers/<paper-id>/paper.pdf      # when the PDF comes from Zotero, --pdf, or --pdf-url
papers/<paper-id>/paper.md
notes/<paper-id>.md
```

`read-selected` can process candidates that have `zotero_key`, `pdf_url`, or an arXiv identifier. Candidates with only a DOI and no PDF source will be reported as failures, because the pipeline should not invent a full-paper reading from metadata alone.

Save MinerU output to:

```text
projects/<slug>/papers/<paper-id>/paper.md
```

MinerU output is semantic Markdown for AI reading, not layout-perfect reproduction. Use the original PDF when visual layout or figures need verification.

### 4. Reading Notes

Use:

```text
prompts/read-paper-mineru.md
templates/reading-note.md
```

Generate notes under:

```text
notes/<paper-id>.md
```

### 5. Literature Map

Update:

```text
maps/literature-map.md
```

The literature map should be written in Chinese by default and include:

- 核心问题
- 阅读优先级
- 领域时间线
- 方法分类
- 关键 claim 与证据
- 争议点
- open questions
- 写作引用计划

### 6. BibTeX Export

Prefer Better BibTeX auto-export for stable citation keys.

Fallback:

```bash
python3 scripts/research_pipeline.py export-bib projects/<slug>
```

## Privacy And GitHub

Do not commit:

- Zotero API keys, MinerU tokens, proxy configs, cookies.
- Zotero databases such as `zotero.sqlite`.
- PDFs, MinerU Markdown, real reading notes, or project `.bib` files unless you know they are safe to publish.
- `projects/*` by default.

Ignored by default:

- `projects/*`
- `*.pdf`
- `*.xpi`
- `*.bib`
- `*.sqlite*`
- `.env*`
- `*.key`
- `*.token`
- `secrets/`
- `credentials/`

## Using On Another Computer

1. Install Zotero.
2. Install Better BibTeX.
3. Configure Codex Zotero MCP.
4. Configure MinerU PDF Router.
5. Clone this repository.
6. Run the CLI inside `research-literature-pipeline/`.

Keep credentials in each machine's local config, not in GitHub.
