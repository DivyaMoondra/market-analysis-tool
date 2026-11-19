import json
import math
import time

import folium
import streamlit as st
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable, GeocoderTimedOut
from streamlit_folium import st_folium

st.set_page_config(
    page_title="Market Analysis Tool",
    page_icon="📍",
    layout="wide"
)

STATE_ABBREVIATIONS = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ",
    "Arkansas": "AR", "California": "CA", "Colorado": "CO",
    "Connecticut": "CT", "Delaware": "DE", "Florida": "FL",
    "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA",
    "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE",
    "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
    "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI",
    "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY"
}


# -----------------------------
# GEOCODING
# -----------------------------

@st.cache_data(ttl=60 * 60 * 24 * 30)
def geocode_address(query):

    geolocator = Nominatim(
        user_agent="market_analysis_tool_prototype/1.0"
    )

    time.sleep(1)

    location = geolocator.geocode(query, timeout=15)

    if location is None:
        return None

    return {
        "matched_address": location.address,
        "latitude": location.latitude,
        "longitude": location.longitude
    }


# -----------------------------
# CREATE MARKET CIRCLE
# -----------------------------

def make_circle_boundary(lat, lon, radius_miles, points=72):

    earth_radius_m = 6_371_008.8
    distance_m = radius_miles * 1609.344
    angular_distance = distance_m / earth_radius_m

    lat1 = math.radians(lat)
    lon1 = math.radians(lon)

    coordinates = []

    for i in range(points):

        bearing = 2 * math.pi * i / points

        lat2 = math.asin(
            math.sin(lat1) * math.cos(angular_distance)
            + math.cos(lat1) * math.sin(angular_distance)
            * math.cos(bearing)
        )

        lon2 = lon1 + math.atan2(
            math.sin(bearing) * math.sin(angular_distance)
            * math.cos(lat1),
            math.cos(angular_distance)
            - math.sin(lat1) * math.sin(lat2)
        )

        coordinates.append([
            math.degrees(lon2),
            math.degrees(lat2)
        ])

    coordinates.append(coordinates[0])

    return coordinates


# -----------------------------
# TITLE
# -----------------------------

st.title("Market Analysis Tool")

st.caption(
    "Define a market by location and radius to begin the analysis."
)


# -----------------------------
# TWO-COLUMN LAYOUT
# -----------------------------

left_col, right_col = st.columns(
    [1, 1],
    gap="large"
)


# =============================
# LEFT COLUMN - INPUTS
# =============================

with left_col:

    st.subheader("Market Inputs")

    with st.form("market_inputs_form"):

        address = st.text_input(
            "Address :red[*]",
            placeholder="Street address"
        )

        city = st.text_input(
            "City :red[*]",
            placeholder="City"
        )

        state = st.selectbox(
            "State :red[*]",
            options=list(STATE_ABBREVIATIONS.keys()),
            index=None,
            placeholder="Select state",
            format_func=lambda s: (
                f"{s} ({STATE_ABBREVIATIONS[s]})"
            )
        )

        zip_code = st.text_input(
            "ZIP Code :red[*]",
            max_chars=5,
            placeholder="5-digit ZIP code"
        )

        radius_miles = st.selectbox(
            "Market Radius (miles)",
            [1, 3, 5],
            index=1
        )

        submit = st.form_submit_button(
            "Map Market",
            type="primary",
            use_container_width=True
        )


    # -----------------------------
    # VALIDATE & PROCESS INPUTS
    # -----------------------------

    if submit:

        if not all([
            address.strip(),
            city.strip(),
            state,
            zip_code.strip()
        ]):

            st.error(
                "Please complete all required location fields."
            )

        elif not (
            zip_code.isdigit()
            and len(zip_code) == 5
        ):

            st.error(
                "Please enter a valid 5-digit ZIP code."
            )

        else:

            query = (
                f"{address.strip()}, "
                f"{city.strip()}, "
                f"{STATE_ABBREVIATIONS[state]}, "
                f"{zip_code}, USA"
            )

            try:

                result = geocode_address(query)

                if result is None:

                    st.session_state.pop(
                        "market_result",
                        None
                    )

                    st.error(
                        "We couldn't find this location. "
                        "Please check the address and try again."
                    )

                else:

                    lat = result["latitude"]
                    lon = result["longitude"]

                    boundary_coordinates = make_circle_boundary(
                        lat,
                        lon,
                        radius_miles
                    )

                    area_sq_miles = math.pi * radius_miles**2

                    st.session_state["market_result"] = {

                        "input": {
                            "address": address.strip(),
                            "city": city.strip(),
                            "state": state,
                            "state_abbreviation":
                                STATE_ABBREVIATIONS[state],
                            "zip_code": zip_code,
                            "radius_miles": radius_miles
                        },

                        "geocoding": result,

                        "market_geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                boundary_coordinates
                            ],
                            "coordinate_order":
                                "longitude, latitude (GeoJSON)"
                        },

                        "area_sq_miles": area_sq_miles,

                        "geocoding_source":
                            "OpenStreetMap Nominatim"
                    }

                    st.success(
                        "Market mapped successfully."
                    )

            except (
                GeocoderUnavailable,
                GeocoderTimedOut
            ):

                st.error(
                    "The geocoding service is temporarily "
                    "unavailable. Please try again shortly."
                )

            except Exception as exc:

                st.error(
                    f"An error occurred while mapping "
                    f"the market: {exc}"
                )


