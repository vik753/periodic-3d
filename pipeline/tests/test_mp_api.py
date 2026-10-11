import json
from pathlib import Path
from typing import Any

import pytest

from p3d_pipeline.sources import mp_api


class FakeFetcher:
    """Records requests; answers like the MP API summary endpoint."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        from collections import Counter

        self.stats: Counter[str] = Counter()

    def get(self, url: str, params: dict[str, str], **kwargs: Any) -> bytes:
        self.calls.append({"url": url, "params": params, **kwargs})
        data = [
            {"material_id": "mp-22862", "theoretical": False, "database_IDs": {"icsd": ["icsd-18189"]}},
            {"material_id": "mp-9999999", "theoretical": True, "database_IDs": {}},
        ]
        return json.dumps({"data": data}).encode()


def test_origins_need_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MP_API_KEY", raising=False)
    fetcher = FakeFetcher()
    assert mp_api.origins(fetcher, ["mp-22862"]) == {}  # type: ignore[arg-type]
    assert fetcher.calls == []


def test_origins_send_the_key_in_a_header_only(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MP_API_KEY", "secret-key")
    fetcher = FakeFetcher()
    result = mp_api.origins(fetcher, ["mp-22862", "mp-9999999", "mp-22862", "agm002"])  # type: ignore[arg-type]
    assert result["mp-22862"].experimental and result["mp-22862"].icsd == ("icsd-18189",)
    assert not result["mp-9999999"].experimental
    (call,) = fetcher.calls
    assert call["headers"] == {"X-API-KEY": "secret-key"}
    assert "secret-key" not in json.dumps(call["params"]) and "secret-key" not in call["url"]
    assert call["params"]["material_ids"] == "mp-22862,mp-9999999"
