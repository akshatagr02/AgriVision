#!/usr/bin/env python3
"""
Sentinel-2 L2A  ->  NDVI, MSAVI2, NDRE, NDMI   (all output at 10 m)

* Recursively scans the input folder (works with unzipped .SAFE folders or flat folders of .jp2/.tif)
* Finds B04, B08 (10 m)  and  B05, B8A, B11 (20 m)  (+ SCL optional) automatically
* Resamples the 20 m bands to 10 m using B08 as the reference grid (bilinear)
* Applies reflectance scaling (/10000) and the +1000 BOA offset for baseline >= 04.00 (scenes after 25-Jan-2022)
* Writes GeoTIFFs:  output/<INDEX>/<YEAR>/<INDEX>_<YYYYMMDD>_<TILE>.tif

Install:  pip install rasterio numpy
Run:      python sentinel2_indices.py --input input --output output
"""
import argparse
import logging
import re
from collections import defaultdict
from contextlib import ExitStack
from datetime import date
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window

NODATA = -9999.0
EXTS = {".jp2", ".tif", ".tiff"}
WINDOW = 1024
BASELINE_CHANGE = date(2022, 1, 25)       # processing baseline 04.00 -> BOA offset of -1000
SCL_BAD = [0, 1, 3, 8, 9, 10]             # nodata, saturated, cloud shadow, cloud med/high, cirrus

BAND_RE = re.compile(r"(?:^|_)(?P<band>B0?[1-9]|B1[0-2]|B8A|SCL)(?:_(?P<res>\d{2}m))?\.[A-Za-z0-9]+$", re.I)
DATE_RE = re.compile(r"(20\d{2})([01]\d)([0-3]\d)")
TILE_RE = re.compile(r"(?<![A-Z0-9])T\d{2}[A-Z]{3}(?![A-Z])")
BASELINE_RE = re.compile(r"_N(\d{2})(\d{2})_")
RES_DIR_RE = re.compile(r"R(\d{2}m)", re.I)

WANTED = {"B04", "B08", "B05", "B8A", "B11", "SCL"}
PREFERRED_RES = {"B04": "10m", "B08": "10m", "B05": "20m", "B8A": "20m", "B11": "20m", "SCL": "20m"}


# ----------------------------------------------------------------------------- index formulas
def nd(a, b):
    s = a + b
    out = np.zeros_like(s)
    np.divide(a - b, s, out=out, where=s != 0)
    return out


def ndvi(d):   return nd(d["B08"], d["B04"])
def ndre(d):   return nd(d["B8A"], d["B05"])
def ndmi(d):   return nd(d["B8A"], d["B11"])


def msavi2(d):
    nir, red = d["B08"], d["B04"]
    inner = np.maximum((2 * nir + 1) ** 2 - 8 * (nir - red), 0)
    return (2 * nir + 1 - np.sqrt(inner)) / 2


INDICES = {
    "NDVI":   (("B08", "B04"), ndvi),
    "MSAVI2": (("B08", "B04"), msavi2),
    "NDRE":   (("B8A", "B05"), ndre),
    "NDMI":   (("B8A", "B11"), ndmi),
}


# ----------------------------------------------------------------------------- file discovery
def find_scenes(root: Path):
    """Return {(date_str, tile): {band: [(res, path), ...]}}"""
    scenes = defaultdict(lambda: defaultdict(list))
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in EXTS:
            continue
        m = BAND_RE.search(p.name)
        if not m:
            continue
        band = m.group("band").upper()
        if band != "B8A" and band != "SCL":
            band = "B" + band[1:].zfill(2)
        if band not in WANTED:
            continue
        full = str(p)
        dm = DATE_RE.search(p.name) or DATE_RE.search(full)
        if not dm:
            logging.warning("No date found for %s - skipped", p)
            continue
        tm = TILE_RE.search(p.name) or TILE_RE.search(full)
        tile = tm.group(0) if tm else "TUNK"
        res = (m.group("res") or "").lower()
        if not res:
            rm = RES_DIR_RE.search(full)
            res = rm.group(1).lower() if rm else ""
        scenes[("".join(dm.groups()), tile)][band].append((res, p))
    return scenes


def pick(cands, band):
    pref = PREFERRED_RES[band]
    return sorted(cands, key=lambda rp: (rp[0] != pref, str(rp[1])))[0][1]


def boa_offset(d: date, paths):
    """-1000 for processing baseline >= 04.00, else 0."""
    for p in paths:
        m = BASELINE_RE.search(str(p))
        if m:
            return -1000 if int(m.group(1)) >= 4 else 0
    return -1000 if d >= BASELINE_CHANGE else 0


