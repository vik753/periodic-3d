from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VERSION = "2026.01.01-test"


async def get(client: Any, path: str, **kwargs: Any) -> Any:
    response = await client.get(path, **kwargs)
    assert response.status_code == 200, response.text
    return response.json()


async def test_meta(client: Any) -> None:
    response = await client.get("/api/v1/meta")
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == VERSION
    assert body["apiVersion"] == 1
    assert body["schemaVersion"] == 1
    assert body["counts"]["compounds"] == 4
    assert response.headers["etag"] == f'W/"{VERSION}-test"'
    assert "s-maxage=" in response.headers["cache-control"]


async def test_conditional_request_returns_304(client: Any) -> None:
    first = await client.get("/api/v1/elements")
    second = await client.get("/api/v1/elements", headers={"If-None-Match": first.headers["etag"]})
    assert second.status_code == 304
    assert second.content == b""


async def test_elements(client: Any) -> None:
    body = await get(client, "/api/v1/elements")
    assert [element["symbol"] for element in body["elements"]] == ["H", "O", "Fe"]
    counts = {element["symbol"]: element["compoundCount"] for element in body["elements"]}
    assert counts == {"H": 2, "O": 4, "Fe": 1}
    iron = body["elements"][2]
    assert iron["names"]["uk"] == "Ферум"
    assert iron["hasSubstance"] is True
    assert body["elements"][0]["hasSubstance"] is False


async def test_element_detail(client: Any) -> None:
    body = await get(client, "/api/v1/elements/fe")  # symbols are case-insensitive
    assert body["symbol"] == "Fe"
    assert body["electronegativity"] == 1.83
    assert body["partners"] == [{"z": 8, "symbol": "O", "count": 1}]
    assert [compound["id"] for compound in body["topCompounds"]] == ["Q103223"]
    assert body["substance"]["info"]["kind"] == "crystal"
    assert body["substance"]["names"]["uk"] == "залізо"
    assert len(body["substance"]["structure"]["atoms"]) == 9


async def test_element_partners_and_top_compounds_are_sorted(client: Any) -> None:
    body = await get(client, "/api/v1/elements/O")
    assert [partner["symbol"] for partner in body["partners"]] == ["H", "Fe"]
    assert [compound["id"] for compound in body["topCompounds"]] == ["Q283", "Q36933", "Q103223", "Q849881"]


async def test_unknown_element_is_404(client: Any) -> None:
    response = await client.get("/api/v1/elements/Xx")
    assert response.status_code == 404
    assert response.headers["cache-control"] == "public, max-age=60"


async def test_compound(client: Any) -> None:
    body = await get(client, "/api/v1/compounds/q283")
    assert body["id"] == "Q283"
    assert body["formula"] == "H₂O"
    assert body["names"]["ru"] == "Вода"
    assert body["structureInfo"]["source"] == "pubchem"
    assert len(body["structure"]["atoms"]) == 3
    assert body["classes"] == [
        {
            "qid": "Q113145171",
            "names": {"en": "chemical compound", "ru": "химическое соединение", "uk": "хімічна сполука"},
        }
    ]
    roles = [source["role"] for source in body["sources"]]
    assert roles[0] == "identity"
    assert {"description", "properties", "structure"} <= set(roles)
    wikipedia = [source["url"] for source in body["sources"] if source["role"] == "description"]
    assert "https://ru.wikipedia.org/wiki/%D0%92%D0%BE%D0%B4%D0%B0" in wikipedia


async def test_compound_with_missing_structure_file(client: Any) -> None:
    body = await get(client, "/api/v1/compounds/Q36933")
    assert body["structure"] is None
    assert body["structureInfo"] is None
    assert "structure" not in [source["role"] for source in body["sources"]]


async def test_ion_keeps_its_charge(client: Any) -> None:
    body = await get(client, "/api/v1/compounds/Q849881")
    assert body["charge"] == 1
    assert body["formula"] == "H₃O⁺"


async def test_unknown_compound_is_404(client: Any) -> None:
    assert (await client.get("/api/v1/compounds/Q1")).status_code == 404


async def test_pair_in_both_orders(client: Any) -> None:
    forward = await get(client, "/api/v1/pairs/O-Fe")
    backward = await get(client, "/api/v1/pairs/fe-o")
    assert forward == backward
    assert forward["a"] == {"z": 8, "symbol": "O"}
    assert forward["b"] == {"z": 26, "symbol": "Fe"}
    assert [compound["id"] for compound in forward["compounds"]] == ["Q103223"]


