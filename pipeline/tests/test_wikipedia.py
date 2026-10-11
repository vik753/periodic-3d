import json
from collections.abc import Mapping
from pathlib import Path

from p3d_pipeline.http import Fetcher
from p3d_pipeline.sources import wikipedia


class FakeFetcher(Fetcher):
    """Answers extract queries from a dictionary and counts the requests."""

    def __init__(self, cache_dir: Path, texts: dict[str, str], cut_off: bool = False) -> None:
        super().__init__(cache_dir)
        self.texts = texts
        self.cut_off = cut_off
        self.requests: list[list[str]] = []

    def get(self, url: str, params: Mapping[str, str] | None = None, **_: object) -> bytes | None:
        titles = (params or {})["titles"].split("|")
        self.requests.append(titles)
        pages = [{"title": title, "extract": self.texts.get(title, "")} for title in titles]
        if self.cut_off:
            pages = pages[:1]
        data: dict[str, object] = {"query": {"pages": pages}}
        if self.cut_off:
            data["continue"] = {"excontinue": 1}
        return json.dumps(data).encode()


def test_extracts_are_remembered_per_title(tmp_path: Path) -> None:
    texts = {"Water": "Water is H2O.", "Ozone": "Ozone is O3."}
    first = FakeFetcher(tmp_path, texts)
    assert wikipedia.extracts(first, "en", ["Water", "Ozone", "Nothing"]) == texts
    assert len(first.requests) == 1

    # A new list: only the new title is requested; "Nothing" is remembered as empty.
    second = FakeFetcher(tmp_path, {**texts, "Benzene": "Benzene is C6H6."})
    result = wikipedia.extracts(second, "en", ["Water", "Benzene", "Nothing"])
    assert result == {"Water": "Water is H2O.", "Benzene": "Benzene is C6H6."}
    assert second.requests == [["Benzene"]]


def test_cut_off_answers_are_asked_again(tmp_path: Path) -> None:
    texts = {"A": "Text A.", "B": "Text B."}
    assert wikipedia.extracts(FakeFetcher(tmp_path, texts, cut_off=True), "en", ["A", "B"]) == {"A": "Text A."}
    again = FakeFetcher(tmp_path, texts)
    assert wikipedia.extracts(again, "en", ["A", "B"]) == texts
    assert again.requests == [["B"]]


def test_parse_extracts_maps_redirects_back() -> None:
    data = {
        "query": {
            "normalized": [{"from": "water", "to": "Water"}],
            "redirects": [{"from": "Water", "to": "Water (molecule)"}],
            "pages": [{"title": "Water (molecule)", "extract": " H2O. "}],
        }
    }
    assert wikipedia.parse_extracts(data, ["water"]) == {"water": "H2O."}
