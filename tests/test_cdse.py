import pytest

from sstcanarias import cdse


def test_polygon_is_closed_and_lon_lat_order():
    wkt = cdse.polygon_wkt((-19.0, 27.3, -13.0, 29.8))
    assert wkt.startswith("POLYGON((-19.0 27.3,")
    coords = wkt[len("POLYGON((") : -2].split(",")
    assert coords[0] == coords[-1]


def test_filter_contains_all_parts():
    f = cdse.build_filter((-19.0, 27.3, -13.0, 29.8), "2026-10-01", "2026-10-10")
    assert "Collection/Name eq 'SENTINEL-3'" in f
    assert "contains(Name,'SL_2_WST')" in f
    assert "ContentDate/Start gt 2026-10-01T00:00:00.000Z" in f
    assert "OData.CSC.Intersects(area=geography'SRID=4326;POLYGON((" in f


class FakeResponse:
    def __init__(self, status=200, payload=None, text="", headers=None):
        self.status_code = status
        self._payload = payload or {}
        self.text = text
        self.headers = headers or {}

    def json(self):
        return self._payload

    def close(self):
        pass


def test_search_returns_values(monkeypatch):
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["params"] = params
        return FakeResponse(payload={"value": [{"Id": "1", "Name": "A.SEN3"}]})

    monkeypatch.setattr(cdse.requests, "get", fake_get)
    res = cdse.search_products((-19, 27.3, -13, 29.8), "2026-10-01", "2026-10-10", limit=3)
    assert res == [{"Id": "1", "Name": "A.SEN3"}]
    assert captured["params"]["$top"] == "3"


def test_search_error_includes_status(monkeypatch):
    monkeypatch.setattr(cdse.requests, "get", lambda *a, **k: FakeResponse(status=400, text="bad filter"))
    with pytest.raises(cdse.CdseError, match="HTTP 400"):
        cdse.search_products((-19, 27.3, -13, 29.8), "2026-10-01", "2026-10-10")


def test_token_error_is_explicit(monkeypatch):
    monkeypatch.setattr(cdse.requests, "post", lambda *a, **k: FakeResponse(status=401, text="invalid_grant"))
    with pytest.raises(cdse.CdseError, match="HTTP 401"):
        cdse.get_token("u", "p")


def test_token_is_never_sent_to_foreign_hosts():
    assert cdse._is_allowed("https://download.dataspace.copernicus.eu/x")
    assert not cdse._is_allowed("https://evil.example.com/x")
    assert not cdse._is_allowed("http://download.dataspace.copernicus.eu/x")  # sin https
    assert not cdse._is_allowed("https://dataspace.copernicus.eu.evil.com/x")