async def test_pair_order_follows_the_dataset(client: Any) -> None:
    body = await get(client, "/api/v1/pairs/H-O")
    assert [compound["id"] for compound in body["compounds"]] == ["Q283", "Q849881"]
    assert body["count"] == 2


async def test_pair_without_compounds_is_404(client: Any) -> None:
    assert (await client.get("/api/v1/pairs/H-Fe")).status_code == 404
    assert (await client.get("/api/v1/pairs/H")).status_code == 404


async def test_query_contains(client: Any) -> None:
    body = await get(client, "/api/v1/compounds", params={"elements": "O,H"})
    assert body["elements"] == ["H", "O"]
    assert body["mode"] == "contains"
    assert body["total"] == 2
    assert [compound["id"] for compound in body["compounds"]] == ["Q283", "Q849881"]


async def test_query_only(client: Any) -> None:
    body = await get(client, "/api/v1/compounds", params={"elements": "O", "mode": "only"})
    assert [compound["id"] for compound in body["compounds"]] == ["Q36933"]
    body = await get(client, "/api/v1/compounds", params={"elements": "O"})
    assert body["total"] == 4


async def test_query_paging(client: Any) -> None:
    body = await get(client, "/api/v1/compounds", params={"elements": "O", "limit": 2, "offset": 1})
    assert [compound["id"] for compound in body["compounds"]] == ["Q36933", "Q103223"]
    assert body["total"] == 4


async def test_query_rejects_unknown_elements(client: Any) -> None:
    response = await client.get("/api/v1/compounds", params={"elements": "O,Xx"})
    assert response.status_code == 400
    assert "Xx" in response.json()["detail"]


async def test_index(client: Any) -> None:
    body = await get(client, "/api/v1/index")
    assert body["fields"] == ["id", "formula", "elements", "fame", "kind", "names"]
    assert body["rows"][0][:5] == ["Q283", "H₂O", [1, 8], 330, "molecule"]
    assert len(body["rows"]) == 4


async def test_health(client: Any) -> None:
    body = await get(client, "/health")
    assert body == {"status": "ok", "version": VERSION}


async def test_openapi_lists_the_endpoints(client: Any) -> None:
    body = await get(client, "/api/openapi.json")
    assert "/api/v1/elements/{symbol}" in body["paths"]


async def test_static_export_matches_the_api(loaded_database: str, client: Any, tmp_path: Path) -> None:
    from p3d_api.db import Database
    from p3d_api.export import export_static

    database = Database(loaded_database)
    try:
        report = await export_static(database, tmp_path)
    finally:
        await database.dispose()
    assert report.missing == []
    # meta + elements list + 3 elements + 4 compounds + 2 pairs + index
    assert report.files == 12
    root = tmp_path / VERSION
    pairs = {
        "meta": tmp_path / "meta.json",
        "elements": root / "elements.json",
        "elements/Fe": root / "elements" / "Fe.json",
        "compounds/Q283": root / "compounds" / "Q283.json",
        "pairs/O-Fe": root / "pairs" / "O-Fe.json",
        "index": root / "index.json",
    }
    for api_path, file in pairs.items():
        assert json.loads(file.read_text(encoding="utf-8")) == await get(client, f"/api/v1/{api_path}")


async def test_search_by_formula_and_name(client: Any) -> None:
    body = await get(client, "/api/v1/search", params={"q": "H2O"})
    assert body["compounds"][0]["id"] == "Q283"
    body = await get(client, "/api/v1/search", params={"q": "гемати́т"})  # stress mark is ignored
    assert [compound["id"] for compound in body["compounds"]] == ["Q103223"]
    body = await get(client, "/api/v1/search", params={"q": "вод"})
    assert "Q283" in [compound["id"] for compound in body["compounds"]]


async def test_search_escapes_wildcards(client: Any) -> None:
    body = await get(client, "/api/v1/search", params={"q": "%"})
    assert body["compounds"] == []
    assert (await client.get("/api/v1/search", params={"q": ""})).status_code == 422


async def test_similar_elements_from_vectors(client: Any) -> None:
    body = await get(client, "/api/v1/elements/Fe")
    assert [item["symbol"] for item in body["similar"]] == ["O", "H"]
    assert abs(body["similar"][0]["score"] - 0.6) < 0.01


async def test_similar_compounds_from_vectors(client: Any) -> None:
    body = await get(client, "/api/v1/compounds/Q103223")
    assert [compound["id"] for compound in body["similar"]] == ["Q36933", "Q283", "Q849881"]
