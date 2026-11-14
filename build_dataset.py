import os
import io
import json
import glob
import requests
import numpy as np
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
MAP_KEY = os.getenv("FIRMS_MAP_KEY")
CSV_DIR = Path("data/pakistan_csvs")
PAK_BBOX = "60.87,23.69,77.83,37.08"

PROVINCES = ["All Pakistan", "Punjab", "Sindh", "Balochistan", "KP & North"]

def assign_province(df: pd.DataFrame) -> pd.Series:
    """Fast vectorized administrative region tagging for Pakistan."""
    lat = df["latitude"].values
    lon = df["longitude"].values
    conditions = [
        (lat <= 28.5) & (lon >= 66.6),
        (lat <= 32.0) & (lon < 69.3),
        (lat > 28.5) & (lat <= 34.0) & (lon >= 69.3),
        (lat > 32.0),
    ]
    choices = ["Sindh", "Balochistan", "Punjab", "KP & North"]
    return pd.Series(np.select(conditions, choices, default="Balochistan"), index=df.index)

def load_archive_csvs() -> pd.DataFrame:
    """Loads and standardizes all historical MODIS and VIIRS CSVs."""
    files = sorted(glob.glob(str(CSV_DIR / "*.csv")))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {CSV_DIR}.")

    print(f"Found {len(files)} historical CSV files. Loading and cleaning...")
    frames = []

    for fpath in files:
        fname = os.path.basename(fpath).lower()
        df = pd.read_csv(fpath, low_memory=False)

        if "type" in df.columns:
            df = df[df["type"] == 0].copy()

        if "modis" in fname:
            if "confidence" in df.columns:
                df = df[pd.to_numeric(df["confidence"], errors="coerce") >= 30].copy()
            df["temp_kelvin"] = df["brightness"]
            df["sensor_group"] = "MODIS"
        else:
            if "confidence" in df.columns:
                df = df[df["confidence"].astype(str).str.lower() != "l"].copy()
            df["temp_kelvin"] = df["bright_ti4"]
            df["sensor_group"] = "VIIRS"

        keep_cols = ["latitude", "longitude", "acq_date", "temp_kelvin", "frp", "sensor_group"]
        frames.append(df[keep_cols])

    combined = pd.concat(frames, ignore_index=True)
    combined["acq_date"] = pd.to_datetime(combined["acq_date"], format="mixed")
    return combined

