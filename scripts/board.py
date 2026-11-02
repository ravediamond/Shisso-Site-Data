#!/usr/bin/env python3
"""Board CLI: one markdown card per paper in papers/<arxiv-id>.md and per piece of work in work/<slug>.md
(WS-147: an analysis, gate run, Shisso paper or robot day that is not one arXiv paper), board.json generated.

  board.py add <id> [--kind paper|work] [--status S] [--tags a b] [--ws WS-NNN] [--title T] [--papers ID ...]
  board.py set <id> key=value ...      (sets updated=today, appends ws; papers= replaces the list)
  board.py has <id>                    exit 0 when the card exists (either kind)
  board.py build                       write board.json
  board.py check                       validate cards and that board.json is up to date
  board.py list [--status S]
"""
import argparse, datetime, json, os, re, sys, urllib.request
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARDS = os.path.join(ROOT, "papers")
WORK = os.path.join(ROOT, "work")
DIRS = {"paper": CARDS, "work": WORK}
OUT = os.path.join(ROOT, "board.json")
LIBRARY_INDEX = os.path.expanduser("~/workspace/papers/index.json")

STATUSES = ["backlog", "reading", "testing", "review", "done", "parked"]
KINDS = ["paper", "work"]
FIELDS = ["id", "title", "status", "tags", "added", "updated", "register_id", "ws", "note", "summary", "kind", "papers"]
LISTS = ("tags", "ws", "papers")
ID_RE = re.compile(r"^\d{4}\.\d{4,5}$")
WORK_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")  # ws-147, paper-a
WS_RE = re.compile(r"^WS-\d{3}$")
STALE_DAYS = 21


def today():
    return datetime.date.today().isoformat()


def path(pid, kind=None):
    """Card file; with no kind, the existing card of either kind (else the paper path)."""
    if kind:
        return os.path.join(DIRS[kind], pid + ".md")
    for d in (CARDS, WORK):
        if os.path.exists(os.path.join(d, pid + ".md")):
            return os.path.join(d, pid + ".md")
    return os.path.join(CARDS, pid + ".md")


def rel(pid, kind):
    """The name validate() expects: '<id>.md' for papers, 'work/<id>.md' for work."""
    return pid + ".md" if kind == "paper" else f"work/{pid}.md"


def read_card(fn):
    text = open(fn, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        raise ValueError(f"{fn}: no frontmatter")
    meta = yaml.safe_load(m.group(1)) or {}
    for k in ("added", "updated"):
        if isinstance(meta.get(k), datetime.date):
            meta[k] = meta[k].isoformat()
    return meta, m.group(2).strip()


def write_card(meta, body=""):
    out = {k: meta.get(k, [] if k in LISTS else "") for k in FIELDS}
    front = yaml.safe_dump(out, sort_keys=False, allow_unicode=True, width=1000, default_flow_style=False)
    open(path(meta["id"], meta.get("kind") or "paper"), "w", encoding="utf-8").write(f"---\n{front}---\n{body.strip()}\n" if body.strip()
                                                         else f"---\n{front}---\n")


def all_cards():
    out = []
    for kind, d in DIRS.items():
        if os.path.isdir(d):
            for fn in sorted(os.listdir(d)):
                if fn.endswith(".md"):
                    m, body = read_card(os.path.join(d, fn))
                    m.setdefault("kind", kind)
                    m.setdefault("papers", [])
                    out.append((rel(fn[:-3], kind) if m["kind"] == kind else f"{kind}:{fn}", m, body))
    return out


def lookup_title(pid):
    try:
        for p in json.load(open(LIBRARY_INDEX))["papers"]:
            if p.get("arxiv") == pid and p.get("title"):
                return p["title"]
    except OSError:
        pass
    try:
        with urllib.request.urlopen(f"http://export.arxiv.org/api/query?id_list={pid}", timeout=15) as r:
            m = re.search(r"<entry>.*?<title>(.*?)</title>", r.read().decode(), re.S)
            if m:
                return " ".join(m.group(1).split())
    except Exception:
        pass
    return ""


def validate(cards):
    """Return (errors, warnings)."""
    errs, warns, seen = [], [], set()
    for fn, m, _ in cards:
        t = fn
        pid = str(m.get("id", ""))
        kind = m.get("kind") or "paper"
        if kind not in KINDS:
            errs.append(f"{t}: unknown kind '{kind}'")
        elif kind == "paper" and not ID_RE.match(pid):
            errs.append(f"{t}: id '{pid}' is not an arXiv id")
        elif kind == "work" and (not WORK_RE.match(pid) or ID_RE.match(pid)):
            errs.append(f"{t}: work id '{pid}' is not a slug (ws-147, paper-a)")
        if kind in KINDS and fn != rel(pid, kind):
            errs.append(f"{t}: file name or folder does not match id {pid} (kind {kind})")
        for p in m.get("papers") or []:
            if not ID_RE.match(str(p)):
                errs.append(f"{t}: papers entry '{p}' is not an arXiv id")
        if pid in seen:
            errs.append(f"{t}: duplicate id {pid}")
        seen.add(pid)
        if m.get("status") not in STATUSES:
            errs.append(f"{t}: unknown status '{m.get('status')}'")
        if not m.get("title"):
            errs.append(f"{t}: empty title")
        for k in LISTS:
            if not isinstance(m.get(k, []), list):
                errs.append(f"{t}: {k} must be a list")
        for w in m.get("ws") or []:
            if not WS_RE.match(str(w)):
                errs.append(f"{t}: ws entry '{w}' is not WS-NNN")
        if m.get("status") == "done" and not m.get("note"):
            errs.append(f"{t}: done requires note")
        if m.get("status") in ("review", "done") and not m.get("ws"):
            errs.append(f"{t}: {m.get('status')} requires at least one ws")
        a, u = m.get("added"), m.get("updated")
        if not a or not u:
            errs.append(f"{t}: added and updated are required")
        elif str(u) < str(a):
            errs.append(f"{t}: updated {u} is before added {a}")
        if m.get("status") in ("reading", "testing") and u:
            age = (datetime.date.today() - datetime.date.fromisoformat(str(u))).days
            if age > STALE_DAYS:
                warns.append(f"{t}: {m['status']} card not updated for {age} days")
    return errs, warns


def board_data(cards):
    rows = []
    for _, m, _ in cards:
        if m.get("status") == "parked":
            continue
        r = {k: m.get(k, [] if k in LISTS else "") for k in FIELDS}
        r["kind"] = r["kind"] or "paper"
        rows.append(r)
    rows.sort(key=lambda r: (STATUSES.index(r["status"]), r["updated"], r["kind"], r["id"]), reverse=False)
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in STATUSES[:5]}
    by_kind = {k: {s: sum(1 for r in rows if r["status"] == s and r["kind"] == k) for s in STATUSES[:5]} for k in KINDS}
    stamp = max([r["updated"] for r in rows] or [""])
    return {"generated": stamp, "statuses": STATUSES[:5], "kinds": KINDS, "counts": counts, "counts_by_kind": by_kind,
            "cards": rows}


