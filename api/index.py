
import json
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# Allow requests from any origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Access-Control-Allow-Origin"]
)

# Load the assignment's JSON file.
DATA_FILE = (
    Path(__file__).resolve().parent.parent
    / "q-vercel-latency.json"
)


class AnalyticsRequest(BaseModel):
    regions: list[str]
    threshold_ms: float = 180


@app.post("/")
def analytics(request: AnalyticsRequest):
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            records = json.load(f)

        results = {}

        for region in request.regions:
            selected = [
                row for row in records
                if row["region"].lower() == region.lower()
            ]

            if not selected:
                raise HTTPException(
                    status_code=400,
                    detail=f"No records found for region: {region}",
                )

            latencies = np.array([
                float(row["latency_ms"]) for row in selected
            ])

            uptimes = np.array([
                float(row["uptime_pct"]) for row in selected
            ])

            results[region] = {
                "avg_latency": float(np.mean(latencies)),
                "p95_latency": float(np.percentile(latencies, 95)),
                "avg_uptime": float(np.mean(uptimes)),
                "breaches": int(
                    np.sum(latencies > request.threshold_ms)
                ),
            }

        return results

    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="Telemetry file not found in deployment",
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid telemetry data: {exc}",
        )