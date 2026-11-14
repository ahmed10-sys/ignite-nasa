import os
import io
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

load_dotenv()

app = FastAPI(
    title="IGNITE | MODIS & VIIRS Harmonized Fire Regime API",
    description="NASA Space Apps Challenge #08 — Harmonization of MODIS and VIIRS Hot Spots",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
MAP_KEY = os.getenv("FIRMS_MAP_KEY")
PAK_BBOX = "60.87,23.69,77.83,37.08"


@app.get("/", include_in_schema=False)
def serve_dashboard():
    index_path = BASE_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found in project root.")
    return FileResponse(index_path)


@app.get("/dashboard_data.json", include_in_schema=False)
def serve_dashboard_data():
    data_path = BASE_DIR / "dashboard_data.json"
    if not data_path.exists():
        raise HTTPException(
            status_code=404,
            detail="dashboard_data.json not found. Run 'python build_dataset.py' first.",
        )
    return FileResponse(data_path, media_type="application/json")


@app.get("/api/health")
def health_check():
    data_path = BASE_DIR / "dashboard_data.json"
    return {
        "status": "online",
        "team": "IGNITE",
        "challenge": "Challenge #08 - Harmonization of MODIS and VIIRS Hot Spots",
        "dashboard_data_ready": data_path.exists(),
        "firms_api_key_configured": bool(MAP_KEY),
    }


@app.get("/api/live-preview")
def get_live_nrt_preview(days: int = 2):
    """Fetches live NASA FIRMS NRT counts for Pakistan to demonstrate real-time ingestion."""
    if not MAP_KEY:
        raise HTTPException(status_code=400, detail="FIRMS_MAP_KEY not configured in .env")

    days = max(1, min(days, 5))
    summary = {}

    for source in ["MODIS_NRT", "VIIRS_NOAA20_NRT"]:
        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{source}/{PAK_BBOX}/{days}"
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200 and "latitude" in resp.text:
                df = pd.read_csv(io.StringIO(resp.text))
                summary[source] = len(df)
            else:
                summary[source] = 0
        except Exception as e:
            summary[source] = f"error: {str(e)}"

    return {"region": "Pakistan", "window_days": days, "live_detections": summary}