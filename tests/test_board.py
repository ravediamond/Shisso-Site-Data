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
