# from flask import Flask, request, jsonify
# from flask_cors import CORS
# import os
# import json


# def create_app():
#     app = Flask(__name__)
#     CORS(app)

#     @app.route("/", methods=["GET"])
#     def index():
#         return jsonify({"Message": "Hello, World"})

#     @app.route("/api/data", methods=["POST", "GET"])
#     def get_data():
#         if request.method == "POST":
#             id = int(request.json.get("user"))
#         else:
#             id = 2

#         directory = os.path.dirname(os.path.abspath(__file__))
#         data_path = os.path.join(directory, "../q-vercel-latency.json")

#         with open(data_path) as f:
#             data = json.load(f)

#         return data[id]

#     return app


# app = create_app()

# if __name__ == "__main__":
#     app.run(debug=True)


from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import numpy as np
import os

# Create FastAPI app instance
app = FastAPI()

# Enable CORS for all origins. Note: when allow_origins is ['*'],
# many browsers will ignore Access-Control-Allow-Credentials if
# allow_credentials is True. For a true wildcard + credentials,
# you must set allow_credentials to False or specify explicit origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# ---------- models ----------
class LatencyRequest(BaseModel):
    regions: list[str]
    threshold_ms: float


# ---------- helpers ----------
def load_telemetry():
    directory = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(directory, "../q-vercel-latency.json")

    with open(data_path) as f:
        records = json.load(f)

    grouped = {}
    for r in records:
        grouped.setdefault(r["region"], []).append(
            {"latency_ms": r["latency_ms"], "uptime": r["uptime_pct"]}
        )
    return grouped


def calc_metrics(latencies, uptimes, threshold, region=None):
    return {
        "region": region,
        "avg_latency": round(float(np.mean(latencies)), 2),
        "p95_latency": round(float(np.percentile(latencies, 95)), 2),
        "avg_uptime": round(float(np.mean(uptimes)), 2),
        "breaches": int(np.sum(np.array(latencies) > threshold)),
    }


# ---------- routes ----------
@app.get("/")
def health():
    return {"msg": "Hello, World. FastAPI on Vercel is Up!"}


@app.post("/api/latency")
def latency_metrics(body: LatencyRequest):
    telemetry = load_telemetry()
    resp = []  # Initialize resp as a list
    for reg in body.regions:
        if reg not in telemetry:
            raise HTTPException(status_code=400, detail=f"region '{reg}' not found")
        lat = [x["latency_ms"] for x in telemetry[reg]]
        upt = [x["uptime"] for x in telemetry[reg]]
        resp.append(calc_metrics(lat, upt, body.threshold_ms, region=reg))
    return {"regions": resp}
