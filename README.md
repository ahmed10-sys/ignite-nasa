# 🔥 IGNITE | NASA Space Apps 2026
**Challenge #08:** Harmonization of MODIS and VIIRS Hot Spots

![IGNITE Dashboard](https://img.shields.io/badge/Status-Live_Demo_Ready-success?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Pandas](https://img.shields.io/badge/Data_Pipeline-Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)

## 🌍 The Problem
For over two decades, NASA has tracked active fires via satellite. However, the legacy MODIS sensor tracks fires in **1 km pixels**, while newer VIIRS sensors use **375 m pixels**. 
Because VIIRS is much sharper and more sensitive, raw fire counts artificially spike by over **300%** starting in 2012. Without harmonization, emergency managers and climate scientists cannot reliably compare today's fires against the 25-year historical baseline.

## 🚀 Our Solution: IGNITE
IGNITE is an end-to-end data pipeline and interactive web application that processes over **1.28 million real NASA FIRMS fire detections** for Pakistan (2000–2026) and harmonizes them into a unified, mathematically rigorous baseline.

### Key Features
1. **Automated ETL Pipeline:** Ingests 26 years of historical CSVs + live 2026 Near Real-Time (NRT) Area API data.
2. **Deterministic Harmonization (3 Steps):**
   * **Filters False Positives:** Strips out industrial gas flares (`type != 0`) and low-confidence thermal noise.
   * **Spatial Co-Aggregation:** Maps high-resolution 375m VIIRS sub-pixels onto a unified `0.01°` (~1 km) daily grid to eliminate double-counting.
   * **Monthly Calibration ($\alpha_m$):** Normalizes seasonal VIIRS oversampling using a strict empirical ratio derived from the 2012–2018 sensor overlap period.
3. **Interactive Burning Activity Calendar:** Colorblind-safe (Viridis) web dashboard allowing land managers to instantly compare current regional burns against 25-year historical medians.
4. **Blind Holdout Validation:** Proves our algorithm works by training on 2012–2018 data and blindly predicting 2019–2025 ground-truth MODIS counts with high accuracy.

---

## 🛠️ How to Run Locally

**1. Clone and Setup Environment**
```bash
git clone [https://github.com/ahmed10-sys/ignite-nasa.git](https://github.com/ahmed10-sys/ignite-nasa.git)
cd ignite-nasa
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt