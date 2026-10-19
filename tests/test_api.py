import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SST_DATA_DIR", str(tmp_path))
    processed = tmp_path / "processed"
    processed.mkdir()
    for name, start in (("A", "2026-10-01T10:00:00Z"), ("B", "2026-10-05T10:00:00Z")):
        (processed / f"{name}.json").write_text(
            json.dumps({"name": name, "sensing_start": start, "valid_pixels": 10, "mean_c": 21.0})
        )
    from sstcanarias.api import app

    return TestClient(app)


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_products_sorted_newest_first(client):
    names = [p["name"] for p in client.get("/products").json()]
    assert names == ["B", "A"]


def test_latest(client):
    assert client.get("/products/latest").json()["name"] == "B"


def test_unknown_product_404(client):
    assert client.get("/products/ZZZ").status_code == 404


def test_latest_404_when_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("SST_DATA_DIR", str(tmp_path))
    from sstcanarias.api import app

    assert TestClient(app).get("/products/latest").status_code == 404
