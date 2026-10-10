#!/usr/bin/env python3
"""
Change maps (date2 - date1) of NDVI, MSAVI2, NDRE and NDMI within a radius
(default 10 km) of a point, PLUS a risk map that marks the areas under risk and
lists the reason and the suggested solution for each.

Change maps: each index keeps its own colormap in 4 equal intervals (symmetric +-L, 0 on the
middle edge): strong decrease | mild decrease | mild increase | strong increase.
NDRE (YlGnBu) is sequential: light = decrease, dark = increase.

Risk zones (smoothed over ~5x5 pixels so they are areas, not speckles; only land that was
vegetated on date1, NDVI >= 0.25):
    1 Vegetation loss        NDVI fell by >= L/2 (and MSAVI2 fell)
    2 Water stress           NDMI fell by >= L/2, or fell >= L/4 and is now below 0
    3 Early nutrient stress  NDRE fell by >= L/2 while NDVI is still steady (> -0.10)
    4 Multiple stresses      two or more of the above overlap (highest priority)
The thresholds are generic starting values - tune them for your crop and region.

Reads   output/<INDEX>/<year>/<INDEX>_<YYYYMMDD>_<TILE>.tif
Writes  output/change_maps/change_<d1>_<d2>_<lat>_<lon>.png  and  risk_<...>.txt
        output/change_maps/riskmap_<...>.html   <- INTERACTIVE web map: zoom/pan over a satellite or
                                                  street basemap, toggle layers, click for reason/solution
                                                  (needs internet in the browser for the basemap tiles)

Install:  pip install rasterio numpy matplotlib      (scipy optional: numbers the hotspots)
Run:      python change_map.py                         # first vs last available date, 10 km
          python change_map.py --date1 20161009 --date2 20261007
          python change_map.py --radius 5 --lang both  # reasons/solutions in English + Hindi
          python change_map.py --stage mature          # crop near harvest: skip vegetation/nutrient flags
          python change_map.py --smooth 11             # bigger = fewer, field-scale risk areas (default 5)
          python change_map.py --no-web                # skip the interactive HTML map
          python change_map.py --square --no-show
"""
import argparse
import base64
import html as _html
import io
import json
import re
import textwrap
import webbrowser
from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib import colors
from matplotlib.patches import Circle
from rasterio.enums import Resampling
from rasterio.errors import RasterioError
from rasterio.transform import from_bounds as tf_from_bounds
from rasterio.warp import calculate_default_transform, reproject
from rasterio.warp import transform as warp_transform
from rasterio.windows import Window, bounds as win_bounds, from_bounds

# index: (base colormap, symmetric change limit L)
PANELS = {
    "NDVI":   ("RdYlGn",  0.4),
    "MSAVI2": ("RdYlGn",  0.4),
    "NDRE":   ("YlGnBu",  0.3),
    "NDMI":   ("BrBG",    0.4),
}
LAYOUT = ["NDVI", "MSAVI2", "NDRE", "NDMI"]
N_BINS = 4
plt.rcParams["font.family"] = ["Nirmala UI", "Mangal", "Noto Sans Devanagari", "DejaVu Sans"]

DEFAULT_LAT = 22.87706                          # 22.87706°N
DEFAULT_LON = 78.89161                          # 78.89161°E

FILE_RE = re.compile(r"^(?P<idx>[A-Za-z0-9]+)_(?P<date>\d{8})_(?P<tile>T[0-9A-Z]+)\.tif$")


# --------------------------------------------------------------------------- #
# discovery
# --------------------------------------------------------------------------- #
def find_files(out_root: Path):
    """{(index, date): [paths]}"""
    d = {}
    for p in out_root.rglob("*.tif"):
        m = FILE_RE.match(p.name)
        if m and m["idx"] in PANELS:
            d.setdefault((m["idx"], m["date"]), []).append(p)
    return d


def covers(path, lon, lat):
    try:
        with rasterio.open(path) as s:
            x, y = warp_transform("EPSG:4326", s.crs, [lon], [lat])
            b = s.bounds
            return b.left <= x[0] <= b.right and b.bottom <= y[0] <= b.top
    except RasterioError:
        return False


