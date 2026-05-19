---
name: research-literature-pipeline
description: Run a project-start to BibTeX-export literature workflow using Zotero, MinerU PDF Router, and Better BibTeX-style project artifacts.
---

# Research Literature Pipeline

Use this skill when the user wants to start a research project, collect and screen literature, read PDFs with MinerU, build a literature map, and export `.bib` references.

## Workflow

1. Ground in the project directory.
   - Use `research-literature-pipeline/scripts/research_pipeline.py`.
   - Keep project artifacts under `research-literature-pipeline/projects/<slug>/`.

2. Project start.
   - Create a project with `init`.
   - Ask for missing high-impact scope only when it cannot be inferred.
   - Record the topic in `project.toml`.

3. Literature screening.
   - Collect metadata first.
   - Add candidates to `data/candidates.jsonl`.
   - Do not import every search result into Zotero.
   - Prefer importing papers classified as `must-read`, `method`, or high-value `background`.

4. Zotero import.
   - Use Zotero MCP tools when available.
   - Use local extras for DOI import if Web API writes are unavailable.
   - Tag imported papers with the project tag from `project.toml`.

5. PDF to Markdown.
   - For every paper that should be read, first verify that a PDF attachment or local PDF path exists.
   - If no PDF is available, find/download/attach a PDF before attempting full reading.
   - Use `mineru-pdf-router` for semantic PDF-to-Markdown conversion.
   - Save MinerU output to `papers/<paper-id>/paper.md`.
   - If `paper.md` is missing, do not claim the paper has been read.
   - Mention in summaries that the source was MinerU Markdown.

6. Reading notes.
   - Generate notes from `templates/reading-note.md`.
   - Save notes under `notes/`.
   - Focus on claims, method, data, limitations, and project relevance.

7. Literature map.
   - Update `maps/literature-map.md`.
   - Write the literature map in Chinese by default.
   - Keep claims linked to specific papers.

8. BibTeX export.
   - Prefer Better BibTeX auto-export when configured.
   - Otherwise use `research_pipeline.py export-bib` or `zotero_local_export_bibtex`.

## Quality Bar

- Keep PDFs in Zotero and AI-readable Markdown in the project directory.
- Cache MinerU output and avoid repeated parsing.
- Treat `paper.md` as the required input for automatic full-paper reading.
- Do not store API keys or tokens in the project.
- Be explicit about excluded papers and why they were excluded.