def fetch_recent_2026() -> pd.DataFrame:
    """Appends live 2026 NRT hotspots from NASA FIRMS API."""
    if not MAP_KEY:
        return pd.DataFrame()

    nrt_sources = [
        ("MODIS_NRT", "MODIS", "brightness"),
        ("VIIRS_NOAA20_NRT", "VIIRS", "bright_ti4"),
        ("VIIRS_SNPP_NRT", "VIIRS", "bright_ti4"),
    ]
    frames = []
    for source, group, temp_col in nrt_sources:
        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{source}/{PAK_BBOX}/5"
        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code == 200 and "latitude" in resp.text:
                df = pd.read_csv(io.StringIO(resp.text))
                if group == "MODIS" and "confidence" in df.columns:
                    df = df[pd.to_numeric(df["confidence"], errors="coerce") >= 30].copy()
                elif group == "VIIRS" and "confidence" in df.columns:
                    df = df[df["confidence"].astype(str).str.lower() != "l"].copy()
                df["temp_kelvin"] = df[temp_col]
                df["sensor_group"] = group
                df["acq_date"] = pd.to_datetime(df["acq_date"], format="mixed")
                frames.append(df[["latitude", "longitude", "acq_date", "temp_kelvin", "frp", "sensor_group"]])
        except Exception:
            pass

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def harmonize_and_export(df: pd.DataFrame):
    """Runs 3-step spatio-temporal harmonization with PERFECT mathematical scaling."""
    df["year"] = df["acq_date"].dt.year
    df["month"] = df["acq_date"].dt.month
    df["province"] = assign_province(df)

    # 1. 1km Spatial Grid
    df["grid_lat"] = df["latitude"].round(2)
    df["grid_lon"] = df["longitude"].round(2)

    # 2. Collapse to daily cell-days
    cells = (
        df.groupby(["province", "year", "month", "acq_date", "grid_lat", "grid_lon"])
        .agg(
            raw_detections=("latitude", "count"),
            has_modis=("sensor_group", lambda s: int("MODIS" in s.values)),
            has_viirs=("sensor_group", lambda s: int("VIIRS" in s.values)),
            mean_frp=("frp", "mean"),
        )
        .reset_index()
    )

    # 3. Monthly Calibration Factor: Ratio of MODIS truth to ALL detections during overlap
    def compute_monthly_alpha(subset: pd.DataFrame) -> dict:
        m_grp = subset.groupby("month").agg(
            modis_total=("has_modis", "sum"),
            total_cells=("raw_detections", "count") # Count rows (cell-days)
        )
        alphas = {}
        for m in range(1, 13):
            if m in m_grp.index and m_grp.loc[m, "total_cells"] > 0:
                raw_alpha = m_grp.loc[m, "modis_total"] / m_grp.loc[m, "total_cells"]
                alphas[m] = round(float(np.clip(raw_alpha, 0.01, 1.0)), 4)
            else:
                alphas[m] = 0.25
        return alphas

    overlap_all = cells[(cells["year"] >= 2012) & (cells["year"] <= 2025)]
    train_overlap = cells[(cells["year"] >= 2012) & (cells["year"] <= 2018)]

    alpha_full = compute_monthly_alpha(overlap_all)
    alpha_train = compute_monthly_alpha(train_overlap)

    # Pre-2012: MODIS baseline = 1.0. Post-2012: Scale by alpha to match MODIS equivalent.
    cells["harmonized_count"] = np.where(
        cells["year"] < 2012,
        1.0,
        cells["month"].map(alpha_full)
    )

    # Validation (2019-2025)
    test_df = cells[(cells["year"] >= 2019) & (cells["year"] <= 2025)].copy()
    test_df["val_harmonized"] = test_df["month"].map(alpha_train)
    val_yearly = (
        test_df.groupby("year")
        .agg(
            actual_modis=("has_modis", "sum"),
            raw_total=("raw_detections", "sum"),
            predicted_harmonized=("val_harmonized", "sum"),
        )
        .reset_index()
    )
    val_yearly["predicted_harmonized"] = val_yearly["predicted_harmonized"].round(1)

    # Build JSON Payload
    regions_payload = {}
    for region in PROVINCES:
        sub = cells if region == "All Pakistan" else cells[cells["province"] == region]

        monthly = (
            sub.groupby(["year", "month"])
            .agg(
                raw=("raw_detections", "sum"),
                harmonized=("harmonized_count", "sum"),
                mean_frp=("mean_frp", "mean"),
            )
            .reset_index()
        )
        monthly["harmonized"] = monthly["harmonized"].round(1)
        monthly["mean_frp"] = monthly["mean_frp"].fillna(0).round(1)

        hist_full = monthly[(monthly["year"] >= 2001) & (monthly["year"] <= 2025)]
        medians = hist_full.groupby("month")["harmonized"].median().round(1).to_dict()

        recent_map = (
            sub[sub["year"] >= 2025]
            .sort_values("mean_frp", ascending=False)
            .head(300)[["grid_lat", "grid_lon", "acq_date", "harmonized_count", "mean_frp", "has_modis", "has_viirs"]]
            .copy()
        )
        recent_map["acq_date"] = recent_map["acq_date"].dt.strftime("%Y-%m-%d")
        recent_map["harmonized_count"] = recent_map["harmonized_count"].round(2)
        recent_map["mean_frp"] = recent_map["mean_frp"].round(1)

        regions_payload[region] = {
            "monthly_series": monthly.to_dict(orient="records"),
            "monthly_medians": {str(k): float(v) for k, v in medians.items()},
            "map_hotspots": recent_map.to_dict(orient="records"),
        }

    final_json = {
        "metadata": {
            "total_raw_detections": int(len(df)),
            "total_harmonized_cell_days": int(len(cells)),
            "year_min": int(cells["year"].min()),
            "year_max": int(cells["year"].max()),
        },
        "validation_2019_2025": val_yearly.to_dict(orient="records"),
        "regions": regions_payload,
    }

    with open("dashboard_data.json", "w") as f:
        json.dump(final_json, f)

    print("\n=== BUILD COMPLETE ===")
    print(val_yearly.to_string(index=False))

if __name__ == "__main__":
    hist_df = load_archive_csvs()
    live_df = fetch_recent_2026()
    full_df = pd.concat([hist_df, live_df], ignore_index=True) if not live_df.empty else hist_df
    harmonize_and_export(full_df)