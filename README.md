# 🌾 Agrivision — Satellite-Powered Agricultural Intelligence

**Turning satellite imagery into actionable agricultural insights.**

Agrivision is a web-based agricultural monitoring platform designed to help users explore farmland, visualize vegetation indices, compare observations across time, and understand crop conditions through geospatial data.

By bringing satellite imagery, vegetation analysis, and field-level visualization into a single interface, Agrivision aims to make agricultural intelligence more accessible, interpretable, and useful for data-driven decision-making.

> **Project status:** Prototype in development. Satellite-index previews, field-health indicators, comparative insights, and location data may currently use demonstration values. Official land-parcel boundaries and validated, field-specific analysis require compatible geospatial datasets and integration.

---

## ✨ Key Features

### 🛰️ Satellite Imagery Explorer
- View satellite imagery through an interactive map.
- Explore selected locations using a map-based interface.
- Display observation periods for agricultural monitoring.
- Designed to support future integration of georeferenced farm boundaries.

### 🌱 Vegetation Index Visualization
Agrivision provides an interface for exploring six vegetation and moisture-related indices:

| Index | Full Form | Intended Use |
|---|---|---|
| **NDVI** | Normalized Difference Vegetation Index | Assess vegetation greenness and relative vigor |
| **NDRE** | Normalized Difference Red Edge | Explore vegetation condition using red-edge information |
| **GCI** | Green Chlorophyll Index | Estimate relative canopy chlorophyll using suitable imagery |
| **MSAVI** | Modified Soil-Adjusted Vegetation Index | Reduce soil-background influence in vegetation analysis |
| **NDMI** | Normalized Difference Moisture Index | Explore vegetation water-content patterns |
| **NDWI** | Normalized Difference Water Index | Investigate water-related features, depending on the selected formulation |

*Interpretation depends on the index formulation, sensor bands, image quality, crop type, growth stage, and environmental conditions. NDWI has multiple definitions, so the specific formulation should be documented when real analysis is integrated.*

### 📅 Historical & Custom Date Selection
- Select an observation year from **2015 to 2026**.
- Choose a custom start date and end date.
- Display the selected observation period across the interface.
- Establish a foundation for comparing agricultural conditions over time.

Historical comparisons require actual imagery or index products from the corresponding dates; selecting a date range alone does not retrieve historical satellite data.

### 🗺️ Interactive Field Mapping
- Explore locations on an interactive satellite map.
- Display selected-location information through map popups.
- Designed for future rendering of agricultural parcel polygons using GeoJSON.
- Supports a planned transition from point-based location selection to field-level visualization.

**Important:** A map marker is not an official farm boundary. Accurate Khasra-level mapping requires verified cadastral data that is correctly georeferenced to the satellite basemap.

### 📊 Comparative Insights
Agrivision's interface is designed to present:
- Changes in vegetation patterns over time.
- Side-by-side index comparisons.
- Field-condition summaries.
- Visual indicators that help users investigate potential agricultural issues.

Actual trends and conclusions must be computed from validated imagery or raster products rather than static demonstration content.

### 🚜 Crop Risk Assessment — Planned Capability
The project is designed to evolve toward crop-risk assessment using relevant satellite observations and agricultural data.

Potential future capabilities include:
- Identifying unusual vegetation patterns.
- Flagging areas for field inspection.
- Combining moisture and vegetation indicators.
- Incorporating crop type, growth stage, weather, and ground observations.

Agrivision should not be treated as a disease-diagnosis system or a substitute for expert agricultural assessment.

---

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| **React** | Component-based user interface |
| **TypeScript** | Type safety and maintainable application code |
| **Vite** | Development server and build tooling |
| **Leaflet** | Interactive mapping |
| **React Leaflet** | React integration for Leaflet maps |
| **Lucide React** | Interface icons |
| **Recharts** | Data visualization and charts |
| **CSS** | Responsive layouts and custom styling |
| **Esri World Imagery** | Satellite basemap tiles |

### Architecture Overview

```text
User
  │
  ▼
Agrivision Web Interface
  │
  ├── Location & Khasra Search
  │
  ├── Year and Date-Range Selection
  │
  ├── Interactive Satellite Map
  │      └── Field Boundaries (when available)
  │
  ├── Vegetation Index Explorer
  │      ├── NDVI
  │      ├── NDRE
  │      ├── GCI
  │      ├── MSAVI
  │      ├── NDMI
  │      └── NDWI
  │
  └── Comparative Insights & Field Health
         │
         ▼
   Future Geospatial Data Pipeline
         │
         ├── Satellite Imagery
         ├── Raster Index Products
         ├── Cadastral / Parcel Data
         └── Validated Agricultural Observations
```

The current application is primarily a frontend prototype. A production data pipeline and backend integration can be added as the project develops.

---

## 🚀 Getting Started

### Prerequisites

Make sure you have installed:

