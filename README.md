# Research Literature Pipeline

This directory contains a v1 research-literature pipeline for Codex + Zotero + MinerU + Better BibTeX.

The pipeline is intentionally a project directory first, not a full plugin. Zotero, MinerU, and Better BibTeX stay as external tools; this repo stores workflow state, prompts, cached Markdown, reading notes, literature maps, and exported BibTeX.

## Pipeline

1. Project start
   - Create a project directory.
   - Define topic, scope, search terms, Zotero collection name, tags, and output paths.

2. Literature screening
   - Collect candidate metadata first.
   - Rank papers before importing everything into Zotero.
   - Use tags such as `must-read`, `method`, `background`, `maybe`, and `exclude`.

3. Automatic reading
   - Store the PDF in Zotero.
   - Convert the PDF to Markdown with MinerU.
   - Cache the Markdown in the project directory.
   - Generate a structured reading note.

4. Literature map
   - Summarize core papers, methods, timeline, controversies, and open questions.

5. Better BibTeX export
   - Prefer Better BibTeX auto-export for stable citation keys.
   - Use the local Zotero export fallback when Better BibTeX is not installed or configured.

## Directory Layout

```text
research-literature-pipeline/
  README.md
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

Create a paper cache directory after the paper has a Zotero key:

```bash
python3 scripts/research_pipeline.py paper-dir projects/supernova-companion \
  --key TTWH7MG8 \
  --title "Measured measurement"
```

Export BibTeX through Zotero local API fallback:

```bash
python3 scripts/research_pipeline.py export-bib projects/supernova-companion
```

## MinerU Step

Use the `mineru-pdf-router` MCP tool to convert local PDFs to Markdown. Save the returned Markdown to:

```text
projects/<slug>/papers/<paper-id>/paper.md
```

Then create a reading note from `templates/reading-note.md` or by using the prompt in `prompts/read-paper-mineru.md`.

## Recommended First Run

Use a small project with 5 papers:

1. Create the project.
2. Add 10-20 candidates to `data/candidates.jsonl`.
3. Select 5 `must-read` papers.
4. Import only those into Zotero.
5. Convert one PDF through MinerU.
6. Generate one reading note.
7. Update the literature map.
8. Export `refs/project.bib`.

## Security

Do not store Zotero API keys, MinerU tokens, or proxy credentials in this directory. Keep credentials in local config files such as `~/.codex/config.toml` or `~/.codex/mineru-pdf-router.env`.
