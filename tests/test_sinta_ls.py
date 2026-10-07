import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sinta_ls.analysis import coauthor_graph, connecting_subgraph
from sinta_ls.scrape import extract_birth_date, load_roster


def test_birth_date():
    assert extract_birth_date("0526118402") == "26/11/1984"
    assert extract_birth_date("123") is None


def test_roster_drops_retired():
    df = load_roster("UB")
    assert "Sri Rahayu" not in set(df.name_inputted)
    assert df.age.notna().all()


def test_coauthor_graph():
    aff = {"name": "U"}
    data = {
        "1": {"scholar_id": "A", "name_inputted": "Ann", "affiliation_sinta": aff,
              "coauthors": [{"scholar_id": "X", "name": "X", "affiliation": ""},
                            {"scholar_id": "B", "name": "Bob", "affiliation": ""}]},
        "2": {"scholar_id": "B", "name_inputted": "Bob", "affiliation_sinta": aff,
              "coauthors": [{"scholar_id": "X", "name": "X", "affiliation": ""},
                            {"scholar_id": "Y", "name": "Y", "affiliation": ""}]},
        "3": {"scholar_id": None, "name_inputted": "Nobody", "affiliation_sinta": aff, "coauthors": None},
    }
    G = coauthor_graph(data)
    assert set(G) == {"A", "B", "X", "Y"}
    assert G.nodes["B"]["role"] == "main"
    assert G.number_of_edges() == 4
    assert set(connecting_subgraph(G)) == {"A", "B", "X"}


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")
