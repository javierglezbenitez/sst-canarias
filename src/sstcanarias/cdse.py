"""Cliente mínimo del Copernicus Data Space Ecosystem (CDSE).

IMPORTANTE: las URLs de catálogo y el filtro por colección/fecha/polígono están contrastados con la
documentación oficial. Lo siguiente NO pude verificarlo y debe comprobarse en la primera ejecución real:
  - TOKEN_URL y client_id "cdse-public" (autenticación por contraseña).
  - DOWNLOAD_URL (descarga con $value).
  - El filtro contains(Name, 'SL_2_WST').
Si algo falla, el mensaje de error indica qué respuesta devolvió el servidor.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from urllib.parse import urlparse

import requests

CATALOGUE_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
# A COMPROBAR en la primera ejecución:
TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
DOWNLOAD_URL = "https://download.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"
CLIENT_ID = "cdse-public"

# El token solo se reenvía a dominios de Copernicus, nunca a terceros.
ALLOWED_HOST_SUFFIX = ".dataspace.copernicus.eu"
MAX_REDIRECTS = 5
TIMEOUT = 60


class CdseError(RuntimeError):
    """Error al hablar con el CDSE, con contexto suficiente para depurar."""


def get_token(username: str, password: str) -> str:
    """Obtiene un access token con usuario y contraseña de tu cuenta CDSE."""
    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id": CLIENT_ID,
            "grant_type": "password",
            "username": username,
            "password": password,
        },
        timeout=TIMEOUT,
    )
    if resp.status_code != 200:
        raise CdseError(f"No se pudo obtener el token (HTTP {resp.status_code}): {resp.text[:300]}")
    token = resp.json().get("access_token")
    if not token:
        raise CdseError("La respuesta del servidor de identidad no incluye access_token.")
    return token


def polygon_wkt(bbox: tuple[float, float, float, float]) -> str:
    """Polígono WKT cerrado (orden lon lat) a partir de una caja geográfica."""
    lon_min, lat_min, lon_max, lat_max = bbox
    ring = [
        (lon_min, lat_min),
        (lon_max, lat_min),
        (lon_max, lat_max),
        (lon_min, lat_max),
        (lon_min, lat_min),
    ]
    coords = ",".join(f"{lon} {lat}" for lon, lat in ring)
    return f"POLYGON(({coords}))"


def build_filter(
    bbox: tuple[float, float, float, float],
    start: str,
    end: str,
    product_token: str = "SL_2_WST",
) -> str:
    """Construye el $filter OData. Las fechas van en formato YYYY-MM-DD."""
    return (
        "Collection/Name eq 'SENTINEL-3'"
        f" and contains(Name,'{product_token}')"
        f" and ContentDate/Start gt {start}T00:00:00.000Z"
        f" and ContentDate/Start lt {end}T23:59:59.999Z"
        f" and OData.CSC.Intersects(area=geography'SRID=4326;{polygon_wkt(bbox)}')"
    )


def search_products(
    bbox: tuple[float, float, float, float],
    start: str,
    end: str,
    limit: int = 5,
    product_token: str = "SL_2_WST",
) -> list[dict]:
    """Busca productos y devuelve una lista de diccionarios con Id, Name y ContentDate."""
    params = {
        "$filter": build_filter(bbox, start, end, product_token),
        "$orderby": "ContentDate/Start desc",
        "$top": str(limit),
    }
    resp = requests.get(CATALOGUE_URL, params=params, timeout=TIMEOUT)
    if resp.status_code != 200:
        raise CdseError(f"Búsqueda fallida (HTTP {resp.status_code}): {resp.text[:300]}")
    return resp.json().get("value", [])


def _is_allowed(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and (parsed.hostname or "").endswith(ALLOWED_HOST_SUFFIX)


def _get_following_redirects(url: str, token: str) -> requests.Response:
    """GET en streaming que reenvía el token en cada redirección, solo hacia dominios de Copernicus."""
    headers = {"Authorization": f"Bearer {token}"}
    session = requests.Session()
    for _ in range(MAX_REDIRECTS + 1):
        if not _is_allowed(url):
            raise CdseError(f"Redirección a un dominio no permitido, se aborta: {url}")
        resp = session.get(url, headers=headers, stream=True, allow_redirects=False, timeout=TIMEOUT)
        if resp.status_code in (301, 302, 303, 307, 308):
            url = resp.headers.get("Location", "")
            resp.close()
            continue
        return resp
    raise CdseError("Demasiadas redirecciones al descargar el producto.")


def download_product(product: dict, token: str, out_dir: Path) -> Path:
    """Descarga y descomprime un producto. Devuelve la carpeta .SEN3 resultante."""
    out_dir.mkdir(parents=True, exist_ok=True)
    name = product["Name"]
    target = out_dir / (name if name.endswith(".SEN3") else f"{name}.SEN3")
    if target.exists():
        return target  # ya descargado

    url = DOWNLOAD_URL.format(product_id=product["Id"])
    resp = _get_following_redirects(url, token)
    if resp.status_code != 200:
        raise CdseError(f"Descarga fallida (HTTP {resp.status_code}): {resp.text[:300]}")

    zip_path = out_dir / f"{product['Id']}.zip"
    with open(zip_path, "wb") as fh:
        for chunk in resp.iter_content(chunk_size=1024 * 1024):
            fh.write(chunk)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(out_dir)
    zip_path.unlink()
    if not target.exists():
        # El zip puede traer la carpeta con otro nombre; devolvemos la primera .SEN3 que aparezca.
        found = sorted(out_dir.glob("*.SEN3"))
        if not found:
            raise CdseError("El zip descargado no contiene ninguna carpeta .SEN3.")
        return found[-1]
    return target
