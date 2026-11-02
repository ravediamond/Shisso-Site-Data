# Card schema

One file per paper: `papers/<arxiv-id>.md`, YAML frontmatter, optional free note below it. Only papers with an arXiv id.

| Field | Meaning |
|---|---|
| `id` | arXiv id (`2603.19312`), equals the file name, unique |
| `title` | paper title |
| `status` | `backlog` · `reading` · `testing` · `review` · `done` · `parked` |
| `tags` | list |
| `added`, `updated` | dates (`YYYY-MM-DD`); `updated` ≥ `added` |
| `register_id` | row id in the site register, empty if none |
| `ws` | list of `WS-NNN` that worked on the paper |
| `note` | link to the analysis (post URL, repo path), empty if none |
| `summary` | one plain line, never a copied TL;DR presented as a finding |

Statuses, in board order: `backlog` (to analyse) · `reading` (being analysed) · `testing` (running on the rig / Orin)
· `review` (result written, waiting for the owner) · `done` · `parked` (not shown publicly).

Rules (`scripts/board.py check`, also run by CI): unknown status fails; `done` requires `note`; `review` and `done`
require at least one `ws`; `updated` ≥ `added`; ids unique; the id is an arXiv id. A `reading` or `testing` card not
updated for 21 days gives a warning. `board.json` is generated (`board.py build`), never hand-edited, and `check`
fails when it is out of date.
