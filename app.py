import math
import time
from typing import Dict, List, Tuple

import folium
import streamlit as st
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable, GeocoderTimedOut
from streamlit_folium import st_folium

# -------------------------
# App configuration
# -------------------------
st.set_page_config(page_title="Market Analysis Tool", page_icon="📍", layout="wide")

STATES = [
    "Select state", "Alabama (AL)", "Alaska (AK)", "Arizona (AZ)", "Arkansas (AR)",
    "California (CA)", "Colorado (CO)", "Connecticut (CT)", "Delaware (DE)",
    "Florida (FL)", "Georgia (GA)", "Hawaii (HI)", "Idaho (ID)", "Illinois (IL)",
    "Indiana (IN)", "Iowa (IA)", "Kansas (KS)", "Kentucky (KY)", "Louisiana (LA)",
    "Maine (ME)", "Maryland (MD)", "Massachusetts (MA)", "Michigan (MI)",
    "Minnesota (MN)", "Mississippi (MS)", "Missouri (MO)", "Montana (MT)",
    "Nebraska (NE)", "Nevada (NV)", "New Hampshire (NH)", "New Jersey (NJ)",
    "New Mexico (NM)", "New York (NY)", "North Carolina (NC)", "North Dakota (ND)",
    "Ohio (OH)", "Oklahoma (OK)", "Oregon (OR)", "Pennsylvania (PA)",
    "Rhode Island (RI)", "South Carolina (SC)", "South Dakota (SD)", "Tennessee (TN)",
    "Texas (TX)", "Utah (UT)", "Vermont (VT)", "Virginia (VA)", "Washington (WA)",
    "West Virginia (WV)", "Wisconsin (WI)", "Wyoming (WY)",
]

STATE_ABBREVIATIONS = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY",
}

# -------------------------
# Helper functions
# -------------------------
def circle_polygon(lon: float, lat: float, radius_m: float, points: int = 72) -> List[List[float]]:
    """Create approximate geodesic circle GeoJSON coordinates [lon, lat]."""
    earth_radius_m = 6_371_008.8
    angular_distance = radius_m / earth_radius_m
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)
    coords: List[List[float]] = []

    for bearing_deg in range(0, 360, int(360 / points)):
        bearing = math.radians(bearing_deg)
        lat2 = math.asin(
            math.sin(lat1) * math.cos(angular_distance)
            + math.cos(lat1) * math.sin(angular_distance) * math.cos(bearing)
        )
        lon2 = lon1 + math.atan2(
            math.sin(bearing) * math.sin(angular_distance) * math.cos(lat1),
            math.cos(angular_distance) - math.sin(lat1) * math.sin(lat2),
        )
        coords.append([math.degrees(lon2), math.degrees(lat2)])

    coords.append(coords[0])
    return coords


@st.cache_data(ttl=60 * 60 * 24 * 30, show_spinner=False)
def geocode_address(address: str):
    """Single user-triggered lookup via Nominatim; cached for 30 days."""
    # Public Nominatim usage guidance: no more than one request per second.
    time.sleep(1.05)
    geocoder = Nominatim(user_agent="market_analysis_tool_prototype/1.0 (user-triggered address lookup)")
    location = geocoder.geocode(address, exactly_one=True, addressdetails=True, timeout=15)
    if location is None:
        return None
    return (float(location.latitude), float(location.longitude), location.address or address)



# -------------------------
# User interface
# -------------------------
st.title("Market Analysis Tool")
st.caption("Prototype · Define a market by property address and radius")

with st.form("market_inputs"):
    st.subheader("Property / Market Inputs")
    address = st.text_input("Address", placeholder="Street address")
    city = st.text_input("City", placeholder="City")
    state_display = st.selectbox("State", STATES, index=0)
    zip_code = st.text_input("ZIP Code", placeholder="5-digit ZIP", max_chars=5)
    radius_miles = st.selectbox("Radius", [1, 3, 5], index=0, format_func=lambda x: f"{x} mile{'s' if x != 1 else ''}")
    submitted = st.form_submit_button("Map Market", type="primary")

