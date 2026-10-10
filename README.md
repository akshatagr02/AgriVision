# Sentinel-2 Crop Health Analysis

A Python workflow for processing Sentinel-2 Level-2A imagery into vegetation and moisture indices, comparing two dates, mapping likely crop-stress zones, and plotting index trends at a point.

This README documents the supported top-level scripts only:

- `main.py` - build index GeoTIFFs from Sentinel-2 imagery
- `cmap.py` - create date-to-date change maps and a risk report
- `Plots.py` - create a time-series plot at a latitude/longitude

The `dump/` folder is not part of the documented workflow.

## What The Workflow Produces

The pipeline calculates these indices at 10 m resolution:

| Index | Formula | Main use |
| --- | --- | --- |
| NDVI | `(B08 - B04) / (B08 + B04)` | Vegetation greenness |
| MSAVI2 | Soil-adjusted vegetation index from B08 and B04 | Vegetation cover with reduced soil influence |
| NDRE | `(B8A - B05) / (B8A + B05)` | Chlorophyll and possible nutrient stress |
| NDMI | `(B8A - B11) / (B8A + B11)` | Canopy moisture |
| NDWI | `(B03 - B08) / (B03 + B08)` | Surface water or wetness; calculated on demand by `Plots.py` |

The normal workflow is:

```text
Sentinel-2 .SAFE scenes
        |
        v
main.py  ->  output/NDVI, MSAVI2, NDRE, NDMI GeoTIFFs
        |
        +--> cmap.py   -> change figure, risk text, interactive HTML map
        |
        +--> Plots.py  -> point trend PNG and optional CSV
```

## Requirements

- Python 3.9 or newer
- Sentinel-2 Level-2A imagery
- Enough free disk space for GeoTIFF outputs and temporary processing
- Internet access only when opening the interactive risk map basemap