- [Node.js](https://nodejs.org/) — preferably an active LTS release.
- npm, which is included with Node.js.
- [Git](https://git-scm.com/).
- [Visual Studio Code](https://code.visualstudio.com/) or another code editor.

### 1. Clone the Repository

Replace the example URL with your actual GitHub repository URL.

```bash
git clone https://github.com/YOUR_USERNAME/agrivision.git
cd agrivision
```

### 2. Install Dependencies

```bash
npm install
```

The project uses React, TypeScript, Vite, Leaflet, React Leaflet, Recharts, and Lucide React.

If any dependency is missing from your project, install it with:

```bash
npm install lucide-react leaflet react-leaflet recharts
npm install -D @types/leaflet
```

### 3. Start the Development Server

```bash
npm run dev
```

Open the local URL printed in your terminal, typically:

```text
http://localhost:5173/
```

### 4. Build for Production

```bash
npm run build
```

### 5. Preview the Production Build

```bash
npm run preview
```

---

## 📁 Project Structure

The following is the expected high-level structure; your repository may contain additional files.

```text
agrivision/
├── public/
│   └── analysis/
│       ├── 26_gci.png
│       ├── 26_msavi.png
│       ├── 26_ndmi.png
│       ├── 26_ndre.png
│       ├── 26_ndvi.png
│       └── 26_ndwi.png
│
├── src/
│   ├── App.tsx
│   ├── MapExplorer.tsx
│   ├── MapExplorer.css
│   ├── index.css
│   └── main.tsx
│
├── index.html
├── package.json
├── package-lock.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

**Note:** The raster filenames above are expected demonstration assets. Ensure that each file exists before relying on its preview in the interface.

---

## 🗺️ Agricultural Field Boundaries

A key development goal is to display individual agricultural parcels directly over satellite imagery instead of representing each selected field with a single point.

The intended workflow is:

1. Obtain authoritative parcel or cadastral boundary data for the target region.
2. Verify the coordinate reference system and georeferencing accuracy.
3. Convert the data into a compatible format, such as GeoJSON, if necessary.
4. Load the boundary features into the Leaflet map.
5. Style individual polygons and enable parcel selection.
6. Connect parcel identifiers to the appropriate Khasra records, where reliable identifiers are available.

For a Chhattisgarh deployment, the official [Chhattisgarh Bhu-Naksha portal](https://revenue.cg.nic.in/bhunaksha/) is a relevant starting point for cadastral maps and plot information.

The availability of downloadable data, access permissions, and coordinate accuracy must be verified for the specific district and village. A cadastral map may not align directly with satellite imagery without georeferencing.

---

## 📡 Data & Analysis Integrity

Agrivision's long-term usefulness depends on reliable geospatial data.

A production implementation should establish:

- **Satellite data provenance:** Record the source, sensor, acquisition date, and processing method.
- **Cloud and image quality handling:** Exclude or flag observations affected by clouds, shadows, or poor-quality pixels.
- **Correct index calculations:** Use the appropriate spectral bands and document each index formula.
- **Spatial alignment:** Ensure raster imagery, parcel boundaries, and map layers share compatible coordinates.
- **Temporal consistency:** Compare observations using compatible sensors, processing methods, and seasonal windows.
- **Ground validation:** Validate important agricultural conclusions against field observations or trusted reference data.
- **Uncertainty reporting:** Distinguish measured results from estimates and demonstration values.

Vegetation indices are indicators, not definitive diagnoses. A low vegetation-index value, for example, can reflect several different conditions and should not automatically be interpreted as disease or crop failure.

---

## 🌍 Potential Applications

Agrivision is intended to support exploration of agricultural geospatial data for:

- Monitoring vegetation patterns across agricultural areas.
- Comparing crop conditions across observation periods.
- Identifying locations that may require closer field inspection.
- Exploring moisture-related and vegetation-related spatial patterns.
- Supporting data-informed agricultural monitoring at parcel level.

Its practical value will depend on the availability, resolution, and accuracy of the underlying datasets.

---

## 🤝 Contributing

Contributions, feedback, and ideas are welcome.

1. Fork the repository.
2. Create a feature branch:

   ```bash
   git checkout -b feature/your-feature
   ```

3. Make your changes and test the application.
4. Commit your changes:

   ```bash
   git commit -m "Add your feature"
   ```

5. Push your branch:

   ```bash
   git push origin feature/your-feature
   ```

6. Open a pull request describing the changes.

For substantial changes, consider opening an issue first to discuss the implementation approach.

---

## 🔒 Limitations

Agrivision is under active development.

- Khasra search is not yet connected to an authoritative land-record database.
- Selected locations may use demonstration coordinates.
- Field boundaries are not official unless sourced from and verified against authoritative cadastral records.
- Raster previews and health indicators may be illustrative rather than calculated from live satellite observations.
- Historical date selection does not itself guarantee imagery availability.
- Crop-risk assessments require suitable input data and validation before they can support real-world decisions.

Do not use demonstration outputs as the sole basis for crop treatment, irrigation, financial, or other high-impact agricultural decisions.

---

## 📜 Data Attribution & Licensing

- **Satellite basemap:** Esri World Imagery. Review the applicable [Esri terms of use](https://www.esri.com/en-us/legal/terms/full-master-agreement) and attribution requirements before public deployment.
- **Cadastral data:** Attribute the relevant government data source and follow its access and reuse conditions.
- **Satellite analysis datasets:** Document the provider, license, processing pipeline, and relevant usage restrictions when integrated.

The application source code's license does not automatically grant rights to redistribute third-party imagery or land-record datasets.

---

## 👩‍💻 Project

**Agrivision — Satellite-Powered Agricultural Intelligence**

Built with React, TypeScript, Leaflet, and geospatial visualization technologies.

Developed as a prototype exploring how satellite imagery and agricultural data can be brought together in an accessible web interface.

---

*From pixels in orbit to insights on the ground.* 🌱
