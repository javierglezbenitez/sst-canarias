from pathlib import Path
import numpy as np
import xarray as xr

BBOX = (-19.0, 27.3, -13.0, 29.8)  # lon_min, lat_min, lon_max, lat_max

nc = sorted(Path("data/raw").rglob("*L2P*.nc"))[-1]
print("Fichero:", nc.name, "\n")

with xr.open_dataset(nc, mask_and_scale=True) as ds:
    print("Variables:", list(ds.variables), "\n")
    sst = ds["sea_surface_temperature"].squeeze(drop=True).values.astype("float64")
    lat = ds["lat"].squeeze(drop=True).values.astype("float64")
    lon = ds["lon"].squeeze(drop=True).values.astype("float64")
    q = ds["quality_level"].squeeze(drop=True).values if "quality_level" in ds.variables else None

print("Formas  sst/lat/lon:", sst.shape, lat.shape, lon.shape)
print("Rango lat:", np.nanmin(lat), np.nanmax(lat))
print("Rango lon:", np.nanmin(lon), np.nanmax(lon))
print("Píxeles totales:", sst.size)
print("SST no NaN:", int(np.isfinite(sst).sum()))

lon_min, lat_min, lon_max, lat_max = BBOX
en_caja = (lon >= lon_min) & (lon <= lon_max) & (lat >= lat_min) & (lat <= lat_max)
print("Dentro de la caja de Canarias:", int(en_caja.sum()))
print("Dentro de la caja Y con SST:", int((en_caja & np.isfinite(sst)).sum()))

if q is not None:
    vals, cnt = np.unique(q[en_caja], return_counts=True)
    print("quality_level dentro de la caja:", dict(zip(vals.tolist(), cnt.tolist())))
    for umbral in (5, 4, 3, 2, 1):
        n = int((en_caja & np.isfinite(sst) & (q >= umbral)).sum())
        print(f"  con quality_level >= {umbral}: {n}")