if submitted:
    errors = []
    if not address.strip():
        errors.append("Please enter an address.")
    if not city.strip():
        errors.append("Please enter a city.")
    if state_display == "Select state":
        errors.append("Please select a state.")
    if not zip_code.strip():
        errors.append("Please enter a ZIP Code.")
    elif not zip_code.strip().isdigit() or len(zip_code.strip()) != 5:
        errors.append("ZIP Code must contain exactly 5 digits.")

    if errors:
        for error in errors:
            st.error(error)
    else:
        state_name, state_abbr = state_display.rsplit(" (", 1)
        state_abbr = state_abbr.rstrip(")")
        full_query = f"{address.strip()}, {city.strip()}, {state_abbr} {zip_code.strip()}, USA"
        with st.spinner("Looking up address…"):
            try:
                # Lookup is only triggered by the form submission and cached for repeat searches.
                result = geocode_address(full_query)
            except (GeocoderUnavailable, GeocoderTimedOut) as exc:
                result = None
                st.error("Address lookup service is temporarily unavailable. Please try again shortly.")
            except Exception as exc:
                result = None
                st.error("We couldn't complete the address lookup. Please review the details and try again.")

        if result:
            lat, lon, matched_address = result
            radius_m = radius_miles * 1609.344
            area_sq_miles = math.pi * radius_miles**2
            boundary_coordinates = circle_polygon(lon, lat, radius_m)

            # Structured output for the next stage (Census geography selection).
            market_result: Dict = {
                "input": {
                    "address": address.strip(),
                    "city": city.strip(),
                    "state": state_name,
                    "state_abbreviation": state_abbr,
                    "zip_code": zip_code.strip(),
                    "radius_miles": radius_miles,
                },
                "geocoding": {
                    "matched_address": matched_address,
                    "latitude": lat,
                    "longitude": lon,
                },
                "market_geometry": {
                    "type": "Polygon",
                    "coordinates": [boundary_coordinates],
                    "coordinate_order": "longitude, latitude (GeoJSON)",
                },
                "area_sq_miles": area_sq_miles,
                "geocoding_source": "OpenStreetMap Nominatim",
            }
            st.session_state["market_result"] = market_result
            st.session_state["market_radius_miles"] = radius_miles
            st.session_state["market_center"] = (lat, lon)
            st.session_state["market_matched_address"] = matched_address

if "market_result" in st.session_state:
    market = st.session_state["market_result"]
    lat, lon = st.session_state["market_center"]
    radius_miles = st.session_state["market_radius_miles"]
    radius_m = radius_miles * 1609.344

    st.divider()
    st.subheader("Mapped Market")
    st.success("Address located. Market boundary created.")
    st.write(f"**Matched address:** {market['geocoding']['matched_address']}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Latitude", f"{lat:.6f}")
    c2.metric("Longitude", f"{lon:.6f}")
    c3.metric("Market radius", f"{radius_miles} mile{'s' if radius_miles != 1 else ''}")
    st.caption(f"Approximate circle area: {market['area_sq_miles']:.2f} square miles")

    fmap = folium.Map(location=[lat, lon], zoom_start=12, tiles=None, control_scale=True)
    folium.TileLayer(
        tiles="OpenStreetMap",
        attr='Map data © <a href="https://openstreetmap.org">OpenStreetMap</a> contributors',
        name="OpenStreetMap",
        overlay=False,
        control=False,
    ).add_to(fmap)
    folium.Marker(
        [lat, lon],
        tooltip="Subject Property",
        popup=folium.Popup(market["geocoding"]["matched_address"], max_width=350),
        icon=folium.Icon(color="red", icon="home", prefix="fa"),
    ).add_to(fmap)
    folium.Circle(
        location=[lat, lon],
        radius=radius_m,
        color="#2367D1",
        weight=2,
        fill=True,
        fill_color="#2367D1",
        fill_opacity=0.12,
        tooltip=f"{radius_miles}-mile market radius",
    ).add_to(fmap)
    folium.GeoJson(
        market["market_geometry"],
        name="Market boundary (GeoJSON)",
        style_function=lambda feature: {"color": "#2367D1", "weight": 1, "fillOpacity": 0.03},
    ).add_to(fmap)
    folium.CircleMarker([lat, lon], radius=4, color="white", fill=True, fill_color="red", fill_opacity=1).add_to(fmap)
    fmap.fit_bounds([[lat - radius_m / 111_000, lon - radius_m / (111_000 * max(math.cos(math.radians(lat)), 0.01))],
                     [lat + radius_m / 111_000, lon + radius_m / (111_000 * max(math.cos(math.radians(lat)), 0.01))]])
    st_folium(fmap, width=None, height=600, returned_objects=[])

    # GeoJSON download for later spatial-data stage
    boundary_geojson = {
        "type": "Feature",
        "properties": {
            "address": market["geocoding"]["matched_address"],
            "radius_miles": radius_miles,
            "latitude": lat,
            "longitude": lon,
        },
        "geometry": market["market_geometry"],
    }
    import json
    st.download_button(
        "Download market boundary (GeoJSON)",
        data=json.dumps(boundary_geojson, indent=2),
        file_name="market_boundary.geojson",
        mime="application/geo+json",
    )

    with st.expander("View structured market output (for next stage)"):
        st.json(market)
