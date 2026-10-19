"""Mapa de temperatura superficial del mar."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # sin pantalla: funciona en servidores y contenedores
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .config import CANARIAS_BBOX  # noqa: E402
from .processing import SstPoints  # noqa: E402

MAX_POINTS = 200_000

# Posición aproximada (lon, lat) del centro de cada isla, solo como referencia visual.
ISLANDS: dict[str, tuple[float, float]] = {
    "El Hierro": (-18.00, 27.75),
    "La Palma": (-17.87, 28.68),
    "La Gomera": (-17.11, 28.10),
    "Tenerife": (-16.58, 28.29),
    "Gran Canaria": (-15.60, 27.96),
    "Fuerteventura": (-14.00, 28.40),
    "Lanzarote": (-13.63, 29.04),
}


def plot_sst(points: SstPoints, out_path: Path, title: str = "SST Canarias") -> Path:
    """Dibuja los píxeles válidos como dispersión y guarda un PNG."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lat, lon, sst = points.lat, points.lon, points.sst_c
    if sst.size > MAX_POINTS:
        idx = np.random.default_rng(0).choice(sst.size, MAX_POINTS, replace=False)
        lat, lon, sst = lat[idx], lon[idx], sst[idx]

    lon_min, lat_min, lon_max, lat_max = CANARIAS_BBOX
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=130)
    if sst.size:
        sc = ax.scatter(lon, lat, c=sst, s=2, cmap="RdYlBu_r", linewidths=0)
        fig.colorbar(sc, ax=ax, label="Temperatura superficial del mar (°C)")
    else:
        ax.text(0.5, 0.5, "Sin píxeles válidos en la región", ha="center", va="center", transform=ax.transAxes)
    for island, (ilon, ilat) in ISLANDS.items():
        ax.plot(ilon, ilat, marker="o", markersize=4, color="black", markerfacecolor="white", zorder=5)
        ax.annotate(island, (ilon, ilat), xytext=(4, 4), textcoords="offset points", fontsize=7, zorder=5)
    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(lat_min, lat_max)
    ax.set_aspect(1 / np.cos(np.deg2rad((lat_min + lat_max) / 2)))
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    return out_path