def render(cards):
    return json.dumps(board_data(cards), indent=1, ensure_ascii=False) + "\n"


def cmd_add(a):
    pid, kind = a.id, a.kind
    if kind == "paper" and not ID_RE.match(pid):
        sys.exit(f"'{pid}' is not an arXiv id (a paper card needs one; use --kind work for other work)")
    if kind == "work" and (not WORK_RE.match(pid) or ID_RE.match(pid)):
        sys.exit(f"'{pid}' is not a work slug (ws-147, paper-a)")
    if any(os.path.exists(path(pid, k)) for k in KINDS):
        sys.exit(f"{pid} already has a card")
    os.makedirs(DIRS[kind], exist_ok=True)
    meta = {"id": pid, "title": a.title or (lookup_title(pid) if kind == "paper" else ""), "status": a.status,
            "tags": a.tags or [], "added": today(), "updated": today(), "ws": [a.ws] if a.ws else [],
            "register_id": "", "note": "", "summary": "", "kind": kind, "papers": a.papers or []}
    if not meta["title"]:
        sys.exit("no title found; pass --title")
    write_card(meta)
    cmd_build(a)


def cmd_set(a):
    if not os.path.exists(path(a.id)):
        sys.exit(f"no card for {a.id}")
    meta, body = read_card(path(a.id))
    for kv in a.kv:
        k, _, v = kv.partition("=")
        if k == "ws":
            for w in re.split(r"[,\s]+", v.strip()):
                if w and w not in meta["ws"]:
                    meta["ws"].append(w)
        elif k in ("tags", "papers"):
            meta[k] = [t for t in re.split(r"[,\s]+", v.strip()) if t]
        elif k in FIELDS and k not in ("id", "added", "updated", "kind"):
            meta[k] = int(v) if k == "register_id" and v.isdigit() else v
        else:
            sys.exit(f"cannot set '{k}'")
    meta["updated"] = today()
    meta.setdefault("kind", "work" if path(a.id).startswith(WORK + os.sep) else "paper")
    meta.setdefault("papers", [])
    errs, _ = validate([(rel(a.id, meta["kind"]), meta, body)])
    if errs:
        sys.exit("\n".join("REFUSED " + e for e in errs))
    write_card(meta, body)
    cmd_build(a)


def cmd_build(_a=None):
    open(OUT, "w", encoding="utf-8").write(render(all_cards()))


def cmd_check(_a):
    cards = all_cards()
    errs, warns = validate(cards)
    if not os.path.exists(OUT) or open(OUT, encoding="utf-8").read() != render(cards):
        errs.append("board.json is not up to date: run scripts/board.py build")
    for w in warns:
        print("WARN", w)
    for e in errs:
        print("FAIL", e)
    print(f"{len(cards)} cards, {len(errs)} errors, {len(warns)} warnings")
    sys.exit(1 if errs else 0)


def cmd_has(a):
    sys.exit(0 if any(os.path.exists(path(a.id, k)) for k in KINDS) else 1)


def cmd_list(a):
    for _, m, _ in all_cards():
        if (not a.status or m["status"] == a.status) and (not a.kind or m["kind"] == a.kind):
            print(f"{m['id']:<11}{m['kind']:<6}{m['status']:<9}{m['updated']}  {','.join(m['ws']):<14}{m['title'][:60]}")
    if not a.status:
        c = {}
        for _, m, _ in all_cards():
            c[m["status"]] = c.get(m["status"], 0) + 1
        print("COUNTS", " ".join(f"{s}={c.get(s, 0)}" for s in STATUSES))


def main():
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("add"); s.add_argument("id"); s.add_argument("--status", default="backlog", choices=STATUSES)
    s.add_argument("--kind", default="paper", choices=KINDS); s.add_argument("--papers", nargs="*")
    s.add_argument("--tags", nargs="*"); s.add_argument("--ws"); s.add_argument("--title"); s.set_defaults(f=cmd_add)
    s = sp.add_parser("has"); s.add_argument("id"); s.set_defaults(f=cmd_has)
    s = sp.add_parser("set"); s.add_argument("id"); s.add_argument("kv", nargs="+"); s.set_defaults(f=cmd_set)
    sp.add_parser("build").set_defaults(f=cmd_build)
    sp.add_parser("check").set_defaults(f=cmd_check)
    s = sp.add_parser("list"); s.add_argument("--status"); s.add_argument("--kind", choices=KINDS); s.set_defaults(f=cmd_list)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
