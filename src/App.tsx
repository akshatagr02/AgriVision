
import { useState, type FormEvent } from "react";
import {
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  Leaf,
  LoaderCircle,
  MapPin,
  Satellite,
  Search,
  ShieldCheck,
  Sprout,
} from "lucide-react";

import MapExplorer from "./MapExplorer";
import "./index.css";

type Screen = "search" | "year" | "map";

const MIN_YEAR = 2015;
const MAX_YEAR = 2026;

const availableYears = Array.from(
  { length: MAX_YEAR - MIN_YEAR + 1 },
  (_, index) => MAX_YEAR - index,
);

function dateString(year: number, month: number, day: number) {
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

function formatDateInput(date: string) {
  if (!date) return "";

  const [year, month, day] = date.split("-");
  return `${day}/${month}/${year}`;
}

function parseDateInput(value: string) {
  const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(value);
  if (!match) return "";

  const [, dayText, monthText, yearText] = match;
  const day = Number(dayText);
  const month = Number(monthText);
  const year = Number(yearText);
  const parsed = new Date(year, month - 1, day);

  if (
    year < MIN_YEAR ||
    year > MAX_YEAR ||
    parsed.getFullYear() !== year ||
    parsed.getMonth() !== month - 1 ||
    parsed.getDate() !== day
  ) {
    return "";
  }

  return dateString(year, month, day);
}

function formatDate(date: string) {
  if (!date) return "Date not selected";

  const [year, month, day] = date.split("-").map(Number);

  return new Date(year, month - 1, day).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export default function App() {
  const [screen, setScreen] = useState<Screen>("search");

  const [khasraInput, setKhasraInput] = useState("");
  const [khasraNumber, setKhasraNumber] = useState("");

  const [village, setVillage] = useState("Narsara");
  const [district, setDistrict] = useState("Durg");

  const [selectedYear, setSelectedYear] = useState(MAX_YEAR);
  const [startDate, setStartDate] = useState("2016-10-07");
  const [endDate, setEndDate] = useState("2026-10-10");
  const [startDateInput, setStartDateInput] = useState("07/10/2016");
  const [endDateInput, setEndDateInput] = useState("10/10/2026");

  const [error, setError] = useState("");
  const [isOpeningExplorer, setIsOpeningExplorer] = useState(false);

  const observationPeriod =
    `${formatDate(startDate)} – ${formatDate(endDate)}`;

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const cleanedKhasra = khasraInput.trim();
    const cleanedVillage = village.trim();
    const cleanedDistrict = district.trim();

    if (!cleanedKhasra) {
      setError("Enter a Khasra number to continue.");
      return;
    }

    // Accepts numeric values and subdivisions such as 636/1.
    if (!/^\d+(?:\/\d+)*$/.test(cleanedKhasra)) {
      setError("Use a numeric Khasra format, such as 142 or 636/1.");
      return;
    }

    if (!cleanedVillage || !cleanedDistrict) {
      setError("Enter both the village and district.");
      return;
    }

    setKhasraNumber(cleanedKhasra);
    setVillage(cleanedVillage);
    setDistrict(cleanedDistrict);
    setError("");
    setScreen("year");
  }

  function handleYearPreset(year: number) {
    const start = dateString(year, 1, 1);
    const end = dateString(year, 12, 31);
    setSelectedYear(year);
    setStartDate(start);
    setEndDate(end);
    setStartDateInput(formatDateInput(start));
    setEndDateInput(formatDateInput(end));
    setError("");
  }

  function handleStartDateChange(value: string) {
    setStartDate(value);
    setError("");

    if (value) {
      setSelectedYear(Number(value.slice(0, 4)));

      // Keep the range valid when the start date moves forward.
      if (endDate && value > endDate) {
        setEndDate(value);
        setEndDateInput(formatDateInput(value));
      }
    }
  }

  function handleEndDateChange(value: string) {
    setEndDate(value);
    setError("");

    if (value) {
      setSelectedYear(Number(value.slice(0, 4)));

      // Keep the range valid when the end date moves backward.
      if (startDate && value < startDate) {
        setStartDate(value);
        setStartDateInput(formatDateInput(value));
      }
    }
  }

  function openMap() {
    if (!startDate || !endDate) {
      setError("Choose both a start date and an end date.");
      return;
    }

    if (startDate > endDate) {
      setError("The start date must be on or before the end date.");
      return;
    }

    setSelectedYear(Number(endDate.slice(0, 4)));
    setError("");
    setScreen("map");
  }

  function openFieldExplorer() {
    if (isOpeningExplorer) return;

    const parsedStartDate = parseDateInput(startDateInput);
    const parsedEndDate = parseDateInput(endDateInput);
    if (!parsedStartDate || !parsedEndDate) {
      setError(`Enter valid dates as DD/MM/YYYY between ${MIN_YEAR} and ${MAX_YEAR}.`);
      return;
    }

    if (parsedStartDate > parsedEndDate) {
      setError("The start date must be on or before the end date.");
      return;
    }

    const explorerPath =
      khasraNumber === "143/22"
        ? "/riskmap_20161009_20261007_22.9213_78.8680-r.html"
        : "/riskmap_20161009_20261007_22.8771_78.8916.html";

    setIsOpeningExplorer(true);
    window.setTimeout(() => {
      window.location.assign(explorerPath);
    }, 650);
  }

  function goBackToSearch() {
    setError("");
    setScreen("search");
  }

  function goBackToYear() {
    setError("");
    setScreen("year");
  }

  function goHome() {
    setError("");
    setScreen("search");
  }

  return (
    <div className="agri-app">
      {/* TOP NAVIGATION */}
      <header className="agri-topbar">
        <a
          href="#home"
          className="agri-brand"
          onClick={(event) => {
            event.preventDefault();
            goHome();
          }}
          aria-label="Agrivision home"
        >
          <span className="agri-brand-icon">
            <Sprout size={24} />
          </span>

          <span>
            <h1>Agrivision</h1>
            <p>Satellite-powered agricultural insights</p>
          </span>
        </a>

      
      </header>

      <main className="agri-main">
        {/* SCREEN 1: LAND SEARCH */}
        {screen === "search" && (
          <section className="landing-screen" id="home">
            <div className="landing-copy">
              <span className="agri-eyebrow">
                <Satellite size={15} />
                GEOSPATIAL AGRICULTURE
              </span>

              <h1>
                Understand your land.
                <br />
                <span>Grow with insight.</span>
              </h1>

              <p className="landing-description">
                Explore satellite imagery and vegetation indicators.
                Select your land and observation period to begin.
              </p>

              <div className="landing-highlights">
                <span className="landing-highlight">
                  <Leaf size={15} />
                  Vegetation indicators
                </span>

                <span className="landing-highlight">
                  <Satellite size={15} />
                  Satellite imagery
                </span>

                <span className="landing-highlight">
                  <CalendarDays size={15} />
                  Custom date ranges
                </span>
              </div>

              <div className="landing-feature">
                <div className="landing-feature-icon">
                  <MapPin size={20} />
                </div>

                <div>
                  <strong>Land-focused exploration</strong>
                  <p>
                    Review sample locations, satellite-analysis layers
                    and comparative observations in one place.
                  </p>
                </div>
              </div>
            </div>

            <form className="search-card" onSubmit={handleSearch}>
              <span className="agri-eyebrow">
                <Search size={14} />
                START EXPLORING
              </span>

              <h2>Find your land</h2>

              <p>Enter your land details to open the explorer.</p>

              <div className="search-field">
                <label htmlFor="khasraNumber">Khasra number</label>

                <input
                  id="khasraNumber"
                  type="text"
                  inputMode="numeric"
                  autoComplete="off"
                  placeholder="e.g. 636/1"
                  value={khasraInput}
                  onChange={(event) => {
                    setKhasraInput(event.target.value);
                    setError("");
                  }}
                  aria-invalid={Boolean(error)}
                  aria-describedby="khasra-helper"
                  required
                />

                <span className="search-helper" id="khasra-helper">
                  Enter the numeric format shown on your land records.
                </span>
              </div>

              <div className="search-field">
                <label htmlFor="village">Village</label>

                <input
                  id="village"
                  type="text"
                  autoComplete="address-level2"
                  value={village}
                  onChange={(event) => {
                    setVillage(event.target.value);
                    setError("");
                  }}
                  placeholder="Enter village name"
                  required
                />
              </div>

              <div className="search-field">
                <label htmlFor="district">District</label>

                <input
                  id="district"
                  type="text"
                  value={district}
                  onChange={(event) => {
                    setDistrict(event.target.value);
                    setError("");
                  }}
                  placeholder="Enter district name"
                  required
                />
              </div>

              {error && (
                <p className="search-error" role="alert">
                  {error}
                </p>
              )}

              <button className="agri-primary-button" type="submit">
                Continue to date selection
                <ArrowRight size={17} />
              </button>

            </form>
          </section>
        )}

        {/* SCREEN 2: DATE SELECTION */}
        {screen === "year" && (
          <section className="year-screen">
            <button
              className="agri-back-button"
              type="button"
              onClick={goBackToSearch}
            >
              <ArrowLeft size={16} />
              Back to land details
            </button>

            <div className="year-screen-header">
              <span className="agri-eyebrow">
                <CalendarDays size={15} />
                OBSERVATION PERIOD
              </span>

              <h1>Choose your analysis dates</h1>

              <p>
                Select a year as a quick preset, or choose specific
                start and end dates. You can compare dates across
                different years.
              </p>
            </div>

            <div className="year-selection-summary">
              <div className="year-summary-icon">
                <MapPin size={19} />
              </div>

              <div>
                <span>Selected land reference</span>
                <strong>Khasra {khasraNumber}</strong>
                <p>
                  {village}, {district}
                </p>
              </div>

              <CheckCircle2
                size={19}
                className="year-summary-check"
              />
            </div>

            <div className="date-picker-card">
              <div className="date-picker-heading">
                <CalendarDays size={19} />

                <div>
                  <h3>Custom date range</h3>
                  <p>Choose the period you want to investigate.</p>
                </div>
              </div>

              <div className="date-picker-grid">
                <div className="date-field">
                  <label htmlFor="startDate">From date</label>

                  <input
                    id="startDate"
                    type="text"
                    inputMode="numeric"
                    placeholder="DD/MM/YYYY"
                    value={startDateInput}
                    onChange={(event) => {
                      const value = event.target.value;
                      setStartDateInput(value);
                      const parsedDate = parseDateInput(value);
                      if (parsedDate) handleStartDateChange(parsedDate);
                      else setError("");
                    }}
                    required
                  />
                </div>

                <div className="date-field">
                  <label htmlFor="endDate">To date</label>

                  <input
                    id="endDate"
                    type="text"
                    inputMode="numeric"
                    placeholder="DD/MM/YYYY"
                    value={endDateInput}
                    onChange={(event) => {
                      const value = event.target.value;
                      setEndDateInput(value);
                      const parsedDate = parseDateInput(value);
                      if (parsedDate) handleEndDateChange(parsedDate);
                      else setError("");
                    }}
                    required
                  />
                </div>
              </div>

              <div className="year-range-preview">
                <CalendarDays size={19} />

                <div>
                  <span>Selected analysis period</span>
                  <strong>{observationPeriod}</strong>
                </div>
              </div>

              {error && (
                <p className="search-error" role="alert">
                  {error}
                </p>
              )}
            </div>

   {/*
    <div className="year-preset-heading">
              <h3>Or select a year preset</h3>
              <p>
                Selecting a year resets the dates to that full year.
              </p>
            </div>

            <div className="year-grid">
              {availableYears.map((year) => {
                const isFullYear =
                  startDate === dateString(year, 1, 1) &&
                  endDate === dateString(year, 12, 31);

                return (
                  <button
                    key={year}
                    type="button"
                    className={
                      isFullYear ? "year-option active" : "year-option"
                    }
                    aria-pressed={isFullYear}
                    onClick={() => handleYearPreset(year)}
                  >
                    <strong>{year}</strong>
                    <span>
                      {isFullYear ? "Full year selected" : "Use full year"}
                    </span>
                  </button>
                );
              })}
            </div> 
   */} 
         

            <div className="year-screen-actions">
              <button
                className="agri-secondary-button"
                type="button"
                onClick={goBackToSearch}
              >
                <ArrowLeft size={16} />
                Back
              </button>
              <button
                className="agri-primary-button"
                type="button"
                onClick={openFieldExplorer}
                disabled={isOpeningExplorer}
                aria-live="polite"
              >
                {isOpeningExplorer ? (
                  <>
                    <LoaderCircle className="agri-loading-spinner" size={17} />
                    Opening field explorer...
                  </>
                ) : (
                  <>
                    Open field explorer
                    <ArrowRight size={17} />
                  </>
                )}
              </button>
            </div>
          </section>
        )}

        {/* SCREEN 3: MAP AND ANALYSIS DASHBOARD */}
        {screen === "map" && (
          <section className="map-screen">
            <div className="map-screen-heading">
              <div>
                <span className="agri-eyebrow">
                  <Satellite size={14} />
                  FIELD INTELLIGENCE
                </span>

                <h1>Land analysis dashboard</h1>

                <p>
                  Khasra {khasraNumber} · {village}, {district}
                </p>

                <p className="map-selected-period">
                  <CalendarDays size={15} />
                  {observationPeriod}
                </p>
              </div>

              <div className="map-screen-heading-actions">
                <button
                  className="agri-secondary-button"
                  type="button"
                  onClick={goBackToYear}
                >
                  <ArrowLeft size={15} />
                  Change dates
                </button>

                <button
                  className="agri-secondary-button"
                  type="button"
                  onClick={goBackToSearch}
                >
                  <Search size={15} />
                  New search
                </button>
              </div>
            </div>

            <div className="map-demo-banner">
              <ShieldCheck size={17} />

             
            </div>

            <MapExplorer
              key={`${khasraNumber}-${startDate}-${endDate}-${village}-${district}`}
              khasraNumber={khasraNumber}
              selectedYear={selectedYear}
              startDate={startDate}
              endDate={endDate}
            />
          </section>
        )}
      </main>

      {/* FOOTER */}
      <footer className="agri-footer">
        <p>
          <strong>Agrivision</strong> · Satellite-powered agricultural
          exploration
        </p>

        <p>
          Prototype interface · Verify findings before making
          agricultural decisions
        </p>
      </footer>
    </div>
  );
}