# --------------------------------------------------------------------------- #
# reading a window around the point
# --------------------------------------------------------------------------- #
def _window(src, x, y, r):
    win = from_bounds(x - r, y - r, x + r, y + r, src.transform).round_offsets().round_lengths()
    return win.intersection(Window(0, 0, src.width, src.height))


def read_index_window(path, lon, lat, r, out_shape=None):
    with rasterio.open(path) as src:
        if not src.crs.is_projected:
            raise SystemExit("Raster CRS is not projected (metres); this script expects Sentinel-2 UTM data.")
        x, y = warp_transform("EPSG:4326", src.crs, [lon], [lat])
        x, y = x[0], y[0]
        win = _window(src, x, y, r)
        data = src.read(1, window=win, masked=True, out_shape=out_shape, resampling=Resampling.nearest)
        return np.ma.masked_invalid(data.astype("float64")), win_bounds(win, src.transform), (x, y)


def load(name, date, files, lon, lat, r, out_shape=None):
    """-> (masked array, bounds, (x, y)) or None if unavailable."""
    try:
        for p in files.get((name, date), []):
            if covers(p, lon, lat):
                return read_index_window(p, lon, lat, r, out_shape)
    except (RasterioError, OSError) as e:
        print(f"  !! could not read {name} {date}: {str(e).splitlines()[0]}")
    return None


# --------------------------------------------------------------------------- #
# drawing
# --------------------------------------------------------------------------- #
def make_cmap_norm(name, lim):
    base_name, default_lim = PANELS[name]
    lim = lim or default_lim
    bounds = np.linspace(-lim, lim, N_BINS + 1)
    cmap = colors.ListedColormap(plt.get_cmap(base_name)(((np.arange(N_BINS) + 0.5) / N_BINS)))
    cmap.set_bad("#2b2b2b")
    return cmap, colors.BoundaryNorm(bounds, cmap.N, clip=True), bounds, lim


def circle_mask(shape, extent, center, r):
    left, bottom, right, top = extent
    h, w = shape
    xs = left + (np.arange(w) + 0.5) * (right - left) / w
    ys = top - (np.arange(h) + 0.5) * (top - bottom) / h
    X, Y = np.meshgrid(xs, ys)
    return (X - center[0]) ** 2 + (Y - center[1]) ** 2 > r ** 2


def draw_panel(fig, ax, name, change, extent, center, r, lim, circle=True):
    cmap, norm, bounds, lim = make_cmap_norm(name, lim)
    ax.set_title(f"Δ{name}", fontsize=11, fontweight="bold")
    im = ax.imshow(change, cmap=cmap, norm=norm, interpolation="nearest",
                   extent=(extent[0], extent[2], extent[1], extent[3]))
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02, ticks=bounds)
    cb.ax.tick_params(labelsize=7)
    cb.set_label(f"Δ{name}  ({PANELS[name][0]}, {N_BINS} intervals)", fontsize=8)
    ax.set_autoscale_on(False)
    if circle:
        ax.add_patch(Circle(center, r, fill=False, ec="black", lw=1.2, ls="--"))
    ax.plot(*center, marker="*", ms=15, mfc="magenta", mec="white", mew=1.3, ls="none", zorder=10)
    ax.tick_params(labelsize=7)
    ax.ticklabel_format(useOffset=False, style="plain")
    v = change.compressed()
    if v.size == 0:
        return None
    return {"mean": float(v.mean()), "dec": 100 * np.mean(v < -lim / 2), "inc": 100 * np.mean(v >= lim / 2),
            "lim": lim, "n": int(v.size)}


