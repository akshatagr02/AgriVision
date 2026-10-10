
import { useEffect, useState } from "react";
import {
  CircleMarker,
  MapContainer,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";
import {
  Activity,
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  ClipboardCheck,
  Droplets,
  Leaf,
  MapPin,
  Satellite,
  ShieldCheck,
  Sprout,
  TrendingUp,
  Wind,
} from "lucide-react";

import "leaflet/dist/leaflet.css";
import "./MapExplorer.css";

interface MapExplorerProps {
  khasraNumber: string;
  startDate: string;
  endDate: string;
}

interface FieldPoint {
  id: number;
  lat: number;
  lng: number;
  demoNdvi: number;
}

interface AnalysisLayer {
  id: string;
  label: string;
  fullName: string;
  image: string;
  description: string;
  icon: typeof Leaf;
}

const fieldPoint: FieldPoint = {
  id: 1,
  lat: 22.85451,
  lng: 78.90208,
  demoNdvi: 0.7,
};

const mapCentre: [number, number] = [
  fieldPoint.lat,
  fieldPoint.lng,
];

const analyses: AnalysisLayer[] = [
  {
    id: "ndwi",
    label: "NDWI",
    fullName: "Normalized Difference Water Index",
    image: "/analysis/26_ndwi.png",
    description:
      "Helps examine surface-water patterns. Water availability cannot be established from this index alone.",
    icon: Droplets,
  },
  {
    id: "ndvi",
    label: "NDVI",
    fullName: "Normalized Difference Vegetation Index",
    image: "/analysis/26_ndvi.png",
    description:
      "Indicates vegetation greenness and helps track changes in green vegetation over time.",
    icon: Leaf,
  },
  {
    id: "ndre",
    label: "NDRE",
    fullName: "Normalized Difference Red Edge",
    image: "/analysis/26_ndre.png",
    description:
      "Can help assess vegetation condition and chlorophyll-related changes. Interpretation depends on the numerical values and legend.",
    icon: Activity,
  },
  {
    id: "gci",
    label: "GCI",
    fullName: "Green Chlorophyll Index",
    image: "/analysis/26_gci.png",
    description:
      "A spectral indicator associated with leaf chlorophyll content.",
    icon: Sprout,
  },
  {
    id: "msavi",
    label: "MSAVI",
    fullName: "Modified Soil-Adjusted Vegetation Index",
    image: "/analysis/26_msavi.png",
    description:
      "Helps assess vegetation while reducing the influence of exposed soil.",
    icon: Leaf,
  },
  {
    id: "ndmi",
    label: "NDMI",
    fullName: "Normalized Difference Moisture Index",
    image: "/analysis/26_ndmi.png",
    description:
      "Provides an indicator associated with vegetation moisture conditions.",
    icon: Droplets,
  },
];

const comparisonInsights = [
  {
    id: "ndwi",
    label: "NDWI",
    title: "Water extent",
    summary:
      "The described 2026 image appears to show a more clearly defined river channel than the 2016 image.",
    interpretation:
      "This may reflect differences in mapped water extent or image conditions.",
    caution:
      "Confirm with comparable acquisition dates, index values, cloud conditions and a consistent colour scale.",
  },
  {
    id: "ndvi",
    label: "NDVI",
    title: "Vegetation greenness",
    summary:
      "The described map pattern changes from predominantly red in 2016 to green and yellow in 2026.",
    interpretation:
      "If the legend confirms higher NDVI for those colours, this may indicate increased vegetation greenness.",
    caution:
      "Colour changes alone cannot establish improved crop health, vegetation cover or yield.",
  },
  {
    id: "ndre",
    label: "NDRE",
    title: "Red-edge response",
    summary:
      "The described map pattern changes from pale green in 2016 to dark blue in 2026.",
    interpretation:
      "The two descriptions suggest a visual difference between the maps.",
    caution:
      "The direction and magnitude of change depend on the numerical NDRE values and colour legend.",
  },
];

function formatDate(date: string) {
  if (!date) return "Date not selected";

  const [year, month, day] = date.split("-").map(Number);

  return new Date(year, month - 1, day).toLocaleDateString(
    "en-GB",
    {
      day: "2-digit",
      month: "short",
      year: "numeric",
    },
  );
}

function formatObservationPeriod(
  startDate: string,
  endDate: string,
) {
  if (!startDate || !endDate) return "Date not selected";

  return `${formatDate(startDate)} – ${formatDate(endDate)}`;
}

function FlyToPoint({
  lat,
  lng,
}: {
  lat: number;
  lng: number;
}) {
  const map = useMap();

  useEffect(() => {
    map.flyTo([lat, lng], 15, { duration: 0.8 });
  }, [map, lat, lng]);

  return null;
}

function getHealth(ndvi: number) {
  if (ndvi >= 0.6) {
    return {
      label: "Higher",
      description: "Higher illustrative vegetation-index value",
      color: "#328653",
    };
  }

  if (ndvi >= 0.4) {
    return {
      label: "Intermediate",
      description: "Intermediate illustrative vegetation-index value",
      color: "#c89a32",
    };
  }

  return {
    label: "Lower",
    description: "Lower illustrative vegetation-index value",
    color: "#c96655",
  };
}

export default function MapExplorer({
  khasraNumber,
  startDate,
  endDate,
}: MapExplorerProps) {
  const [selectedAnalysis, setSelectedAnalysis] =
    useState("ndvi");
  const [imageLoadFailed, setImageLoadFailed] = useState(false);

  const observationPeriod = formatObservationPeriod(
    startDate,
    endDate,
  );

  // Demo images currently represent 2026 only.
  const hasImageryForYear =
    Boolean(startDate) &&
    Boolean(endDate) &&
    startDate >= "2026-01-01" &&
    endDate <= "2026-12-31" &&
    startDate <= endDate;

  const health = getHealth(fieldPoint.demoNdvi);

  const analysis =
    analyses.find((item) => item.id === selectedAnalysis) ??
    analyses[1];

  function changeAnalysis(id: string) {
    setSelectedAnalysis(id);
    setImageLoadFailed(false);
  }

  return (
    <section className="geo-explorer" id="explorer">
      {/* PAGE HEADER */}
      <header className="geo-header">
        <div className="geo-header-copy">
          <span className="geo-eyebrow">
            <Satellite size={15} />
            GEOSPATIAL INTELLIGENCE
          </span>

          <h2>Field Analysis Explorer</h2>

          <p>
            Explore satellite-based vegetation and
            water indicators for {observationPeriod}.
          </p>
        </div>

        <span className="geo-demo-badge">DEMO DATA</span>
      </header>

      {/* MAP AND ANALYSIS PANEL */}
      <div className="geo-layout">
        <div className="geo-map-card">
          <div className="geo-map-topbar">
            <span>
              <MapPin size={15} />
              Selected field location
            </span>

            <span>1 selected location</span>
          </div>

          <MapContainer
            center={mapCentre}
            zoom={13}
            scrollWheelZoom={true}
            className="geo-map"
          >
            <TileLayer
              attribution="Tiles &copy; Esri — Sources: Esri, Maxar, Earthstar Geographics"
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            />

            {/* ONE MARKER ONLY */}
            <CircleMarker
              center={[fieldPoint.lat, fieldPoint.lng]}
              radius={9}
              pathOptions={{
                color: "#ffffff",
                weight: 3,
                fillColor: "#e9b34d",
                fillOpacity: 1,
              }}
            >
              <Popup>
                <div className="geo-popup">
                  <div className="geo-popup-kicker">
                    FIELD MONITORING
                  </div>

                  <h3>Selected Field</h3>

                  <p>
                    Explore vegetation indicators, moisture-related
                    indices and comparative satellite observations.
                  </p>

                  <div className="geo-popup-detail">
                    <CalendarDays size={15} />
                    <span>{observationPeriod}</span>
                  </div>

                  <div className="geo-popup-detail">
                    <Leaf size={15} />
                    <span>
                      Illustrative field health: {health.label}
                    </span>
                  </div>

                  <p className="geo-popup-coordinates">
                    {fieldPoint.lat.toFixed(5)}°,{" "}
                    {fieldPoint.lng.toFixed(5)}°
                  </p>

                  <small>
                    Provisional sample location. Not a verified
                    Khasra boundary.
                  </small>
                </div>
              </Popup>
            </CircleMarker>

            <FlyToPoint
              lat={fieldPoint.lat}
              lng={fieldPoint.lng}
            />
          </MapContainer>

          <div className="geo-map-footer">
            <MapPin size={14} />
            <span>
              Provisional coordinates · Official Khasra boundaries
              are not connected
            </span>
          </div>
        </div>

        {/* ANALYSIS PANEL */}
        <aside className="geo-analysis-card">
          <div className="geo-analysis-heading">
            <div>
              <span className="geo-eyebrow">
                SELECTED LOCATION
              </span>

              <h3>Khasra {khasraNumber}</h3>

              <p className="geo-location-subtitle">
                Narsara region · Provisional location
              </p>
            </div>

            <span className="geo-selected-dot" />
          </div>

          <div className="geo-coordinates">
            <div>
              <span>Latitude</span>
              <strong>{fieldPoint.lat.toFixed(5)}°</strong>
            </div>

            <div>
              <span>Longitude</span>
              <strong>{fieldPoint.lng.toFixed(5)}°</strong>
            </div>
          </div>

          <div className="geo-date">
            <CalendarDays size={16} />

            <div>
              <span className="geo-date-label">
                Selected analysis period
              </span>

              <strong>{observationPeriod}</strong>

              <span className="geo-date-status">
                {hasImageryForYear
                  ? "2026 demo raster previews available"
                  : "Demo imagery not supplied for this period"}
              </span>
            </div>
          </div>

          {hasImageryForYear ? (
            <>
              <div className="geo-layer-heading">
                <h4>Analysis layers</h4>
                <span>{analyses.length} indicators</span>
              </div>

              <div className="geo-layer-tabs">
                {analyses.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={
                      selectedAnalysis === item.id
                        ? "geo-layer active"
                        : "geo-layer"
                    }
                    aria-pressed={selectedAnalysis === item.id}
                    onClick={() => changeAnalysis(item.id)}
                  >
                    {item.label}
                  </button>
                ))}
              </div>

              <div className="geo-image-preview">
                {imageLoadFailed ? (
                  <div className="geo-image-unavailable">
                    <Satellite size={25} />
                    <p>
                      This image could not be loaded. Check that{" "}
                      <code>{analysis.image}</code> exists in
                      your <code>public/analysis</code> folder.
                    </p>
                  </div>
                ) : (
                  <img
                    key={analysis.image}
                    src={analysis.image}
                    alt={`${analysis.label} demonstration raster`}
                    onError={() => setImageLoadFailed(true)}
                  />
                )}

                <span className="geo-image-label">
                  {analysis.label} · DEMO
                </span>
              </div>

              <h3 className="geo-index-title">
                {analysis.fullName}
              </h3>

              <p className="geo-index-description">
                {analysis.description}
              </p>
            </>
          ) : (
            <div className="geo-year-unavailable">
              <CalendarDays size={26} />

              <h3>Imagery not supplied</h3>

              <p>
                The supplied demo rasters are for 2026.
                Select a date range entirely within 2026
                to preview these layers.
              </p>
            </div>
          )}

          <div className="geo-data-note">
            <ShieldCheck size={17} />

            <span>
              Demo only. The selected point is not linked to
              a verified parcel or measured satellite results.
            </span>
          </div>
        </aside>
      </div>

      {/* COMPARATIVE INSIGHTS */}
      <section className="geo-insights-card">
        <div className="geo-insights-header">
          <div>
            <span className="geo-eyebrow">
              SATELLITE INTERPRETATION
            </span>

            <h3>Comparative Insights</h3>

            <p>
              Provisional visual comparison of the 2016 and
              2026 index maps.
            </p>
          </div>

          <span className="geo-insights-period">
            2016 <span>→</span> 2026
          </span>
        </div>

        <div className="geo-insights-grid">
          {comparisonInsights.map((item) => (
            <article
              className="geo-insight-item"
              key={item.id}
            >
              <div className="geo-insight-title">
                <span className={`geo-index-tag geo-tag-${item.id}`}>
                  {item.label}
                </span>

                <h4>{item.title}</h4>
              </div>

              <p className="geo-insight-summary">
                {item.summary}
              </p>

              <p className="geo-insight-interpretation">
                {item.interpretation}
              </p>

              <div className="geo-insight-caution">
                <ShieldCheck size={16} />
                <span>{item.caution}</span>
              </div>
            </article>
          ))}
        </div>

        <div className="geo-insights-disclaimer">
          <ShieldCheck size={17} />

          <p>
            These interpretations are based on the visual
            descriptions supplied for this demo. They are not
            calculated from the selected point, date range or
            raster pixels. Verify the legends, acquisition dates
            and numerical index values before drawing conclusions.
          </p>
        </div>
      </section>

      {/* FIELD HEALTH BAR */}
      <section className="geo-health-card">
        <div className="geo-health-heading">
          <div className="geo-health-icon">
            <Activity size={21} />
          </div>

          <div>
            <span className="geo-eyebrow">
              FIELD CONDITION
            </span>

            <h3>Field Health Bar</h3>
          </div>

          <span
            className="geo-health-status"
            style={{
              color: hasImageryForYear
                ? health.color
                : "#7b867d",
            }}
          >
            {hasImageryForYear ? health.label : "Unavailable"}
          </span>
        </div>

        {hasImageryForYear ? (
          <>
            <div className="geo-health-meter">
              <div className="geo-health-track">
                <div
                  className="geo-health-marker"
                  style={{
                    left: `${fieldPoint.demoNdvi * 100}%`,
                    backgroundColor: health.color,
                  }}
                />
              </div>

              <div className="geo-health-scale">
                <span>Lower</span>
                <span>Intermediate</span>
                <span>Higher</span>
              </div>
            </div>

            <div className="geo-health-summary">
              <div>
                <span>Illustrative NDVI</span>
                <strong>{fieldPoint.demoNdvi.toFixed(2)}</strong>
              </div>

              <div>
                <span>Observation period</span>
                <strong>{observationPeriod}</strong>
              </div>

              <p>
                <TrendingUp size={15} />
                {health.description}
              </p>
            </div>
          </>
        ) : (
          <p className="geo-health-unavailable">
            No verified vegetation-index value is available
            for this date range.
          </p>
        )}

        <p className="geo-health-disclaimer">
          The NDVI value is synthetic demonstration data,
          not a measured satellite reading.
        </p>
      </section>

      {/* CROP RISK ASSESSMENT */}
      <section className="geo-risk-card">
        <div className="geo-risk-heading">
          <div className="geo-risk-icon">
            <ShieldCheck size={21} />
          </div>

          <div>
            <span className="geo-eyebrow">
              EARLY-WARNING OVERVIEW
            </span>

            <h3>Crop Risk Assessment</h3>

            <p>
              Indicators to investigate before deciding on
              field-level action.
            </p>
          </div>
        </div>

        <div className="geo-risk-grid">
          <article className="geo-risk-item">
            <div className="geo-risk-item-icon">
              <AlertTriangle size={20} />
            </div>

            <div className="geo-risk-item-copy">
              <h4>Possible disease risk</h4>
              <span className="geo-risk-status">
                Needs assessment
              </span>
              <p>
                Requires crop type, local weather and
                disease-specific evidence.
              </p>
            </div>
          </article>

          <article className="geo-risk-item">
            <div className="geo-risk-item-icon">
              <Droplets size={20} />
            </div>

            <div className="geo-risk-item-copy">
              <h4>Moisture stress</h4>
              <span className="geo-risk-status">
                Needs data
              </span>
              <p>
                Assess using moisture indices, rainfall and
                recent weather conditions.
              </p>
            </div>
          </article>

          <article className="geo-risk-item">
            <div className="geo-risk-item-icon">
              <Sprout size={20} />
            </div>

            <div className="geo-risk-item-copy">
              <h4>Vegetation stress</h4>
              <span className="geo-risk-status">
                Needs analysis
              </span>
              <p>
                Compare vegetation-index changes across
                multiple observation dates.
              </p>
            </div>
          </article>

          <article className="geo-risk-item">
            <div className="geo-risk-item-icon">
              <Wind size={20} />
            </div>

            <div className="geo-risk-item-copy">
              <h4>Weather-related stress</h4>
              <span className="geo-risk-status">
                Needs forecast
              </span>
              <p>
                Check heat, rainfall and wind forecasts
                alongside the crop growth stage.
              </p>
            </div>
          </article>
        </div>

        <div className="geo-risk-recommendation">
          <div className="geo-risk-recommendation-icon">
            <ClipboardCheck size={20} />
          </div>

          <div>
            <h4>Recommended next step</h4>
            <p>
              Inspect the field for leaf discoloration,
              wilting, unusual spots or waterlogging.
              Combine these observations with crop-specific
              data before deciding on treatment.
            </p>
          </div>
        </div>

        <div className="geo-risk-disclaimer">
          <CheckCircle2 size={16} />
          <p>
            Risk indicators are currently unassessed.
            No disease probability or confirmed diagnosis
            is generated by this demo. Real risk estimates
            require crop, weather and validated analysis data.
          </p>
        </div>
      </section>
    </section>
  );
}
