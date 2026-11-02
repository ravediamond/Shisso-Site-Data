# Shisso-Site-Data

Data for the paper board on shissorobotics.com/board/: one markdown card per paper in `papers/`, plus the generated
`board.json` that the page reads live from this repo. Fields and rules: `schema.md`.

Move a card (three commands; needs Python 3 with PyYAML):

```sh
python scripts/board.py set 2610.39451 status=testing ws=WS-064   # sets updated to today, appends the WS id
python scripts/board.py check                                      # validates; fails if board.json is stale
git add -A && git commit -m "board: 2610.39451 -> testing" && git push
```

Other commands: `board.py add <id> [--status S] [--tags a b] [--ws WS-NNN]`, `board.py list [--status S]`,
`board.py build`. Tests: `python -m pytest tests`. No PDF, Drive path or paper file belongs in this repo.