RISK = {
    1: dict(color="#d32f2f", name=("Vegetation loss", "वनस्पति का नुकसान"),
            reason=("Green cover fell sharply (NDVI and MSAVI2 down). Possible causes: pest or disease damage, "
                    "water shortage or waterlogging, or the crop was harvested / cleared.",
                    "हरियाली में तेज़ गिरावट (NDVI व MSAVI2 घटे)। संभावित कारण: कीट/रोग, पानी की कमी या जलभराव, "
                    "या फसल कट चुकी है।"),
            solution=("Visit these patches now. Check pests, disease, water and drainage. If the crop was not harvested, "
                      "ask the KVK for treatment advice; re-sow / gap-fill only after the cause is confirmed.",
                      "इन हिस्सों में अभी जाकर कीट, रोग, पानी और जल निकासी जाँचें। फसल कटी नहीं है तो KVK से उपचार की सलाह लें; "
                      "कारण पक्का होने पर ही दोबारा बुवाई करें।")),
    2: dict(color="#f28e2b", name=("Water stress", "नमी का तनाव"),
            reason=("Moisture in the crop / soil dropped sharply (NDMI down or now below zero).",
                    "फसल/मिट्टी की नमी तेज़ी से घटी है (NDMI घटा या शून्य से नीचे)।"),
            solution=("Check soil moisture; irrigate if dry. Use mulching and better-timed (drip) irrigation to save water.",
                      "मिट्टी की नमी जाँचें; सूखी हो तो सिंचाई करें। मल्चिंग और ड्रिप/सही समय पर सिंचाई अपनाएँ।")),
    3: dict(color="#f0d000", name=("Early nutrient stress", "पोषक तत्व का शुरुआती तनाव"),
            reason=("Leaf chlorophyll (NDRE) is falling while greenness (NDVI) is still steady - an early sign of "
                    "nitrogen / nutrient shortage.",
                    "पत्तियों का क्लोरोफिल (NDRE) घट रहा है जबकि हरियाली (NDVI) स्थिर है — नाइट्रोजन/पोषक तत्व की कमी का शुरुआती संकेत।"),
            solution=("Look for pale or yellowing leaves, do a soil test, and follow a fertiliser recommendation from the KVK; "
                      "consider organic / green manure.",
                      "पत्तियों का पीलापन देखें, मिट्टी की जाँच कराएँ और KVK की खाद सलाह अपनाएँ; जैविक/हरी खाद पर विचार करें।")),
    4: dict(color="#7b1fa2", name=("Multiple stresses - highest priority", "एक से ज़्यादा तनाव — सबसे ज़रूरी"),
            reason=("Two or more warning signs (greenness, moisture, chlorophyll) overlap here.",
                    "यहाँ दो या अधिक चेतावनी संकेत (हरियाली, नमी, क्लोरोफिल) एक साथ हैं।"),
            solution=("Inspect these areas first. Check water, nutrients and pests together and get expert (KVK) advice "
                      "before applying inputs.",
                      "सबसे पहले इन्हीं हिस्सों का निरीक्षण करें। पानी, पोषक तत्व और कीट एक साथ जाँचें; इनपुट डालने से पहले KVK से सलाह लें।")),
}
NO_RISK_COLOR = "#d9ead3"
DISCLAIMER = ("Satellite-based alert, not a diagnosis. Harvest, ploughing or cloud also lower the indices - "
              "confirm in the field before acting.",
              "यह उपग्रह आधारित चेतावनी है, निदान नहीं। कटाई, जुताई या बादल से भी सूचकांक घटते हैं — कार्रवाई से पहले खेत में पुष्टि करें।")


def box_mean(a, k):
    """mean over a k x k window (k odd) via an integral image"""
    pad = k // 2
    ap = np.pad(a.astype(float), pad, mode="edge")
    c = np.pad(ap.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)


