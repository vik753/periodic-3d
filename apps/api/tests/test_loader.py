"""Loader checks that need no database."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from p3d_api.loader import DatasetError, gnome_version, load_dataset, load_gnome, open_dataset
from p3d_api.repository import encode_sites, valid_shard

FIXTURES = Path(__file__).parent / "fixtures"


async def test_dataset_loader_refuses_a_gnome_layer() -> None:
    engine: Any = None  # the manifest check runs before any query
    with open_dataset(FIXTURES / "gnome") as root, pytest.raises(DatasetError, match="load-gnome"):
        await load_dataset(engine, root)


async def test_gnome_loader_refuses_a_dataset() -> None:
    engine: Any = None
    with open_dataset(FIXTURES / "dataset") as root, pytest.raises(DatasetError, match="not a GNoME layer"):
        await load_gnome(engine, root)


def test_gnome_version_is_the_release_tag() -> None:
    assert gnome_version({"version": "2026.10.11-r2"}) == "gnome-2026.10.11-r2"


def test_sites_pack_into_seven_bytes_each() -> None:
    import base64

    text = encode_sites([26, 0, 9999, 5000, 8, 1, 2, 3])
    raw = base64.b64decode(text)
    assert len(raw) == 14
    assert raw[0] == 26 and raw[7] == 8
    assert int.from_bytes(raw[3:5], "little") == 9999


def test_shard_prefix_is_four_hex_characters() -> None:
    assert valid_shard("ABcd") == "abcd"
    assert valid_shard("abc") is None
    assert valid_shard("abcg") is None
