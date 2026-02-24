# server.py
from typing import List, Optional, Dict, Any
from typing_extensions import TypedDict
from mcp.server.fastmcp import FastMCP
import requests
import os

# ---------- Types ----------

class Flight(TypedDict, total=False):
    icao24: str
    callsign: Optional[str]
    origin_country: str
    time_position: Optional[int]
    last_contact: Optional[int]
    longitude: Optional[float]
    latitude: Optional[float]
    baro_altitude: Optional[float]
    on_ground: bool
    velocity: Optional[float]
    true_track: Optional[float]
    vertical_rate: Optional[float]
    geo_altitude: Optional[float]
    squawk: Optional[str]
    spi: bool
    position_source: Optional[int]

class Snapshot(TypedDict):
    region: str
    snapshot_time: int
    fetched_at_iso: str
    flight_count: int
    flights: List[Flight]

class FlightLookupResult(TypedDict, total=False):
    region: str
    snapshot_time: int
    fetched_at_iso: str
    flight: Optional[Flight]
    message: str

class Alert(TypedDict):
    flight: Flight
    reason: str
    severity: str

class AlertResult(TypedDict):
    region: str
    snapshot_time: int
    fetched_at_iso: str
    alert_count: int
    alerts: List[Alert]


# ---------- MCP server ----------

mcp = FastMCP("Airspace Copilot", json_response=True)

# Load webhook URLs from environment variables, with defaults
REGION_WEBHOOKS: Dict[str, str] = {
    "region1": os.getenv("REGION1_WEBHOOK", "http://localhost:5678/webhook/latest-region1"),
    # add more later, e.g. "region2": os.getenv("REGION2_WEBHOOK", "http://localhost:5678/webhook/latest-region2"),
}


def _fetch_snapshot(region: str) -> Snapshot:
    """Internal helper: call n8n webhook and return latest snapshot."""
    if region not in REGION_WEBHOOKS:
        raise ValueError(f"Unknown region '{region}'. "
                         f"Known regions: {', '.join(REGION_WEBHOOKS.keys())}")

    url = REGION_WEBHOOKS[region]
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data: Dict[str, Any] = resp.json()

    # n8n already returns these fields; ensure they exist
    data.setdefault("region", region)
    data.setdefault("flight_count", len(data.get("flights", [])))

    return data  # type: ignore[return-value]


# ---------- Tools ----------

@mcp.tool()
def flights_list_region_snapshot(region: str = "region1") -> Snapshot:
    """
    Return the latest cached flight snapshot for a region.

    Use this when you need the full list of flights for a region.
    """
    snapshot = _fetch_snapshot(region)
    return snapshot


@mcp.tool()
def flights_get_by_callsign(callsign: str, region: str = "region1") -> FlightLookupResult:
    """
    Look up a single flight by callsign (e.g. 'PIA293') in the latest snapshot.
    """
    snapshot = _fetch_snapshot(region)
    target = callsign.strip().upper()

    found: Optional[Flight] = None
    for f in snapshot.get("flights", []):
        cs = (f.get("callsign") or "").strip().upper()
        if cs == target:
            found = f
            break

    if found is None:
        return {
            "region": snapshot["region"],
            "snapshot_time": snapshot["snapshot_time"],
            "fetched_at_iso": snapshot["fetched_at_iso"],
            "flight": None,
            "message": f"No flight with callsign '{callsign}' found in {region}",
        }

    return {
        "region": snapshot["region"],
        "snapshot_time": snapshot["snapshot_time"],
        "fetched_at_iso": snapshot["fetched_at_iso"],
        "flight": found,
        "message": f"Found flight {callsign} in {region}",
    }


@mcp.tool()
def alerts_list_active(region: str = "region1") -> AlertResult:
    """
    Simple anomaly detector.

    Flags flights that look suspicious based on instantaneous data:
    - Very low speed at cruise altitude
    - Very high descent / climb rates
    """
    snapshot = _fetch_snapshot(region)
    alerts: List[Alert] = []

    for f in snapshot.get("flights", []):
        v = f.get("velocity") or 0.0       # m/s
        alt = f.get("geo_altitude") or f.get("baro_altitude") or 0.0
        vr = f.get("vertical_rate") or 0.0

        reasons: List[str] = []
        severity = "info"

        # Low speed at high altitude
        if alt > 8000 and v < 100:
            reasons.append("Unusually low speed at high altitude")
            severity = "warning"

        # Very high descent or climb rates
        if vr < -20:
            reasons.append("Very high descent rate")
            severity = "warning"
        elif vr > 20:
            reasons.append("Very high climb rate")
            severity = "warning"

        if reasons:
            alerts.append({
                "flight": f,
                "reason": "; ".join(reasons),
                "severity": severity,
            })

    return {
        "region": snapshot["region"],
        "snapshot_time": snapshot["snapshot_time"],
        "fetched_at_iso": snapshot["fetched_at_iso"],
        "alert_count": len(alerts),
        "alerts": alerts,
    }


# ---------- Entry point ----------

if __name__ == "__main__":
    # Exposes HTTP endpoint at: http://localhost:8000/mcp
    mcp.run(transport="streamable-http")
