# Stack (formerly IGNITE) — Multi-Sensor MODIS & VIIRS Fire Regime Harmonization

**Winner — NASA Space Apps Challenge Karachi (Solo Entry | Challenge #08: Harmonization of MODIS and VIIRS Hot Spots)**  
*Note: The exact code submitted prior to the hackathon deadline is preserved under the [`spaceapps-submission`](../../releases/tag/spaceapps-submission) Git tag.*

---

## The Problem: The "Camera Illusion" (Sensor-Shift Distortion)
Long-term wildfire and agricultural burning trend analysis relies on combining NASA's legacy **1 km MODIS** (Terra & Aqua, 2000–present) archive with higher-resolution **375 m VIIRS** (Suomi-NPP, NOAA-20, NOAA-21, 2012–present) observations. 

Because a 375 m VIIRS pixel covers roughly one-seventh the area of a 1 km MODIS pixel and detects smaller, cooler thermal anomalies, raw active fire counts jump artificially by **over 300% starting in 2012**. Treating raw multi-sensor counts as a single continuous timeline distorts climate baselines and triggers false smog and crop-burning policy alarms.

---

## 3-Stage Harmonization Pipeline
**Stack** processes **1,286,521 raw satellite detections** across Pakistan (2000–2026)—combining historical bulk archives from **NASA FIRMS** (2000–2025) with Near Real-Time (NRT) observations via the **NASA FIRMS Area API** (2026)—into **1,044,233 unified 1 km-equivalent cell-days**:

1. **False-Positive & Industrial Filtering (`type = 0`):** Strips static industrial thermal anomalies (e.g., refinery gas flares) and low-confidence sensor noise to isolate presumed vegetation and agricultural fires.
2. **Spatial Co-Aggregation (`0.01° × 0.01°` Daily Grid):** Projects both 375 m VIIRS and 1 km MODIS detections onto a unified daily spatial grid (~1 km² cells), converting fragmented multi-pixel detections of a single fire into standardized **1 km cell-days** (removing **~83%** of sub-pixel oversampling bias).
3. **Monthly Sensor Calibration ($\alpha_m$):** Computes month-specific normalization factors from the 2012–2018 dual-sensor overlap period to align VIIRS sensitivity and orbital overpass differences with the 25-year MODIS baseline.

---

## Blind Holdout Validation (2019–2025)
To verify that the calibration generalizes out-of-sample without data leakage:
* Calibration coefficients ($\alpha_m$) were fit **strictly on the 2012–2018 overlap window**.
* The model was evaluated **blind on 2019–2025** against actual MODIS ground-truth observations, accurately tracking inter-annual fire spikes (e.g., 2021) and seasonal monsoon suppressions while preserving VIIRS's improved detection of smaller smoldering fires.

---

## Key Features
* **25-Year Burning Activity Calendar (`Year × Month`):** Interactive heatmap showing multi-decade fire seasonality, historical medians, real-time anomaly percentages, and mean Fire Radiative Power (MW).
* **Raw vs. Harmonized Toggle:** Side-by-side comparison proving how harmonization eliminates artificial 2012 and 2018 resolution jumps.
* **Custom Spatial Bounding Box Filtering:** Leaflet-powered geospatial map supporting provincial presets (Punjab, Sindh, Balochistan, KP & North) as well as custom map-drawn bounding boxes that dynamically recalculate all KPIs, calendar cells, and trend charts.
* **Accessibility & Data Export:** Defaults to a colorblind-safe **Viridis** palette alongside a **Thermal Fire** option, plus one-click filtered **CSV export**.

---

## Tech Stack
* **Data Engineering & ETL:** Python, Pandas, NumPy
* **Backend:** FastAPI, Uvicorn, Pre-aggregated JSON Spatial Cube
* **Frontend:** HTML5, Tailwind CSS, JavaScript, Leaflet.js, Chart.js
* **Data Sources:** NASA FIRMS Archive (MODIS Collection 6.1 & VIIRS 375m) & NASA FIRMS Area API (Near Real-Time)

---

## How to Run Locally
```bash
# 1. Clone the repository
git clone [https://github.com/ahmed10-sys/ignite-nasa.git](https://github.com/ahmed10-sys/ignite-nasa.git)
cd ignite-nasa

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate  # On macOS/Linux: source venv/bin/activate

# 3. Install dependencies
pip install fastapi uvicorn pandas numpy requests

# 4. (Optional) Rebuild dataset from raw CSVs + NASA FIRMS Area API
# set FIRMS_MAP_KEY=your_nasa_firms_key
python build_dataset.py

# 5. Start the FastAPI server
uvicorn main:app --reload