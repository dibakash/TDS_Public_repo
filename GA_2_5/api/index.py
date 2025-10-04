from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import numpy as np
import os
from pathlib import Path

# Create FastAPI app instance
app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- models ----------
class LatencyRequest(BaseModel):
    regions: list[str]
    threshold_ms: float


# ---------- helpers ----------
def load_telemetry():
    """Load telemetry data with multiple path attempts for Vercel compatibility"""
    possible_paths = [
        # Vercel deployment paths
        Path("/var/task/q-vercel-latency.json"),
        Path("/var/task/api/../q-vercel-latency.json"),
        Path("./q-vercel-latency.json"),
        Path("q-vercel-latency.json"),
        # Local development paths
        Path(__file__).parent.parent / "q-vercel-latency.json",
        Path(__file__).parent / "q-vercel-latency.json",
    ]

    for path in possible_paths:
        try:
            if path.exists():
                with open(path, "r") as f:
                    records = json.load(f)
                print(f"✅ Successfully loaded data from: {path}")

                # Group by region
                grouped = {}
                for r in records:
                    grouped.setdefault(r["region"], []).append(
                        {"latency_ms": r["latency_ms"], "uptime": r["uptime_pct"]}
                    )
                return grouped
        except Exception as e:
            print(f"❌ Failed to load from {path}: {e}")
            continue

    # If no file found, return empty with available files info
    current_dir = Path(__file__).parent
    parent_dir = current_dir.parent
    print(f"Current directory contents: {list(current_dir.glob('*'))}")
    print(f"Parent directory contents: {list(parent_dir.glob('*'))}")

    raise Exception("q-vercel-latency.json not found in any location")


def calc_metrics(latencies, uptimes, threshold, region=None):
    return {
        "region": region,
        "avg_latency": round(float(np.mean(latencies)), 2),
        "p95_latency": round(float(np.percentile(latencies, 95)), 2),
        "avg_uptime": round(float(np.mean(uptimes)), 2),
        "breaches": int(np.sum(np.array(latencies) > threshold)),
    }


# Load data at startup (or handle errors gracefully)
try:
    telemetry_data = load_telemetry()
    available_regions = list(telemetry_data.keys())
    print(f"✅ Available regions: {available_regions}")
except Exception as e:
    print(f"❌ Failed to load telemetry data: {e}")
    telemetry_data = {}
    available_regions = []


# ---------- routes ----------
@app.get("/")
def check_status():
    return {
        "msg": "FastAPI on Vercel is working",
        "available_regions": available_regions,
        "endpoint": "POST /api/latency",
    }


@app.post("/api/latency")
def latency_metrics(body: LatencyRequest):
    try:
        # Reload data on each request to ensure freshness
        telem = load_telemetry()
        resp = []

        for reg in body.regions:
            if reg not in telem:
                raise HTTPException(
                    status_code=400,
                    detail=f"region '{reg}' not found. Available regions: {list(telem.keys())}",
                )

            lat = [x["latency_ms"] for x in telem[reg]]
            upt = [x["uptime"] for x in telem[reg]]
            resp.append(calc_metrics(lat, upt, body.threshold_ms, region=reg))

        return {"regions": resp}

    except Exception as e:
        print(f"❌ Error in latency_metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# CORS preflight
@app.options("/api/latency")
async def options_latency():
    return {"status": "ok"}


@app.options("/{rest_of_path:path}")
async def preflight_handler():
    return {"status": "ok"}
