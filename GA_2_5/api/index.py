from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict
import statistics
import json
from pathlib import Path

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request model
class RegionRequest(BaseModel):
    regions: List[str]
    threshold_ms: int


# Response model
class RegionMetrics(BaseModel):
    avg_latency: float
    p95_latency: float
    avg_uptime: float
    breaches: int


def load_telemetry_data():
    """Load telemetry data from JSON file"""
    try:
        # Try different paths
        paths_to_try = [
            Path("q-vercel-latency.json"),
            Path("./q-vercel-latency.json"),
            Path(__file__).parent.parent / "q-vercel-latency.json",
            Path("/var/task/q-vercel-latency.json"),
        ]

        for data_path in paths_to_try:
            if data_path.exists():
                with open(data_path, "r") as f:
                    data = json.load(f)
                    print(f"Loaded {len(data)} records from {data_path}")
                    return data

        print("q-vercel-latency.json not found")
        # Fallback: return some sample data for testing
        return [
            {"region": "emea", "latency_ms": 150, "uptime_pct": 99.0},
            {"region": "emea", "latency_ms": 200, "uptime_pct": 98.0},
            {"region": "apac", "latency_ms": 160, "uptime_pct": 97.0},
            {"region": "apac", "latency_ms": 190, "uptime_pct": 96.0},
        ]
    except Exception as e:
        print(f"Error loading data: {e}")
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
        f"Received request: regions={request.regions}, threshold={request.threshold_ms}"
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
            # Return zeros if region not found
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
        avg_latency = statistics.mean(latencies) if latencies else 0.0
        p95_latency = calculate_percentile(latencies, 0.95)
        avg_uptime = statistics.mean(uptimes) if uptimes else 0.0
        breaches = sum(1 for latency in latencies if latency > request.threshold_ms)

        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 4),
            "breaches": breaches,
        }

    print(f"Returning results: {results}")
    return results


# CORS preflight for /api/latency
@app.options("/api/latency")
async def options_latency():
    return JSONResponse(
        content={"message": "CORS preflight"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        },
    )


@app.get("/")
def read_root():
    return {"message": "Latency Metrics API - Use POST /api/latency"}


@app.get("/api/latency")
def get_latency_info():
    return {"message": "Use POST method with JSON body"}


# For local development
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, debug=True)
