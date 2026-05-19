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
   - Ask for missing key research objectives or themes only when they cannot be inferred from the user's initial query or context.
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
   - 1. Verify if a PDF attachment or local PDF path exists for every paper that should be read.
   - 2. If no PDF is available, find/download/attach a PDF before attempting full reading. If a PDF cannot be downloaded, log the issue and notify the user to manually resolve it.
   - 3. Run the appropriate command for reading the paper:
     - For single papers: `python3 scripts/research_pipeline.py read-paper <project-dir> --key <ZOTERO_ITEM_KEY>`.
     - For batches: `python3 scripts/research_pipeline.py read-selected <project-dir> --statuses must-read,method,background`.
   - 4. Use `--pdf` or `--pdf-url` when the Zotero item does not have a local PDF attachment.
   - 5. Ensure the command creates `papers/<paper-id>/paper.md` and `notes/<paper-id>.md`. If `paper.md` is missing, do not claim the paper has been read.
   - 6. Mention in summaries that the source was MinerU Markdown.

6. Reading notes.
   - Generate notes from `templates/reading-note.md`.
   - Save notes under `notes/`.
   - Focus on claims, method, data, limitations, and project relevance.

7. Literature map.
   - Update `maps/literature-map.md`.
   - Write the literature map in Chinese unless the user specifies another language.
   - Keep claims linked to specific papers.

8. BibTeX export.
   - Prefer Better BibTeX auto-export when configured.
   - Otherwise use `research_pipeline.py export-bib` or `zotero_local_export_bibtex`.

## Quality Bar

- Keep PDFs in Zotero and AI-readable Markdown in the project directory.
- Cache MinerU output and avoid repeated parsing.
- Treat `paper.md` as the required input for automatic full-paper reading.
- Use `python3 scripts/research_pipeline.py audit <project-dir>` to catch skipped reading steps.
- Do not store API keys or tokens in the project.
- Be explicit about excluded papers and why they were excluded.