# ----------------------------------------------------------------------------- processing
def process_scene(key, bands, out_root: Path, wanted, mask_clouds, overwrite):
    ds, tile = key
    d = date(int(ds[:4]), int(ds[4:6]), int(ds[6:]))
    year = ds[:4]

    paths = {b: pick(c, b) for b, c in bands.items()}
    todo = []
    for name in wanted:
        need, _ = INDICES[name]
        if not all(b in paths for b in need):
            logging.warning("%s %s: missing %s for %s - skipped", ds, tile, [b for b in need if b not in paths], name)
            continue
        out = out_root / name / year / f"{name}_{ds}_{tile}.tif"
        if out.exists() and not overwrite:
            continue
        todo.append((name, out))
    if not todo:
        return
    if mask_clouds and "SCL" not in paths:
        logging.warning("%s %s: SCL not found, cloud masking disabled", ds, tile)
        mask_clouds = False

    used = sorted({b for n, _ in todo for b in INDICES[n][0]} | ({"SCL"} if mask_clouds else set()))
    ref_path = paths.get("B08") or paths[used[0]]
    offset = boa_offset(d, paths.values())
    logging.info("%s %s | bands %s | BOA offset %d", ds, tile, used, offset)

    with ExitStack() as stack:
        ref = stack.enter_context(rasterio.open(ref_path))        # B08 = 10 m reference grid
        src = {}
        for b in used:
            r = stack.enter_context(rasterio.open(paths[b]))
            if (r.width, r.height) != (ref.width, ref.height) or r.transform != ref.transform:
                method = Resampling.nearest if b == "SCL" else Resampling.bilinear
                r = stack.enter_context(WarpedVRT(r, crs=ref.crs, transform=ref.transform,
                                                  width=ref.width, height=ref.height,
                                                  resampling=method))
            src[b] = r

        profile = dict(driver="GTiff", dtype="float32", count=1, nodata=NODATA, width=ref.width,
                       height=ref.height, crs=ref.crs, transform=ref.transform, compress="deflate",
                       predictor=3, tiled=True, blockxsize=512, blockysize=512, BIGTIFF="IF_SAFER")
        outs = {}
        for name, out in todo:
            out.parent.mkdir(parents=True, exist_ok=True)
            outs[name] = stack.enter_context(rasterio.open(out, "w", **profile))

        for row in range(0, ref.height, WINDOW):
            for col in range(0, ref.width, WINDOW):
                win = Window(col, row, min(WINDOW, ref.width - col), min(WINDOW, ref.height - row))
                raw = {b: src[b].read(1, window=win) for b in used}
                refl = {b: np.maximum(raw[b].astype(np.float32) + offset, 0) / 10000.0
                        for b in used if b != "SCL"}
                bad = np.zeros((win.height, win.width), bool)
                if mask_clouds:
                    bad = np.isin(raw["SCL"], SCL_BAD)
                for name, _ in todo:
                    need, func = INDICES[name]
                    valid = ~bad
                    for b in need:
                        valid &= raw[b] > 0
                    res = func(refl).astype(np.float32)
                    res[~valid] = NODATA
                    outs[name].write(res, 1, window=win)


def main():
    ap = argparse.ArgumentParser(description="Sentinel-2 L2A vegetation/moisture indices at 10 m")
    ap.add_argument("--input", default="input", help="root folder with Sentinel-2 files")
    ap.add_argument("--output", default="output", help="output folder")
    ap.add_argument("--indices", nargs="+", default=list(INDICES), choices=list(INDICES))
    ap.add_argument("--start-year", type=int, default=2016)
    ap.add_argument("--end-year", type=int, default=2026)
    ap.add_argument("--mask-clouds", action="store_true", help="mask cloud/shadow/cirrus using SCL")
    ap.add_argument("--overwrite", action="store_true")
    a = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    root = Path(a.input)
    if not root.exists():
        raise SystemExit(f"Input folder not found: {root.resolve()}")

    scenes = find_scenes(root)
    logging.info("Found %d scenes", len(scenes))
    for key in sorted(scenes):
        if not (a.start_year <= int(key[0][:4]) <= a.end_year):
            continue
        try:
            process_scene(key, scenes[key], Path(a.output), a.indices, a.mask_clouds, a.overwrite)
        except Exception as e:                      # keep going if one scene is corrupt
            logging.error("Failed %s %s: %s", key[0], key[1], e)
    logging.info("Done")


if __name__ == "__main__":
    main()