"""Línea de comandos.

Ejemplos:
    python -m sstcanarias.cli search  --start 2026-10-10 --end 2026-10-18
    python -m sstcanarias.cli run     --start 2026-10-10 --end 2026-10-18 --limit 2
    python -m sstcanarias.cli process --path data/raw/MI_PRODUCTO.SEN3
Credenciales: variables de entorno CDSE_USERNAME y CDSE_PASSWORD (nunca en el código).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from . import cdse
from .config import CANARIAS_BBOX, PRODUCT_TOKEN, get_settings
from .plotting import plot_sst
from .processing import load_best_sst, summarize


SCENE_RE = re.compile(r"^(S3[AB])_.*?(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})")


def parse_scene_name(name: str) -> tuple[str, str] | None:
    """Extrae (satélite, fecha ISO UTC) del nombre de un producto Sentinel-3. None si no encaja."""
    m = SCENE_RE.match(name)
    if not m:
        return None
    sat, y, mo, d, h, mi, s = m.groups()
    return sat, f"{y}-{mo}-{d}T{h}:{mi}:{s}Z"


def scene_title(name: str) -> str:
    parsed = parse_scene_name(name)
    if not parsed:
        return f"SST Canarias · {name[:40]}"
    sat, iso = parsed
    return f"SST Canarias · Sentinel-3{sat[-1]} · {iso[8:10]}/{iso[5:7]}/{iso[:4]} {iso[11:16]} UTC"


def process_product(product_dir: Path, name: str | None = None, sensing_start: str | None = None) -> dict:
    """Procesa un producto ya descargado: estadísticas JSON + mapa PNG."""
    settings = get_settings()
    nc_path, points = load_best_sst(product_dir)
    name = (name or Path(product_dir).stem).removesuffix(".SEN3")  # mismo nombre en run y process
    if sensing_start is None and (parsed := parse_scene_name(name)):
        sensing_start = parsed[1]
    result = {"name": name, "sensing_start": sensing_start, "source_file": nc_path.name, **summarize(points)}

    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    (settings.processed_dir / f"{name}.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    plot_sst(points, settings.processed_dir / f"{name}.png", title=scene_title(name))
    return result


def _credentials() -> tuple[str, str]:
    user, pwd = os.environ.get("CDSE_USERNAME"), os.environ.get("CDSE_PASSWORD")
    if not user or not pwd:
        sys.exit("Define CDSE_USERNAME y CDSE_PASSWORD en el entorno (ver .env.example).")
    return user, pwd


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sstcanarias")
    sub = parser.add_subparsers(dest="cmd", required=True)

    for name in ("search", "run"):
        p = sub.add_parser(name)
        p.add_argument("--start", required=True, help="YYYY-MM-DD")
        p.add_argument("--end", required=True, help="YYYY-MM-DD")
        p.add_argument("--limit", type=int, default=2)
    p_proc = sub.add_parser("process")
    p_proc.add_argument("--path", required=True, help="Carpeta .SEN3 o fichero .nc")

    args = parser.parse_args(argv)

    if args.cmd == "process":
        print(json.dumps(process_product(Path(args.path)), indent=2, ensure_ascii=False))
        return 0

    products = cdse.search_products(CANARIAS_BBOX, args.start, args.end, args.limit, PRODUCT_TOKEN)
    if not products:
        print("Sin resultados para ese rango. Prueba a ampliar las fechas.")
        return 1
    if args.cmd == "search":
        for p in products:
            print(p["Name"], p.get("ContentDate", {}).get("Start", ""))
        return 0

    token = cdse.get_token(*_credentials())
    raw_dir = get_settings().raw_dir
    for p in products:
        print(f"Descargando {p['Name']} ...")
        product_dir = cdse.download_product(p, token, raw_dir)
        res = process_product(product_dir, name=p["Name"], sensing_start=p.get("ContentDate", {}).get("Start"))
        print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
