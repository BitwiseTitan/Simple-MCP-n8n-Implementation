# ui_app.py
import os
import json
import streamlit as st

# Import your tools & agents
from server import (
    flights_list_region_snapshot,
    flights_get_by_callsign,
    alerts_list_active,
)
from agents import traveler_agent, ops_agent, traveler_with_ops

# ------------- Page config -------------

st.set_page_config(
    page_title="Airspace Copilot",
    layout="wide",
)

st.title("✈️ Airspace Copilot")

st.caption(
    "Backed by: n8n (OpenSky snapshots) → MCP tools → Groq agents."
)

tabs = st.tabs(["Traveler View", "Ops View"])

# ------------- Traveler View -------------

with tabs[0]:
    st.subheader("Traveler View – Personal Flight Watchdog")

    callsign = st.text_input(
        "Flight callsign (e.g. PIA293, IGO562P)",
        value="PIA293",
    )
    passenger_question = st.text_area(
        "Your question",
        value="Where is my flight roughly now, and is everything normal?",
        height=80,
    )

    colA, colB = st.columns(2)
    with colA:
        run_traveler_only = st.button("Ask Traveler Agent")
    with colB:
        run_traveler_ops = st.button("Ask Traveler + Ops (coordinated)")

    # Show structured flight info
    if st.button("Fetch current flight data (tools only)"):
        with st.spinner("Looking up flight data..."):
            result = flights_get_by_callsign(callsign=callsign, region="region1")
        st.write("Tool result:")
        st.json(result)

    if run_traveler_only:
        with st.spinner("Traveler agent thinking..."):
            q = (
                f"My flight {callsign} is in region1. "
                f"{passenger_question} Please use tools if needed."
            )
            answer = traveler_agent(q)
        st.markdown("**Traveler agent answer:**")
        st.write(answer)

    if run_traveler_ops:
        with st.spinner("Traveler + Ops agents coordinating..."):
            answer = traveler_with_ops(callsign, passenger_question)
        st.markdown("**Coordinated answer (Traveler + Ops):**")
        st.write(answer)


# ------------- Ops View -------------

with tabs[1]:
    st.subheader("Ops View – Airspace Ops Copilot")

    region = st.selectbox(
        "Region",
        options=["region1"],
        index=0,
    )

    col1, col2 = st.columns(2)
    with col1:
        run_snapshot = st.button("Fetch latest snapshot")
    with col2:
        run_alerts = st.button("Analyze anomalies")

    if run_snapshot:
        with st.spinner("Fetching latest snapshot..."):
            snapshot = flights_list_region_snapshot(region=region)

        st.markdown("**Region summary**")
        st.write(
            f"Region: `{snapshot['region']}`, "
            f"snapshot time: `{snapshot['snapshot_time']}`, "
            f"flight count: `{snapshot['flight_count']}`"
        )

        flights = snapshot.get("flights", [])
        if flights:
            # Light-weight table view
            table_rows = []
            for f in flights:
                table_rows.append(
                    {
                        "callsign": (f.get("callsign") or "").strip(),
                        "icao24": f.get("icao24"),
                        "country": f.get("origin_country"),
                        "altitude_m": f.get("geo_altitude") or f.get("baro_altitude"),
                        "speed_mps": f.get("velocity"),
                        "on_ground": f.get("on_ground"),
                    }
                )
            st.dataframe(table_rows, use_container_width=True)
        else:
            st.info("No flights in snapshot.")

    if run_alerts:
        with st.spinner("Running anomaly checks..."):
            alert_result = alerts_list_active(region=region)

        st.markdown("**Anomalies detected**")
        st.write(
            f"Region: `{alert_result['region']}`, "
            f"Alerts: `{alert_result['alert_count']}`"
        )

        if alert_result["alert_count"] == 0:
            st.success("No active anomalies based on simple rules.")
        else:
            rows = []
            for a in alert_result["alerts"]:
                f = a["flight"]
                rows.append(
                    {
                        "callsign": (f.get("callsign") or "").strip(),
                        "icao24": f.get("icao24"),
                        "altitude_m": f.get("geo_altitude")
                        or f.get("baro_altitude"),
                        "speed_mps": f.get("velocity"),
                        "vertical_rate": f.get("vertical_rate"),
                        "reason": a["reason"],
                        "severity": a["severity"],
                    }
                )
            st.dataframe(rows, use_container_width=True)

        # Ask the Ops agent for a textual SITREP
        if st.button("Ask Ops agent for SITREP"):
            with st.spinner("Ops agent analyzing region..."):
                question = (
                    "Give me a concise situation report for this region. "
                    "Summarize traffic levels and any anomalies, and highlight "
                    "the most critical flight."
                )
                answer = ops_agent(question)
            st.markdown("**Ops agent answer:**")
            st.write(answer)
