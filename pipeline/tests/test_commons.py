import json
from collections.abc import Mapping
from pathlib import Path

from p3d_pipeline.http import Fetcher
from p3d_pipeline.sources import commons
from p3d_pipeline.sources.wikidata import commons_file_name

ANSWER = {
    "query": {
        "normalized": [{"from": "File:Hematite_crystal.jpg", "to": "File:Hematite crystal.jpg"}],
        "pages": [
            {
                "title": "File:Hematite crystal.jpg",
                "imageinfo": [
                    {
                        "thumburl": "https://upload.wikimedia.org/thumb/640px-Hematite.jpg",
                        "descriptionurl": "https://commons.wikimedia.org/wiki/File:Hematite_crystal.jpg",
                        "extmetadata": {
                            "LicenseShortName": {"value": "CC BY-SA 3.0"},
                            "Artist": {"value": '<a href="//commons.wikimedia.org/User:R">Rob&nbsp;Lavinsky</a>'},
                            "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/3.0"},
                        },
                    }
                ],
            },
            {"title": "File:Missing.jpg", "missing": True},
        ],
    }
}


class FakeFetcher(Fetcher):
    def __init__(self, cache_dir: Path) -> None:
        super().__init__(cache_dir)
        self.requests: list[str] = []

    def get(self, url: str, params: Mapping[str, str] | None = None, **_: object) -> bytes | None:
        self.requests.append((params or {})["titles"])
        return json.dumps(ANSWER).encode()


def test_commons_file_name_from_a_wikidata_value() -> None:
    value = "http://commons.wikimedia.org/wiki/Special:FilePath/Iron%20electrolytic_and%201cm3%20cube.jpg"
    assert commons_file_name(value) == "Iron electrolytic and 1cm3 cube.jpg"


def test_photos_carry_author_and_license_and_are_remembered(tmp_path: Path) -> None:
    fetcher = FakeFetcher(tmp_path)
    found = commons.photos(fetcher, ["Hematite_crystal.jpg", "Missing.jpg", "Formula.svg"])
    photo = found["Hematite_crystal.jpg"]
    assert photo.url.endswith("640px-Hematite.jpg")
    assert photo.author == "Rob Lavinsky"
    assert photo.as_json()["licenseUrl"] == "https://creativecommons.org/licenses/by-sa/3.0"
    assert set(found) == {"Hematite_crystal.jpg"}  # missing file skipped, SVG never asked
    assert fetcher.requests == ["File:Hematite_crystal.jpg|File:Missing.jpg"]

    again = FakeFetcher(tmp_path)
    assert commons.photos(again, ["Hematite_crystal.jpg", "Missing.jpg"]) == found
    assert again.requests == []


def test_plain_text_strips_html_and_shortens() -> None:
    assert commons.plain_text("<b>A</b> &amp; B") == "A & B"
    assert len(commons.plain_text("x" * 500)) == commons.MAX_AUTHOR_CHARS
