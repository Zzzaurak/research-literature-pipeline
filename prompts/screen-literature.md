# Literature Screening Prompt

Use this after candidate metadata has been collected.

## Task

For each candidate paper, classify it as:

- `must-read`
- `method`
- `background`
- `maybe`
- `exclude`

Score from 1-5 on:

- Relevance to the project question
- Methodological importance
- Recency or historical importance
- Citation usefulness for writing

## Output

Return a compact screening table with:

| Status | Score | Paper | Reason | Action |
| --- | --- | --- | --- | --- |

Only recommend importing `must-read`, `method`, and strong `background` papers into Zotero.
