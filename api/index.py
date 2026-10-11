
import json
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI()

# Allow POST requests from any website.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

# Load the supplied telemetry data packaged with the project.
DATA_FILE = Path(__file__).resolve().parent.parent / "q-vercel-latency.json"

with open(DATA_FILE, "r", encoding="utf-8") as file:
    telemetry = json.load(file)


class AnalyticsRequest(BaseModel):
    regions: list[str]
    threshold_ms: float = Field(default=180)


def get_records():
    # Accept either a list of records or a dictionary containing records.
    if isinstance(telemetry, list):
        return telemetry

    for key in ("records", "data", "telemetry", "pings"):
        if key in telemetry and isinstance(telemetry[key], list):
            return telemetry[key]

    raise ValueError("Could not find the telemetry records in the JSON file")


@app.post("/")
def analyse(request: AnalyticsRequest):
    try:
        records = get_records()
        results = {}

        for region in request.regions:
            # Find the records belonging to this region.
            selected = [
                row for row in records
                if str(row.get("region", "")).lower() == region.lower()
            ]

            if not selected:
                raise HTTPException(
                    status_code=400,
                    detail=f"No telemetry records found for {region}"
                )

            # Adjust these field names if the supplied JSON uses different ones.
            latencies = np.array([
                float(row["latency_ms"]) for row in selected
            ])
            uptimes = np.array([
                float(row["uptime"]) for row in selected
            ])

            results[region] = {
                "avg_latency": float(np.mean(latencies)),
                "p95_latency": float(np.percentile(latencies, 95)),
                "avg_uptime": float(np.mean(uptimes)),
                "breaches": int(np.sum(latencies > request.threshold_ms)),
            }

        return results

    except HTTPException:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not process telemetry data: {exc}"
        )