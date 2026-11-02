# Card schema

Two kinds of card, one markdown file each, YAML frontmatter, optional free note below it:
- `kind: paper` — `papers/<arxiv-id>.md`, one arXiv paper.
- `kind: work` — `work/<slug>.md`, an analysis, gate run, Shisso paper draft (A / B / C / JEPA), register audit or
  robot day that is not one arXiv paper. The slug is `ws-NNN` (the work-stack item) or the paper repo slug.
  Harness / tooling items and items with no public-facing output get no card.

A card with no `kind` is a paper (cards written before WS-147).

| Field | Meaning |
|---|---|
| `id` | paper: arXiv id (`2603.19312`); work: slug (`ws-147`, `paper-a`); equals the file name, unique |
| `kind` | `paper` · `work`; equals the folder (`papers/` · `work/`) |
| `papers` | list of arXiv ids a work card touches (empty on paper cards) |
| `title` | paper title; work: the item title |
| `status` | `backlog` · `reading` · `testing` · `review` · `done` · `parked` |
| `tags` | list |
| `added`, `updated` | dates (`YYYY-MM-DD`); `updated` ≥ `added` |
| `register_id` | row id in the site register, empty if none |
| `ws` | list of `WS-NNN` that worked on the paper |
| `note` | link to the analysis (post URL, repo path), empty if none; the page links it only when it is a URL |
| `summary` | one plain line, never a copied TL;DR presented as a finding |

Statuses, in board order: `backlog` (to analyse) · `reading` (being analysed) · `testing` (running on the rig / Orin)
· `review` (result written, waiting for the owner) · `done` · `parked` (not shown publicly).

Rules (`scripts/board.py check`, also run by CI): unknown status fails; `done` requires `note`; `review` and `done`
require at least one `ws`; `updated` ≥ `added`; ids unique; a paper id is an arXiv id, a work id is
a slug and not an arXiv id; the folder matches `kind`; `papers` entries are arXiv ids. A `reading` or `testing` card not
updated for 21 days gives a warning. `board.json` is generated (`board.py build`), never hand-edited, and `check`
fails when it is out of date.

## Automatic updates (WS-147)

`ws set WS-NNN status=…` in road-to-robotics mirrors the item onto every card it touches (arXiv ids in its title,
prompt line or `papers:` field; its `work/ws-NNN.md` card; `board: yes` or `board: <slug>`) and commits + pushes this
repo: todo → backlog (first time only), doing → reading (testing when it needs the arm / rig / Orin GPU),
waiting-owner / blocked with a result → review, done → done (note = the public link in the result, else the result
path), parked / dropped → parked. A board failure never blocks the queue (one warning line, logged on the item).