def compute_risk(a1, ch, inside, lims, stage="growing", k=5):
    """a1 / ch: {index: masked array} (date1 value, change). Returns (class map, smoothed flags)."""
    shape = inside.shape

    def arr(d, n):
        return None if n not in d else np.ma.filled(d[n].astype("float64"), np.nan)

    dN, dM, dR, dW = (arr(ch, n) for n in ("NDVI", "MSAVI2", "NDRE", "NDMI"))
    n1 = arr(a1, "NDVI")
    half = {n: (lims.get(n) or PANELS[n][1]) / 2 for n in PANELS}
    false = np.zeros(shape, bool)
    with np.errstate(invalid="ignore"):
        veg_land = (n1 >= 0.25) if n1 is not None else np.ones(shape, bool)
        f_veg = false.copy()
        f_nut = false.copy()
        f_wat = false.copy()
        if stage != "mature":
            if dN is not None:
                f_veg = (dN <= -half["NDVI"]) & veg_land
                if dM is not None:
                    f_veg &= dM <= -half["MSAVI2"] / 2
            if dR is not None:
                steady = (dN > -0.10) if dN is not None else np.ones(shape, bool)
                f_nut = (dR <= -half["NDRE"]) & steady & veg_land
        if dW is not None:
            n2 = (arr(a1, "NDMI") + dW) if "NDMI" in a1 else None
            f_wat = ((dW <= -half["NDMI"]) |
                     ((dW <= -half["NDMI"] / 2) & (n2 < 0) if n2 is not None else false)) & veg_land
    sm = lambda f: (box_mean(f.astype(float), k) >= 0.5) & inside
    f_veg, f_wat, f_nut = sm(f_veg), sm(f_wat), sm(f_nut)
    cls = np.zeros(shape, int)
    cls[f_nut], cls[f_wat], cls[f_veg] = 3, 2, 1
    cls[(f_veg.astype(int) + f_wat + f_nut) >= 2] = 4
    return cls, {"veg": f_veg, "water": f_wat, "nutr": f_nut}


def hotspots(cls, ext, max_per_class=2, min_frac=0.01):
    """centroids of the largest connected zones per class (needs scipy; otherwise [])"""
    try:
        from scipy import ndimage
    except ImportError:
        return []
    left, bottom, right, top = ext
    h, w = cls.shape
    out = []
    for k in (4, 3, 2, 1):
        lab, n = ndimage.label(cls == k)
        if n == 0:
            continue
        sizes = ndimage.sum(np.ones_like(lab), lab, index=range(1, n + 1))
        for i in np.argsort(sizes)[::-1][:max_per_class]:
            if sizes[i] < min_frac * cls.size * 0.78:
                continue
            cy, cx = ndimage.center_of_mass(lab == i + 1)
            out.append((k, left + (cx + 0.5) * (right - left) / w, top - (cy + 0.5) * (top - bottom) / h))
    return out


def draw_risk_map(ax, cls, inside, ext, center, r, circle=True):
    from matplotlib.colors import BoundaryNorm, ListedColormap
    cols = [NO_RISK_COLOR] + [RISK[k]["color"] for k in (1, 2, 3, 4)]
    cmap = ListedColormap(cols)
    cmap.set_bad("#2b2b2b")
    data = np.ma.masked_where(~inside, cls)
    e = (ext[0], ext[2], ext[1], ext[3])
    ax.imshow(data, cmap=cmap, norm=BoundaryNorm(np.arange(-0.5, 5.5, 1), 5), interpolation="nearest", extent=e)
    ax.set_autoscale_on(False)
    for k in (1, 2, 3, 4):
        m = (cls == k)
        if m.any() and not m.all():
            ax.contour(m.astype(float), levels=[0.5], colors=[RISK[k]["color"]], linewidths=1.8,
                       extent=e, origin="upper")
    for k, x, y in hotspots(np.where(inside, cls, 0), ext):
        ax.text(x, y, str(k), ha="center", va="center", fontsize=9, fontweight="bold", color="black",
                bbox=dict(boxstyle="circle,pad=0.25", fc="white", ec=RISK[k]["color"], lw=2), zorder=11)
    if circle:
        ax.add_patch(Circle(center, r, fill=False, ec="black", lw=1.2, ls="--"))
    ax.plot(*center, marker="*", ms=15, mfc="magenta", mec="white", mew=1.3, ls="none", zorder=12)
    ax.set_title("RISK MAP  (numbers = zone type)", fontsize=11, fontweight="bold")
    ax.tick_params(labelsize=7)
    ax.ticklabel_format(useOffset=False, style="plain")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(fc=NO_RISK_COLOR, ec="grey", label="no risk detected")] +
              [Patch(fc=RISK[k]["color"], label=f"{k} {RISK[k]['name'][0]}") for k in (1, 2, 3, 4)],
              loc="upper center", bbox_to_anchor=(0.5, -0.06), ncol=2, fontsize=7, frameon=False)


