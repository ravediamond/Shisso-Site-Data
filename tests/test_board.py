import importlib.util, os, subprocess, sys
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("board", os.path.join(HERE, "..", "scripts", "board.py"))
board = importlib.util.module_from_spec(spec); spec.loader.exec_module(board)


def card(**kw):
    m = {"id": "2601.00001", "title": "T", "status": "backlog", "tags": [], "added": "2026-11-01",
         "updated": "2026-11-02", "register_id": "", "ws": [], "note": "", "summary": ""}
    m.update(kw)
    return (m["id"] + ".md", m, "")


def errs(*cards):
    return board.validate(list(cards))[0]


def test_valid_card_passes():
    assert errs(card()) == []

def test_unknown_status_fails():
    assert any("unknown status" in e for e in errs(card(status="doing")))

def test_done_requires_note():
    assert any("done requires note" in e for e in errs(card(status="done", ws=["WS-001"])))
    assert errs(card(status="done", ws=["WS-001"], note="x")) == []

@pytest.mark.parametrize("s", ["review", "done"])
def test_review_done_require_ws(s):
    assert any("requires at least one ws" in e for e in errs(card(status=s, note="x")))

def test_updated_not_before_added():
    assert any("before added" in e for e in errs(card(added="2026-11-03", updated="2026-11-02")))

def test_duplicate_id_fails():
    assert any("duplicate" in e for e in errs(card(), card()))

def test_non_arxiv_id_fails():
    assert any("not an arXiv id" in e for e in errs(card(id="podcast-1")))

def test_stale_reading_warns_not_fails(monkeypatch):
    e, w = board.validate([card(status="reading", added="2020-01-01", updated="2020-01-02")])
    assert e == [] and len(w) == 1

def test_parked_hidden_from_board():
    d = board.board_data([card(status="parked"), card(id="2601.00002")])
    assert [c["id"] for c in d["cards"]] == ["2601.00002"] and "parked" not in d["counts"]

def test_build_is_deterministic():
    cs = [card(id="2601.00002"), card()]
    assert board.render(cs) == board.render(list(reversed(cs)))


# WS-147: work cards (kind: work, work/<slug>.md)
def work(**kw):
    m = card(**{"id": "ws-147", "kind": "work", **kw})[1]
    return ("work/" + m["id"] + ".md", m, "")

def test_work_card_passes():
    assert errs(work(papers=["2601.00001"])) == []

def test_work_id_must_be_slug():
    assert any("not a slug" in e for e in errs(work(id="2601.00009")))
    assert any("not a slug" in e for e in errs(work(id="WS 147")))

def test_work_card_in_papers_folder_fails():
    m = work()[1]
    assert any("folder does not match" in e for e in errs((m["id"] + ".md", m, "")))

def test_unknown_kind_fails():
    assert any("unknown kind" in e for e in errs(card(kind="podcast")))

def test_papers_entries_are_arxiv_ids():
    assert any("papers entry" in e for e in errs(work(papers=["paper-a"])))

def test_counts_by_kind():
    d = board.board_data([card(), work(status="done", ws=["WS-147"], note="x")])
    assert d["counts_by_kind"]["work"]["done"] == 1 and d["counts_by_kind"]["paper"]["backlog"] == 1
    assert d["counts"]["done"] == 1 and {c["kind"] for c in d["cards"]} == {"paper", "work"}

def test_card_without_kind_is_a_paper():
    m = card()[1]; m.pop("kind", None)
    assert errs(("2601.00001.md", m, "")) == [] and board.board_data([("2601.00001.md", m, "")])["cards"][0]["kind"] == "paper"


def test_cli_add_set_work(tmp_path, monkeypatch):
    for k, v in (("ROOT", str(tmp_path)), ("CARDS", str(tmp_path / "papers")), ("WORK", str(tmp_path / "work")),
                 ("OUT", str(tmp_path / "board.json"))):
        monkeypatch.setattr(board, k, v)
    monkeypatch.setattr(board, "DIRS", {"paper": board.CARDS, "work": board.WORK})
    monkeypatch.setattr(sys, "argv", ["board.py", "add", "ws-147", "--kind", "work", "--title", "Board mirror", "--ws", "WS-147"])
    board.main()
    monkeypatch.setattr(sys, "argv", ["board.py", "set", "ws-147", "status=done", "note=journal/x.md", "papers=2601.00001"])
    board.main()
    m, _ = board.read_card(str(tmp_path / "work/ws-147.md"))
    assert m["kind"] == "work" and m["status"] == "done" and m["papers"] == ["2601.00001"]
    with pytest.raises(SystemExit) as e:
        monkeypatch.setattr(sys, "argv", ["board.py", "has", "ws-147"]); board.main()
    assert e.value.code == 0
