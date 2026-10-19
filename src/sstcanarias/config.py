"""Configuración central del proyecto."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Caja geográfica (lon_min, lat_min, lon_max, lat_max) que cubre el archipiélago con margen.
CANARIAS_BBOX: tuple[float, float, float, float] = (-19.0, 27.3, -13.0, 29.8)

# Producto Sentinel-3 SLSTR nivel 2, temperatura superficial del mar (WST).
PRODUCT_TOKEN = "SL_2_WST"

# Nivel de calidad mínimo aceptado (en GHRSST, 5 = mejor calidad). A COMPROBAR con un fichero real.
DEFAULT_MIN_QUALITY = 4


@dataclass(frozen=True)
class Settings:
    data_dir: Path

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"


def get_settings() -> Settings:
    """Lee la configuración del entorno. SST_DATA_DIR indica dónde guardar los datos."""
    return Settings(data_dir=Path(os.environ.get("SST_DATA_DIR", "data")).resolve())