def risk_report(cls, inside, ext, langs, stage, missing):
    """-> (list of (class, header, why, fix, ha, pct)), plain-text lines"""
    h, w = cls.shape
    px_area_ha = (ext[2] - ext[0]) / w * (ext[3] - ext[1]) / h / 10000.0
    total = int(inside.sum())
    items = []
    for k in (4, 1, 2, 3):
        n = int((cls == k).sum())
        if n:
            items.append((k, n * px_area_ha, 100.0 * n / max(total, 1)))
    notes = []
    if stage == "mature":
        notes.append("Stage 'mature': vegetation-loss and nutrient flags skipped (decline is expected near harvest).")
    if missing:
        notes.append("Not available, so those checks were skipped: " + ", ".join(missing))
    return items, notes


def get_crs(files, name, date, lon, lat):
    for p in files.get((name, date), []):
        if covers(p, lon, lat):
            with rasterio.open(p) as s:
                return s.crs
    return None


def _png_b64(rgba):
    buf = io.BytesIO()
    mpimg.imsave(buf, rgba, format="png")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def build_panel_html(items, langs, d1, d2, lat, lon, notes, opacity):
    e = _html.escape
    out = [f"<b>Risk report</b><br>{d1[:4]}-{d1[4:6]}-{d1[6:]} → {d2[:4]}-{d2[4:6]}-{d2[6:]} · {lat:.5f}°N, {lon:.5f}°E",
           f'<div style="margin:6px 0">Layer opacity <input id="op" type="range" min="0" max="1" step="0.05" value="{opacity}"></div>',
           "<i>Click anywhere on the map to see the zone type, reason and solution at that spot.</i><hr style='margin:6px 0'>"]
    if not items:
        out.append("No risk zones detected with the current thresholds.")
    for k, ha, pct in items:
        R = RISK[k]
        for li in langs:
            out.append(f'<div style="margin-bottom:6px"><span class="sw" style="background:{R["color"]}"></span>'
                       f'<b>{k}. {e(R["name"][li])}</b> — {ha:,.0f} ha ({pct:.1f}%)<br>'
                       f'<b>Reason:</b> {e(R["reason"][li])}<br><b>Solution:</b> {e(R["solution"][li])}</div>')
    for n in notes + [DISCLAIMER[langs[0]]]:
        out.append(f'<div style="color:#555;font-size:12px;margin-top:4px"><i>{e(n)}</i></div>')
    return "".join(out)


WEB_TEMPLATE = """<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Risk map</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.css">
<style>
 html,body,#map{height:100%;margin:0}
 .panel{background:#fff;padding:8px 10px;border-radius:6px;box-shadow:0 1px 6px rgba(0,0,0,.4);
        font:13px/1.35 system-ui,Segoe UI,Arial,sans-serif;width:340px;max-height:72vh;overflow:auto}
 .sw{display:inline-block;width:12px;height:12px;margin-right:6px;border:1px solid #555;vertical-align:-1px}
 .star{font-size:26px;color:#e91e63;text-shadow:0 0 3px #fff,0 0 3px #fff;line-height:26px}
</style></head><body><div id="map"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js"></script>
<script>
const D = __DATA__;
const map = L.map('map');
const sat = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
  {maxZoom: 19, attribution: 'Imagery © Esri'});
const osm = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  {maxZoom: 19, attribution: '© OpenStreetMap contributors'});
sat.addTo(map);
const b = L.latLngBounds(D.bounds[0], D.bounds[1]);
const overlays = {}, imgs = [];
D.layers.forEach(l => {
  const o = L.imageOverlay(l.png, b, {opacity: D.opacity, interactive: false});
  imgs.push(o); overlays[l.name] = o; if (l.on) o.addTo(map);
});
const pt = L.marker([D.lat, D.lon], {icon: L.divIcon({className: '', html: '<div class="star">★</div>', iconSize: [26, 26], iconAnchor: [13, 13]})})
  .bindPopup('<b>Point of interest</b><br>' + D.lat.toFixed(5) + '°N, ' + D.lon.toFixed(5) + '°E').addTo(map);
L.control.layers({'Satellite (Esri)': sat, 'Street map (OSM)': osm}, overlays, {collapsed: false, position: 'topleft'}).addTo(map);
L.control.scale({imperial: false}).addTo(map);
map.fitBounds(b);

const info = L.control({position: 'topright'});
info.onAdd = () => { const d = L.DomUtil.create('div', 'panel'); d.innerHTML = D.html;
  L.DomEvent.disableClickPropagation(d); L.DomEvent.disableScrollPropagation(d); return d; };
info.addTo(map);
const op = document.getElementById('op');
if (op) op.addEventListener('input', () => imgs.forEach(o => o.setOpacity(parseFloat(op.value))));

const bytes = Uint8Array.from(atob(D.lookup.b64), c => c.charCodeAt(0));
const [mx0, my0, mx1, my1] = D.lookup.merc;
function classAt(lat, lng) {
  const x = lng * 20037508.342789244 / 180;
  const y = Math.log(Math.tan((90 + lat) * Math.PI / 360)) * 6378137;
  const fx = (x - mx0) / (mx1 - mx0), fy = (my1 - y) / (my1 - my0);
  if (fx < 0 || fx >= 1 || fy < 0 || fy >= 1) return 255;
  return bytes[Math.floor(fy * D.lookup.h) * D.lookup.w + Math.floor(fx * D.lookup.w)];
}
map.on('click', e => {
  const k = classAt(e.latlng.lat, e.latlng.lng);
  let h = '<b>' + e.latlng.lat.toFixed(5) + '°N, ' + e.latlng.lng.toFixed(5) + '°E</b><br>';
  if (k === 255) h += 'Outside the analysed area.';
  else if (k === 0) h += 'No risk detected here.';
  else { const R = D.risk[k];
    D.langs.forEach(li => { h += '<div style="margin-top:4px"><span class="sw" style="background:' + R.color + '"></span><b>' + k + '. ' + R.name[li] +
      '</b><br><b>Reason:</b> ' + R.reason[li] + '<br><b>Solution:</b> ' + R.solution[li] + '</div>'; }); }
  L.popup({maxWidth: 340}).setLatLng(e.latlng).setContent(h).openOn(map);
});
</script></body></html>"""


