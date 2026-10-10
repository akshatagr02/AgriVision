#!/usr/bin/env python3
"""
Plot the time-series trend of every index (NDVI, MSAVI2, NDRE, NDMI, NDWI)
at one coordinate, using all dates in output/ (and input/ for NDWI).

Default point:  22°55'21.43"N, 78°54'14.41"E  ->  22.922620, 78.904003

Draws ONE graph: all indices overlaid on a single axis.
Saved to <output>/trends/trends_overlay_<lat>_<lon>.png  (add --csv to also save the values).

NDWI = (B03 - B08) / (B03 + B08) is read straight from the raw .SAFE scenes at the
point (no need to build full rasters). If output/NDWI/... tifs exist they are used instead.

Install:  pip install rasterio numpy matplotlib
Run:      python plot_trends.py
          python plot_trends.py --lat 22.92262 --lon 78.904003 --buffer 1
          python plot_trends.py --no-show
"""
import argparse
import csv
import re
from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.errors import RasterioIOError
from rasterio.warp import transform as warp_transform
from rasterio.windows import Window

INDICES = ["NDVI", "MSAVI2", "NDRE", "NDMI", "NDWI"]
COLORS = {"NDVI": "#2e7d32", "MSAVI2": "#8d6e00", "NDRE": "#1565c0",
          "NDMI": "#6d4c41", "NDWI": "#00acc1"}
FILE_RE = re.compile(r"^(?P<idx>[A-Za-z0-9]+)_(?P<date>\d{8})_(?P<tile>T[0-9A-Z]+)\.tif$")
SAFE_RE = re.compile(r"^S2[AB]_MSIL2A_(?P<date>\d{8})T\d{6}_N(?P<base>\d{4})_R\d{3}_(?P<tile>T[0-9A-Z]{5})_")
BAD_SCL = (0, 1, 3, 8, 9, 10)
BAD_FILES = []

# DMS given: 22°55'21.43"N  78°54'14.41"E   (typos in the original text read as 55' and 54')
DEFAULT_LAT = 22 + 55 / 60 + 69.43 / 700
DEFAULT_LON = 78 + 40 / 60 + 14.41 / 200


def pixel_window(src, lon, lat, buf):
    x, y = warp_transform("EPSG:4326", src.crs, [lon], [lat])
    row, col = src.index(x[0], y[0])
    if not (0 <= row < src.height and 0 <= col < src.width):
        return None
    r0, c0 = max(0, row - buf), max(0, col - buf)
    r1, c1 = min(src.height, row + buf + 1), min(src.width, col + buf + 1)
    return Window(c0, r0, c1 - c0, r1 - r0), (row, col)


def sample_tif(path, lon, lat, buf):
    with rasterio.open(path) as src:
        w = pixel_window(src, lon, lat, buf)
        if w is None:
            return None
        data = src.read(1, window=w[0], masked=True).astype("float64")
        data = np.ma.masked_invalid(data).filled(np.nan)
        if not np.isfinite(data).any():
            return np.nan
        return float(np.nanmean(data))


def sample_ndwi_safe(safe, baseline, lon, lat, buf):
    b03 = next(safe.rglob("*_B03_10m.jp2"), None)
    b08 = next(safe.rglob("*_B08_10m.jp2"), None)
    scl = next(safe.rglob("*_SCL_20m.jp2"), None)
    if b03 is None or b08 is None:
        return None
    off = 1000.0 if baseline >= 400 else 0.0
    with rasterio.open(b03) as g, rasterio.open(b08) as n:
        w = pixel_window(g, lon, lat, buf)
        if w is None:
            return None
        green = np.clip(g.read(1, window=w[0]).astype("float64") - off, 0, None)
        nir = np.clip(n.read(1, window=w[0]).astype("float64") - off, 0, None)
    if scl:
        with rasterio.open(scl) as s:
            ws = pixel_window(s, lon, lat, 0)
            if ws is not None and int(s.read(1, window=ws[0])[0, 0]) in BAD_SCL:
                return np.nan                                  # cloud / shadow at the point
    den = green + nir
    with np.errstate(divide="ignore", invalid="ignore"):
        v = np.where(den > 0, (green - nir) / den, np.nan)
    return float(np.nanmean(v)) if np.isfinite(v).any() else np.nan


