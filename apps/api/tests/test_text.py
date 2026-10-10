from p3d_api.text import normalize_text, search_text


def test_normalize_text_matches_the_frontend() -> None:
    assert normalize_text("Гемати́т") == "гематит"
    assert normalize_text("H₂O") == "h2o"
    assert normalize_text("Гётит") == "гетит"
    assert normalize_text("NH₄⁺") == "nh4"
    assert normalize_text("Йод") == "иод"


def test_search_text() -> None:
    assert search_text("Fe₂O₃", {"en": "Hematite", "ru": "Гематит"}) == "fe2o3 | hematite | гематит"