def write_webmap(path, cls, inside, ch, ext, crs, lon, lat, r, d1, d2, items, notes, langs, lim, opacity=0.8):
    h, w = cls.shape
    left, bottom, right, top = ext
    src_t = tf_from_bounds(left, bottom, right, top, w, h)
    dst_t, dw, dh = calculate_default_transform(crs, "EPSG:3857", w, h, left, bottom, right, top)

    def warp(arr, dtype, nodata):
        dst = np.full((dh, dw), nodata, dtype)
        reproject(source=arr.astype(dtype), destination=dst, src_transform=src_t, src_crs=crs,
                  dst_transform=dst_t, dst_crs="EPSG:3857", src_nodata=nodata, dst_nodata=nodata,
                  resampling=Resampling.nearest)
        return dst

    # risk classes -> transparent PNG (class 0 / outside are transparent)
    cls_w = warp(np.where(inside, cls, 255), np.uint8, 255)
    lut = np.zeros((256, 4), np.uint8)
    for k in (1, 2, 3, 4):
        lut[k] = [int(RISK[k]["color"][i:i + 2], 16) for i in (1, 3, 5)] + [255]
    layers = [{"name": "Risk zones", "png": _png_b64(lut[cls_w]), "on": True}]

    # change layers (same colour classes as the figure)
    for name, arr in ch.items():
        cmap, norm, _, _ = make_cmap_norm(name, lim)
        a = warp(np.ma.filled(arr.astype("float64"), np.nan), np.float32, np.nan)
        bad = ~np.isfinite(a)
        rgba = (cmap(norm(np.ma.masked_invalid(a))) * 255).astype(np.uint8)
        rgba[bad, 3] = 0
        layers.append({"name": f"Δ{name}  (change {d1}→{d2})", "png": _png_b64(rgba), "on": False})

    # coarse class grid for click look-up
    L = 600
    ri = np.linspace(0, dh - 1, min(L, dh)).astype(int)
    ci = np.linspace(0, dw - 1, min(L, dw)).astype(int)
    lk = cls_w[np.ix_(ri, ci)]
    mx0, my1 = dst_t.c, dst_t.f
    mx1, my0 = mx0 + dw * dst_t.a, my1 + dh * dst_t.e
    (lo0, lo1), (la0, la1) = [warp_transform("EPSG:3857", "EPSG:4326", [mx0, mx1], [my0, my1])[i] for i in (0, 1)]
    data = {
        "lat": lat, "lon": lon, "radius": r, "radius_km": f"{r / 1000:g}", "opacity": opacity,
        "bounds": [[la0, lo0], [la1, lo1]], "layers": layers, "langs": langs,
        "lookup": {"w": int(lk.shape[1]), "h": int(lk.shape[0]), "merc": [mx0, my0, mx1, my1],
                   "b64": base64.b64encode(lk.tobytes()).decode()},
        "risk": {str(k): {"color": v["color"], "name": list(v["name"]), "reason": list(v["reason"]),
                          "solution": list(v["solution"])} for k, v in RISK.items()},
        "html": build_panel_html(items, langs, d1, d2, lat, lon, notes, opacity),
    }
    Path(path).write_text(WEB_TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False)), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, default=DEFAULT_LAT)
    ap.add_argument("--lon", type=float, default=DEFAULT_LON)
    ap.add_argument("--radius", type=float, default=0.2, help="km around the point (default 0.2 = 200 m)")
    ap.add_argument("--date1", help="earlier date YYYYMMDD (default: first available)")
    ap.add_argument("--date2", help="later date YYYYMMDD (default: last available)")
    ap.add_argument("--limit", type=float, help="override the +-change limit for every index")
    ap.add_argument("--lang", choices=["en", "hi", "both"], default="en", help="language of reason/solution text")
    ap.add_argument("--stage", choices=["growing", "mature"], default="growing")
    ap.add_argument("--smooth", type=int, default=5,
                    help="smoothing window in pixels for the risk areas (odd; bigger = fewer, larger areas)")
    ap.add_argument("--no-web", action="store_true", help="do not write the interactive HTML map")
    ap.add_argument("--square", action="store_true", help="show the whole square window, no circle mask")
    ap.add_argument("--output", default="output")
    ap.add_argument("--no-show", action="store_true")
    a = ap.parse_args()

    out_root = Path(a.output)
    files = find_files(out_root)
    dates = sorted({d for (_, d) in files})
    if len(dates) < 2:
        raise SystemExit("Need at least two dates in output/ to compute change.")
    d1, d2 = a.date1 or dates[0], a.date2 or dates[-1]
    if d1 == d2:
        raise SystemExit("date1 and date2 must be different.")
    r = a.radius * 1000.0
    langs = {"en": [0], "hi": [1], "both": [0, 1]}[a.lang]
    print(f"change {d1} -> {d2} within {a.radius:g} km of {a.lat:.5f}, {a.lon:.5f}")

    # common grid: every index is read onto the grid of the first one available
    ref = next((t for t in (load(n, d1, files, a.lon, a.lat, r) for n in LAYOUT) if t), None)
    if ref is None:
        raise SystemExit(f"No index rasters found for {d1} covering the point.")
    shape, ext, ctr = ref[0].shape, ref[1], ref[2]
    inside = np.ones(shape, bool) if a.square else ~circle_mask(shape, ext, ctr, r)

    v1, ch, missing = {}, {}, []
    for name in LAYOUT:
        p1 = load(name, d1, files, a.lon, a.lat, r, out_shape=shape)
        p2 = load(name, d2, files, a.lon, a.lat, r, out_shape=shape) if p1 else None
        if not p1 or not p2:
            missing.append(f"{name} ({d1 if not p1 else d2})")
            continue
        v1[name] = p1[0]
        ch[name] = np.ma.array(np.ma.masked_invalid(p2[0] - p1[0]),
                               mask=np.ma.getmaskarray(np.ma.masked_invalid(p2[0] - p1[0])) | ~inside)

    lims = {n: a.limit for n in PANELS}
    cls, flags = compute_risk(v1, ch, inside, lims, a.stage, k=a.smooth | 1)
    flag_for = {"NDVI": "veg", "MSAVI2": "veg", "NDRE": "nutr", "NDMI": "water"}
    e = (ext[0], ext[2], ext[1], ext[3])

    fig, axes = plt.subplots(2, 3, figsize=(23, 13))
    axes = axes.ravel()
    for ax, name in zip(axes, LAYOUT):
        if name not in ch:
            ax.text(0.5, 0.5, f"Δ{name}\nnot available", ha="center", va="center", transform=ax.transAxes)
            ax.set_axis_off()
            continue
        st = draw_panel(fig, ax, name, ch[name], ext, ctr, r, a.limit, circle=not a.square)
        m = flags[flag_for[name]]
        if m.any() and not m.all():                       # outline the risk areas on the change map
            ax.contour(m.astype(float), levels=[0.5], colors="black", linewidths=1.3, extent=e, origin="upper")
        if st:
            ax.set_xlabel(f"mean Δ {st['mean']:+.3f}   |   strong ↓ {st['dec']:.1f}%   strong ↑ {st['inc']:.1f}%   "
                          f"(black outline = risk area)", fontsize=8)
            print(f"  {name:7s} mean {st['mean']:+.3f}  strong-decrease {st['dec']:.1f}%  strong-increase {st['inc']:.1f}%")

    draw_risk_map(axes[4], cls, inside, ext, ctr, r, circle=not a.square)

    # reason / solution panel
    tx = axes[5]
    tx.set_axis_off()
    tx.set_xlim(0, 1)
    tx.set_ylim(0, 1)
    items, notes = risk_report(cls, inside, ext, langs, a.stage, missing)
    lines_txt = [f"RISK REPORT  {d1} → {d2}  |  {a.radius:g} km around {a.lat:.5f}°N, {a.lon:.5f}°E", ""]
    y = 0.98
    tx.text(0.0, y, lines_txt[0], fontsize=10, fontweight="bold", va="top")
    y -= 0.05
    lh, wrap = 0.0275, 78
    if not items:
        msg = "No risk zones detected inside the area with the current thresholds."
        tx.text(0.0, y, msg, fontsize=9, va="top")
        lines_txt.append(msg)
    for k, ha, pct in items:
        R = RISK[k]
        for li in langs:
            head = f"{k}. {R['name'][li]}  —  {ha:,.0f} ha  ({pct:.1f}% of the area)"
            tx.text(0.0, y, "■ ", fontsize=11, color=R["color"], va="top")
            tx.text(0.04, y, head, fontsize=9.5, fontweight="bold", va="top")
            y -= lh * 1.25
            lines_txt.append(head)
            for tag, text in (("Reason:", R["reason"][li]), ("Solution:", R["solution"][li])):
                body = textwrap.fill(f"{tag} {text}", wrap)
                tx.text(0.04, y, body, fontsize=8.6, va="top")
                y -= lh * (body.count("\n") + 1) + 0.006
                lines_txt.append(body)
        y -= 0.015
    for n in notes + [DISCLAIMER[langs[0]]]:
        body = textwrap.fill(n, wrap + 8)
        if y > 0.05:
            tx.text(0.0, y, body, fontsize=8, style="italic", color="#444", va="top")
            y -= lh * (body.count("\n") + 1) + 0.006
        lines_txt.append(body)

    fig.suptitle(f"Sentinel-2 change & risk map  |  {d1} → {d2}  |  {a.radius:g} km around the point (★)", fontsize=15)
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    out = out_root / "change_maps"
    out.mkdir(parents=True, exist_ok=True)
    tag = f"{d1}_{d2}_{a.lat:.4f}_{a.lon:.4f}"
    path = out / f"change_{tag}.png"
    fig.savefig(path, dpi=150)
    (out / f"risk_{tag}.txt").write_text("\n".join(lines_txt), encoding="utf-8")
    print("\n".join(lines_txt))
    print("saved", path)
    if not a.no_web:
        crs = next((c for c in (get_crs(files, n, d1, a.lon, a.lat) for n in LAYOUT) if c), None)
        if crs is not None:
            wpath = out / f"riskmap_{tag}.html"
            write_webmap(wpath, cls, inside, ch, ext, crs, a.lon, a.lat, r, d1, d2, items, notes, langs, a.limit)
            print("saved interactive map", wpath)
            if not a.no_show:
                webbrowser.open(wpath.resolve().as_uri())
    if not a.no_show:
        plt.show()


if __name__ == "__main__":
    main()