# =============================
# RIGHT COLUMN - OUTPUT
# =============================

with right_col:

    st.subheader("Market Output")

    market = st.session_state.get("market_result")

    if market is None:

        st.info(
            "Enter the market details on the left and "
            "click Map Market to see the output here."
        )

    else:

        geo = market["geocoding"]
        inp = market["input"]

        lat = geo["latitude"]
        lon = geo["longitude"]
        radius = inp["radius_miles"]


        # -----------------------------
        # MATCHED LOCATION
        # -----------------------------

        st.markdown(
            f"**Matched location:** "
            f"{geo['matched_address']}"
        )


        # -----------------------------
        # MAP
        # -----------------------------

        map_obj = folium.Map(
            location=[lat, lon],
            zoom_start=12,
            tiles="OpenStreetMap",
            control_scale=True
        )

        folium.Marker(
            [lat, lon],
            tooltip="Selected property",
            popup=geo["matched_address"],
            icon=folium.Icon(
                color="red",
                icon="home"
            )
        ).add_to(map_obj)

        folium.Circle(
            location=[lat, lon],
            radius=radius * 1609.344,
            color="#2563eb",
            weight=2,
            fill=True,
            fill_color="#2563eb",
            fill_opacity=0.12,
            tooltip=f"{radius}-mile radius"
        ).add_to(map_obj)

        folium.GeoJson(
            {
                "type": "Feature",
                "properties": {},
                "geometry": market["market_geometry"]
            },
            name="Market boundary",
            style_function=lambda _: {
                "color": "#2563eb",
                "weight": 2,
                "fillOpacity": 0.04
            }
        ).add_to(map_obj)


        # Fit map to the market boundary

        coordinates = (
            market["market_geometry"]["coordinates"][0]
        )

        bounds = [
            [
                min(c[1] for c in coordinates),
                min(c[0] for c in coordinates)
            ],
            [
                max(c[1] for c in coordinates),
                max(c[0] for c in coordinates)
            ]
        ]

        map_obj.fit_bounds(bounds)

        st_folium(
            map_obj,
            height=430,
            use_container_width=True,
            key="market_map"
        )


        # -----------------------------
        # METRICS - SINGLE ROW
        # -----------------------------

        metric_cols = st.columns(4, gap="small")

        with metric_cols[0]:
            st.caption("Latitude")
            st.write(f"{lat:.6f}")

        with metric_cols[1]:
            st.caption("Longitude")
            st.write(f"{lon:.6f}")

        with metric_cols[2]:
            st.caption("Market Radius")
            st.write(f"{radius} mi")

        with metric_cols[3]:
            st.caption("Approx. Market Area")
            st.write(
                f"{market['area_sq_miles']:.2f} sq. mi."
            )


        # -----------------------------
        # GEOJSON DOWNLOAD
        # -----------------------------

        geojson = {
            "type": "Feature",

            "properties": {
                "address": inp["address"],
                "city": inp["city"],
                "state": inp["state"],
                "state_abbreviation":
                    inp["state_abbreviation"],
                "zip_code": inp["zip_code"],
                "radius_miles": radius
            },

            "geometry": market["market_geometry"]
        }

        st.download_button(
            "Download Market Boundary (GeoJSON)",
            data=json.dumps(geojson, indent=2),
            file_name="market_boundary.geojson",
            mime="application/geo+json",
            use_container_width=True
        )