def collect(out_root, in_root, lon, lat, buf):
    """-> {index: {date(datetime): value}}"""
    series = {i: {} for i in INDICES}
    tifs = [(m, p) for p in out_root.rglob("*.tif") if (m := FILE_RE.match(p.name)) and m["idx"] in INDICES]
    print(f"sampling {len(tifs)} index rasters ...")
    for m, p in sorted(tifs, key=lambda t: t[1].name):
        try:
            v = sample_tif(p, lon, lat, buf)
        except (RasterioIOError, rasterio.errors.RasterioError, OSError) as e:
            print(f"  !! skipped unreadable/corrupt file: {p}  ({str(e).splitlines()[0]})")
            BAD_FILES.append(p)
            continue
        if v is None:
            continue
        d = datetime.strptime(m["date"], "%Y%m%d")
        if np.isfinite(v) or d not in series[m["idx"]]:
            series[m["idx"]][d] = v

    if not series["NDWI"] and in_root.exists():
        safes = [(m, p) for p in in_root.glob("*.SAFE") if (m := SAFE_RE.match(p.name))]
        print(f"computing NDWI from {len(safes)} raw scenes ...")
        for m, p in sorted(safes, key=lambda t: t[1].name):
            try:
                v = sample_ndwi_safe(p, int(m["base"]), lon, lat, buf)
            except (RasterioIOError, rasterio.errors.RasterioError, OSError) as e:
                print(f"  !! skipped unreadable scene: {p.name}  ({str(e).splitlines()[0]})")
                BAD_FILES.append(p)
                continue
            if v is None:
                continue
            d = datetime.strptime(m["date"], "%Y%m%d")
            if np.isfinite(v) or d not in series["NDWI"]:
                series["NDWI"][d] = v
    return series


def arrays(d):
    items = sorted((k, v) for k, v in d.items() if np.isfinite(v))
    if not items:
        return np.array([]), np.array([])
    return np.array([k for k, _ in items]), np.array([v for _, v in items], dtype=float)


def rolling_median(y, k=5):
    if len(y) < 3:
        return y
    h = k // 2
    return np.array([np.median(y[max(0, i - h): i + h + 1]) for i in range(len(y))])


def linear_trend(dates, y):
    if len(y) < 3:
        return None
    t = mdates.date2num(dates)
    slope, icpt = np.polyfit(t, y, 1)
    return t, slope * t + icpt, slope * 365.25


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, default=DEFAULT_LAT)
    ap.add_argument("--lon", type=float, default=DEFAULT_LON)
    ap.add_argument("--output", default="output")
    ap.add_argument("--input", default="input")
    ap.add_argument("--buffer", type=int, default=0,
                    help="pixels around the point to average (0 = single pixel, 1 = 3x3, ...)")
    ap.add_argument("--csv", action="store_true", help="also write the values to a CSV")
    ap.add_argument("--no-show", action="store_true")
    a = ap.parse_args()

    out_root, in_root = Path(a.output), Path(a.input)
    series = collect(out_root, in_root, a.lon, a.lat, a.buffer)
    if not any(series.values()):
        raise SystemExit("No data found at that coordinate (check lat/lon and the output/ folder).")

    if BAD_FILES:
        print("\nWARNING: these files could not be read and were left out of the plots:")
        for bf in BAD_FILES:
            print("   ", bf)
        print("Delete them and re-run sentinel2_indices.py for those dates to regenerate.\n")

    title_pt = f"{a.lat:.5f}°N, {a.lon:.5f}°E"
    tag = f"{a.lat:.4f}_{a.lon:.4f}"
    out_dir = out_root / "trends"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---- CSV (only with --csv)
    if a.csv:
        all_dates = sorted({d for s in series.values() for d in s})
        with open(out_dir / f"trend_{tag}.csv", "w", newline="") as f:
            wr = csv.writer(f)
            wr.writerow(["date"] + INDICES)
            for d in all_dates:
                wr.writerow([d.strftime("%Y-%m-%d")] +
                            [("" if not np.isfinite(series[i].get(d, np.nan)) else f"{series[i][d]:.4f}")
                             for i in INDICES])

    SPARSE = 8                                   # fewer valid dates than this -> no smoothing
    ticks = sorted({d for sr in series.values() for d in sr if np.isfinite(sr[d])})

    def style_xaxis(ax):
        if len(ticks) <= 12:                     # few acquisitions: label every real date
            ax.set_xticks(ticks)
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
            for lab in ax.get_xticklabels():
                lab.set_rotation(30)
                lab.set_ha("right")
        else:
            ax.xaxis.set_major_locator(mdates.YearLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    # ---- Figure 2: all indices overlaid
    fig2, ax = plt.subplots(figsize=(14, 6))
    for name in INDICES:
        x, y = arrays(series[name])
        if len(y):
            yy = rolling_median(y) if len(y) >= SPARSE else y
            ax.plot(x, yy, "-o", color=COLORS[name], lw=2, ms=6, label=name)
    ax.axhline(0, color="grey", lw=0.8)
    style_xaxis(ax)
    ax.set_ylabel("index value")
    ax.grid(alpha=0.3)
    ax.legend(ncol=5)
    ax.set_title(f"All indices  |  {title_pt}")
    fig2.tight_layout()
    p2 = out_dir / f"trends_overlay_{tag}.png"
    fig2.savefig(p2, dpi=150)

    print("saved", p2)
    if a.csv:
        print("saved", out_dir / f"trend_{tag}.csv")
    if not a.no_show:
        plt.show()


if __name__ == "__main__":
    main()