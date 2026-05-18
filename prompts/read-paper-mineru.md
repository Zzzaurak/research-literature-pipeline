# Read Paper With MinerU Prompt

Use this after a PDF has been converted to Markdown by `mineru-pdf-router`.

## Inputs

- Project topic:
- Zotero metadata:
- MinerU Markdown:

## Task

Read the Markdown as semantic extraction from the PDF. Do not assume visual layout fidelity.

Generate a structured reading note with:

1. Why this paper matters.
2. Research question.
3. Main claims.
4. Data / sample.
5. Method.
6. Key figures / tables.
7. Limitations.
8. Relation to this project.
9. Quotable claims to cite.
10. Follow-up papers.

## Output

Write the note in the format of `templates/reading-note.md`.