Install the required packages from the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install numpy rasterio matplotlib
```

`scipy` is optional. `cmap.py` uses it to label the largest connected hotspot areas. The change and risk maps still work without it.

If PowerShell does not allow script activation, use the environment's Python directly:

```powershell
.venv\Scripts\python.exe -m pip install numpy rasterio matplotlib
```

## Project Layout

```text
.
├── main.py
├── cmap.py
├── Plots.py
├── input/
│   └── *.SAFE/                  Sentinel-2 L2A scenes
└── output/
    ├── NDVI/<year>/*.tif
    ├── MSAVI2/<year>/*.tif
    ├── NDRE/<year>/*.tif
    ├── NDMI/<year>/*.tif
    ├── NDWI/<year>/*.tif       created on demand by Plots.py
    ├── trends/
    └── change_maps/
```

Run commands from the project directory so the default `input` and `output` paths resolve correctly.

## Input Data

Place unzipped Sentinel-2 Level-2A `.SAFE` directories under `input/`. The input scanner is recursive, so nested `.SAFE` content is supported.

The processor discovers these bands automatically:

- `B04` and `B08` at 10 m
- `B05`, `B8A`, and `B11` at 20 m
- `SCL` at 20 m when cloud masking is requested

The files must retain normal Sentinel-2 names containing the band name, acquisition date, and tile identifier, for example:

```text
input/S2B_MSIL2A_20201023T051859_N0500_R062_T44QKL_20230503T080532.SAFE/
```

The scripts use the date in `YYYYMMDD` form and the tile identifier such as `T44QKL` when naming outputs. Scenes with missing required bands are skipped for the affected index.

## Workflow 1: Build Index Rasters

`main.py` scans all input scenes and writes one GeoTIFF per index, scene, and tile.

### Basic run

```powershell
python main.py
```

Equivalent explicit command:

```powershell
python main.py --input input --output output
```

By default it processes scenes from 2016 through 2026 and calculates all four supported indices.

### Common options

Process selected indices only:

```powershell
python main.py --indices NDVI NDMI
```

Limit the year range:

```powershell
python main.py --start-year 2018 --end-year 2024
```

Enable cloud, cloud-shadow, cirrus, saturated-pixel, and nodata masking using the Scene Classification Layer:

```powershell
python main.py --mask-clouds
```

Rebuild files that already exist:

```powershell
python main.py --overwrite
```

Combine options:

```powershell
python main.py --input input --output output --indices NDVI MSAVI2 NDRE NDMI --start-year 2016 --end-year 2026 --mask-clouds --overwrite
```

### Processing details

- The B08 grid is used as the 10 m reference grid.
- 20 m bands are resampled to the reference grid with bilinear resampling.
- SCL is resampled with nearest-neighbour resampling.
- Digital values are converted to reflectance by applying the Sentinel-2 baseline offset when required and dividing by 10,000.
- Processing is performed in 1024-pixel windows to limit memory use.
- Invalid or masked pixels are written as `-9999.0`.
- A corrupt scene is logged and skipped so the remaining scenes can continue.

### Generated files

```text
output/<INDEX>/<YEAR>/<INDEX>_<YYYYMMDD>_<TILE>.tif
```

Examples:

```text
output/NDVI/2020/NDVI_20201023_T44QKL.tif
output/NDMI/2020/NDMI_20201023_T44QKL.tif
```

Run this workflow before the change-map or trend workflows unless the required GeoTIFFs already exist.

## Workflow 2: Create Change And Risk Maps

`cmap.py` compares two dates around a geographic point. It creates four index change panels, a risk classification, a text report, and optionally an interactive HTML map.

The change is calculated as:

```text
change = index(date2) - index(date1)
```

The default date pair is the first and last available date found under `output/`. The default point is approximately `22.87706, 78.89161`. The actual default radius in the code is `0.2` km, or 200 m.

### Basic run

```powershell
python cmap.py
```

Specify dates and location:

```powershell
python cmap.py --date1 20161009 --date2 20261007 --lat 22.87706 --lon 78.89161
```

Use a larger analysis radius:

```powershell
python cmap.py --radius 5
```

The radius is in kilometres.

### Language, crop stage, and map options

Write risk reasons and solutions in English and Hindi:

```powershell
python cmap.py --lang both
```

Use Hindi only:

```powershell
python cmap.py --lang hi
```

Treat the crop as near maturity. This skips vegetation-loss and nutrient-stress flags because declining greenness can be expected near harvest:

```powershell
python cmap.py --stage mature
```

Override the symmetric change limit used by all change panels:

```powershell
python cmap.py --limit 0.3
```

Use a larger odd smoothing window to produce fewer, larger risk areas:

```powershell
python cmap.py --smooth 11
```

Show the full square window instead of masking the analysis to a circle:

```powershell
python cmap.py --square
```

Do not write the interactive HTML map:

```powershell
python cmap.py --no-web
```

Save files without opening a Matplotlib window or browser:

```powershell
python cmap.py --no-show
```

A typical non-interactive run is:

```powershell
python cmap.py --date1 20161009 --date2 20261007 --lat 22.87706 --lon 78.89161 --radius 5 --lang both --smooth 11 --no-show
```

### Risk classes

The risk map considers land that was vegetated on the first date, generally requiring NDVI of at least `0.25`.

| Class | Meaning | Main rule |
| --- | --- | --- |
| 1 | Vegetation loss | NDVI and MSAVI2 both fall substantially |
| 2 | Water stress | NDMI falls substantially or becomes negative after a moderate fall |
| 3 | Early nutrient stress | NDRE falls while NDVI remains relatively steady |
| 4 | Multiple stresses | At least two warning classes overlap; highest priority |

Risk thresholds are generic starting values. They should be calibrated for the crop, season, sensor conditions, and local agronomic practice.

### Generated files

```text
output/change_maps/change_<date1>_<date2>_<lat>_<lon>.png
output/change_maps/risk_<date1>_<date2>_<lat>_<lon>.txt
output/change_maps/riskmap_<date1>_<date2>_<lat>_<lon>.html
```

The HTML map includes satellite and street basemap toggles, change overlays, risk-zone information, point inspection, and reason/solution text. The basemap tiles require internet access in the browser; the generated overlays and report are created locally.

## Workflow 3: Plot Point Trends

`Plots.py` samples all available index rasters at one coordinate and plots NDVI, MSAVI2, NDRE, NDMI, and NDWI over time.

### Basic run

```powershell
python Plots.py --no-show
```

Without `--no-show`, Matplotlib opens the graph after saving it.

Use a specific point:

```powershell
python Plots.py --lat 22.92262 --lon 78.904003 --no-show
```

Average a neighbourhood around the point instead of one pixel. `--buffer 1` samples a 3x3 pixel window; `--buffer 2` samples a 5x5 window.

```powershell
python Plots.py --lat 22.92262 --lon 78.904003 --buffer 1 --no-show
```

Also write the sampled values to CSV:

```powershell
python Plots.py --lat 22.92262 --lon 78.904003 --buffer 1 --csv --no-show
```

Use custom input and output folders:

```powershell
python Plots.py --input input --output output --lat 22.92262 --lon 78.904003 --csv --no-show
```

### NDWI behaviour

If `output/NDWI/` already contains matching GeoTIFFs, they are sampled directly. Otherwise, `Plots.py` calculates NDWI at the point from raw-scene B03 and B08 data in `input/` and applies SCL cloud filtering when available. It does not create a full NDWI raster during this trend workflow.

### Generated files

```text
output/trends/trends_overlay_<lat>_<lon>.png
output/trends/trend_<lat>_<lon>.csv       # only with --csv
```

The plot uses a rolling median when enough valid observations are available. Missing, cloudy, invalid, or unreadable samples are omitted and reported in the console.

## Recommended End-to-End Runs

### Full analysis from raw scenes

```powershell
python main.py --input input --output output --mask-clouds
python cmap.py --date1 20161009 --date2 20261007 --lat 22.87706 --lon 78.89161 --radius 5 --lang both --no-show
python Plots.py --lat 22.92262 --lon 78.904003 --buffer 1 --csv --no-show
```

### Reprocess one year range and selected indices

```powershell
python main.py --start-year 2020 --end-year 2026 --indices NDVI NDMI --mask-clouds --overwrite
```

### Inspect outputs without opening windows

```powershell
python cmap.py --no-web --no-show
python Plots.py --csv --no-show
```

## Troubleshooting

### `Input folder not found`

Run the command from the project directory or pass the full paths explicitly:

```powershell
python main.py --input "F:\Data\file\Final\input" --output "F:\Data\file\Final\output"
```

### No GeoTIFFs are found by `cmap.py`

Run `main.py` first and confirm that files exist under `output/NDVI`, `output/MSAVI2`, `output/NDRE`, or `output/NDMI`. At least two distinct dates are required for a change map.

### An index is missing for a date

The scene may not contain all required bands, or the band filename may not follow the Sentinel-2 naming pattern. `main.py` logs missing bands and skips only the affected index.

### The selected point has no data

Check that the latitude and longitude fall inside the Sentinel-2 tile coverage and that the coordinate order is `--lat latitude --lon longitude`. For trend plots, try `--buffer 1` or a larger buffer.

### Cloud masking is unavailable

`--mask-clouds` requires an SCL file in the scene. If no SCL is found, `main.py` warns and processes without cloud masking for that scene.

### The interactive map has no basemap

The HTML map uses online Esri and OpenStreetMap tiles. Open it while connected to the internet. The locally generated risk overlay remains available even if the basemap cannot load.

## Interpretation And Limitations

- These are satellite-derived indicators, not field diagnoses.
- Harvest, ploughing, cloud contamination, shadows, registration differences, and seasonal timing can all change an index.
- Compare similar dates in the crop cycle when possible.
- Confirm risk zones in the field before applying irrigation, fertiliser, or pesticides.
- Risk and advisory thresholds are generic and should be tuned with local agronomic knowledge.
- The scripts assume projected Sentinel-2 UTM rasters for the change-map radius calculation.
