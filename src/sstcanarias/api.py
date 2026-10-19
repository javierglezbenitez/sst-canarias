"""API REST que expone los resúmenes ya procesados.

Arranque local:  uvicorn sstcanarias.api:app --reload
Documentación interactiva automática en /docs.
"""

from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException

from . import __version__
from .config import get_settings

app = FastAPI(
    title="SST Canarias API",
    version=__version__,
    description="Resúmenes de temperatura superficial del mar derivados de Sentinel-3 SLSTR (Copernicus).",
)


def _load_all() -> list[dict]:
    processed = get_settings().processed_dir
    if not processed.exists():
        return []
    items = []
    for path in sorted(processed.glob("*.json")):
        items.append(json.loads(path.read_text(encoding="utf-8")))
    return items


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.get("/products")
def list_products() -> list[dict]:
    """Escenas procesadas, de más reciente a más antigua."""
    return sorted(_load_all(), key=lambda p: p.get("sensing_start") or "", reverse=True)


@app.get("/products/latest")
def latest_product() -> dict:
    items = list_products()
    if not items:
        raise HTTPException(status_code=404, detail="Aún no hay escenas procesadas.")
    return items[0]


@app.get("/products/{name}")
def get_product(name: str) -> dict:
    for item in _load_all():
        if item.get("name") == name:
            return item
    raise HTTPException(status_code=404, detail=f"No existe la escena '{name}'.")
