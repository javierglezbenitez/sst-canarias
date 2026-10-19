"""Procesado de un producto SLSTR L2 WST: lectura NetCDF, máscara de calidad y estadísticas.

A COMPROBAR con un fichero real: los nombres de variables (sea_surface_temperature, quality_level,
lat, lon) siguen la convención GHRSST. Si no coinciden, el error lista las variables disponibles.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import xarray as xr

from .config import CANARIAS_BBOX, DEFAULT_MIN_QUALITY

SST_VAR = "sea_surface_temperature"
QUALITY_VAR = "quality_level"
LAT_VAR = "lat"
LON_VAR = "lon"


class ProcessingError(RuntimeError):
    pass


@dataclass
class SstPoints:
    """Píxeles válidos de SST (en °C) con su posición."""

    lat: np.ndarray
    lon: np.ndarray
    sst_c: np.ndarray


def find_sst_file(product_dir: Path) -> Path:
    """Localiza el NetCDF principal dentro de un producto .SEN3 (o devuelve el propio .nc)."""
    return find_sst_files(product_dir)[0]


def find_sst_files(product_dir: Path) -> list[Path]:
    """Todos los NetCDF candidatos de un producto (un producto SLSTR WST puede traer varios,
    por ejemplo vista NADIR y vista DUAL, con cobertura distinta)."""
    product_dir = Path(product_dir)
    if product_dir.is_file():
        return [product_dir]
    candidates = sorted(product_dir.rglob("*.nc"))
    if not candidates:
        raise ProcessingError(f"No hay ficheros .nc en {product_dir}")
    preferred = [c for c in candidates if "L2P" in c.name.upper()]
    return preferred or candidates


def _require(ds: xr.Dataset, name: str) -> xr.DataArray:
    if name not in ds.variables:
        raise ProcessingError(
            f"No encuentro la variable '{name}'. Variables disponibles: {sorted(map(str, ds.variables))}"
        )
    return ds[name]


def load_sst(
    path: Path,
    bbox: tuple[float, float, float, float] = CANARIAS_BBOX,
    min_quality: int = DEFAULT_MIN_QUALITY,
) -> SstPoints:
    """Lee el NetCDF, aplica máscara de calidad y de región, y convierte a grados Celsius."""
    with xr.open_dataset(path, mask_and_scale=True) as ds:
        sst = _require(ds, SST_VAR).squeeze(drop=True).values.astype("float64")
        lat = _require(ds, LAT_VAR).squeeze(drop=True).values.astype("float64")
        lon = _require(ds, LON_VAR).squeeze(drop=True).values.astype("float64")
        quality = None
        if QUALITY_VAR in ds.variables:
            quality = ds[QUALITY_VAR].squeeze(drop=True).values

    if not (sst.shape == lat.shape == lon.shape):
        raise ProcessingError(f"Formas incompatibles: sst{sst.shape}, lat{lat.shape}, lon{lon.shape}")

    lon_min, lat_min, lon_max, lat_max = bbox
    mask = np.isfinite(sst) & np.isfinite(lat) & np.isfinite(lon)
    mask &= (lon >= lon_min) & (lon <= lon_max) & (lat >= lat_min) & (lat <= lat_max)
    if quality is not None:
        mask &= quality >= min_quality

    values = sst[mask]
    if values.size and np.nanmedian(values) > 200:  # kelvin
        values = values - 273.15
    return SstPoints(lat=lat[mask], lon=lon[mask], sst_c=values)


def load_best_sst(
    product_dir: Path,
    bbox: tuple[float, float, float, float] = CANARIAS_BBOX,
    min_quality: int = DEFAULT_MIN_QUALITY,
) -> tuple[Path, SstPoints]:
    """Procesa todos los NetCDF del producto y devuelve el que más píxeles válidos tiene en la región."""
    best: tuple[Path, SstPoints] | None = None
    for path in find_sst_files(product_dir):
        try:
            points = load_sst(path, bbox=bbox, min_quality=min_quality)
        except ProcessingError:
            continue  # fichero sin las variables esperadas
        if best is None or points.sst_c.size > best[1].sst_c.size:
            best = (path, points)
    if best is None:
        raise ProcessingError(f"Ningún .nc de {product_dir} contiene las variables esperadas.")
    return best


def summarize(points: SstPoints) -> dict:
    """Estadísticas básicas de la escena. Devuelve ceros/None si no hay píxeles válidos."""
    n = int(points.sst_c.size)
    if n == 0:
        return {"valid_pixels": 0, "mean_c": None, "min_c": None, "max_c": None, "std_c": None}
    return {
        "valid_pixels": n,
        "mean_c": round(float(np.mean(points.sst_c)), 3),
        "min_c": round(float(np.min(points.sst_c)), 3),
        "max_c": round(float(np.max(points.sst_c)), 3),
        "std_c": round(float(np.std(points.sst_c)), 3),
    }
