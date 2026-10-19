"""Tests con un NetCDF SINTÉTICO que imita la estructura GHRSST. Solo validan la lógica del código;
no son datos reales de Sentinel-3."""

import numpy as np
import pytest
import xarray as xr

from sstcanarias.plotting import plot_sst
from sstcanarias.processing import ProcessingError, find_sst_file, load_sst, summarize


@pytest.fixture
def synthetic_nc(tmp_path):
    lat = np.array([[28.0, 28.0, 28.0], [28.5, 28.5, 28.5], [40.0, 40.0, 40.0]])  # última fila fuera de región
    lon = np.array([[-16.0, -15.5, -15.0], [-16.0, -15.5, -15.0], [-16.0, -15.5, -15.0]])
    sst_k = np.array([[293.15, 294.15, np.nan], [295.15, 296.15, 297.15], [290.0, 290.0, 290.0]])
    quality = np.array([[5, 5, 5], [5, 2, 4], [5, 5, 5]])  # un píxel de baja calidad (2)
    ds = xr.Dataset(
        {
            "sea_surface_temperature": (("y", "x"), sst_k),
            "quality_level": (("y", "x"), quality),
            "lat": (("y", "x"), lat),
            "lon": (("y", "x"), lon),
        }
    )
    path = tmp_path / "L2P_GHRSST_test.nc"
    ds.to_netcdf(path, engine="netcdf4")
    return path


def test_load_filters_quality_region_and_converts_to_celsius(synthetic_nc):
    pts = load_sst(synthetic_nc)
    # válidos: (0,0)=20.0, (0,1)=21.0, (1,0)=22.0, (1,2)=24.0 ; fuera: NaN, calidad 2, fila de lat 40
    assert sorted(np.round(pts.sst_c, 2)) == [20.0, 21.0, 22.0, 24.0]


def test_summary_values(synthetic_nc):
    s = summarize(load_sst(synthetic_nc))
    assert s["valid_pixels"] == 4
    assert s["min_c"] == 20.0
    assert s["max_c"] == 24.0
    assert s["mean_c"] == 21.75


def test_summary_empty_returns_none_values():
    from sstcanarias.processing import SstPoints

    s = summarize(SstPoints(lat=np.array([]), lon=np.array([]), sst_c=np.array([])))
    assert s["valid_pixels"] == 0 and s["mean_c"] is None


def test_missing_variable_lists_available(tmp_path):
    path = tmp_path / "bad.nc"
    xr.Dataset({"otra_cosa": (("x",), [1.0])}).to_netcdf(path, engine="netcdf4")
    with pytest.raises(ProcessingError, match="Variables disponibles"):
        load_sst(path)


def test_find_sst_file_prefers_l2p(tmp_path):
    (tmp_path / "otro.nc").write_bytes(b"")
    (tmp_path / "L2P_x.nc").write_bytes(b"")
    assert find_sst_file(tmp_path).name == "L2P_x.nc"


def test_plot_creates_png(synthetic_nc, tmp_path):
    out = plot_sst(load_sst(synthetic_nc), tmp_path / "out" / "mapa.png")
    assert out.exists() and out.stat().st_size > 1000
