from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import statistics
import json
from pathlib import Path

app = FastAPI()

# Comprehensive CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Request model
class RegionRequest(BaseModel):
    regions: List[str]
    threshold_ms: int


def load_telemetry_data():
    """Load telemetry data from JSON file"""
    try:
        # Try multiple possible locations
        possible_paths = [
            "q-vercel-latency.json",
            "./q-vercel-latency.json",
            "/var/task/q-vercel-latency.json",
            Path(__file__).parent.parent / "q-vercel-latency.json",
        ]

        for path in possible_paths:
            data_path = Path(path) if isinstance(path, str) else path
            if data_path.exists():
                with open(data_path, "r") as f:
                    data = json.load(f)
                    print(f"✅ Loaded {len(data)} records from {path}")
                    return data

        print("❌ q-vercel-latency.json not found in any location")
        return []

    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return []


def calculate_percentile(data: List[float], percentile: float) -> float:
    """Calculate percentile from list of values"""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    index = (len(sorted_data) - 1) * percentile
    lower = int(index)
    upper = lower + 1
    weight = index - lower

    if upper >= len(sorted_data):
        return sorted_data[lower]
    return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight


# Load data
telemetry_data = load_telemetry_data()


@app.post("/api/latency")
async def get_region_metrics(request: RegionRequest):
    """Main endpoint at /api/latency"""
    print(
        f"📨 Received request: regions={request.regions}, threshold={request.threshold_ms}"
    )

    results = {}

    # Group data by region
    region_data = {}
    for record in telemetry_data:
        region = record["region"]
        if region not in region_data:
            region_data[region] = []
        region_data[region].append(record)

    for region in request.regions:
        if region not in region_data:
            # Region not found in data
            results[region] = {
                "avg_latency": 0.0,
                "p95_latency": 0.0,
                "avg_uptime": 0.0,
                "breaches": 0,
            }
            continue

        records = region_data[region]
        latencies = [record["latency_ms"] for record in records]
        uptimes = [
            record["uptime_pct"] / 100.0 for record in records
        ]  # Convert to decimal

        # Calculate metrics
        avg_latency = round(statistics.mean(latencies) if latencies else 0.0, 2)
        p95_latency = round(calculate_percentile(latencies, 0.95), 2)
        avg_uptime = round(statistics.mean(uptimes) if uptimes else 0.0, 4)
        breaches = sum(1 for latency in latencies if latency > request.threshold_ms)

        results[region] = {
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "avg_uptime": avg_uptime,
            "breaches": breaches,
        }

    print(f"📤 Returning results: {results}")

    # Create response with explicit CORS headers
    response = JSONResponse(content=results)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"

    return response


# CORS preflight handler - ESSENTIAL
@app.options("/api/latency")
async def options_latency():
    response = JSONResponse(content={"status": "ok"})
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


# Handle all OPTIONS requests
@app.options("/{rest_of_path:path}")
async def preflight_handler(request: Request, rest_of_path: str):
    response = JSONResponse(content={"status": "ok"})
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response


@app.get("/")
async def root():
    return {
        "message": "Latency Metrics API",
        "endpoint": "POST /api/latency",
        "example_request": {"regions": ["emea", "apac"], "threshold_ms": 174},
    }


@app.get("/api/latency")
async def latency_info():
    return {
        "message": "Use POST method with JSON body",
        "required_fields": ["regions", "threshold_ms"],
        "example": {"regions": ["emea", "apac"], "threshold_ms": 174},
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, debug=True)
