    return {"matched_address": location.address, "latitude": location.latitude, "longitude": location.longitude}


def make_circle_boundary(lat, lon, radius_miles, points=72):
    """Create a geodesic approximation of a circle; GeoJSON uses lon,lat order."""
    earth_radius_m = 6_371_008.8
    distance_m = radius_miles * 1609.344
    angular_distance = distance_m / earth_radius_m
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)
    coords = []
    for i in range(points):
        bearing = 2 * math.pi * i / points
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


st.title("Market Analysis Tool")
st.caption("Define a market by location and radius to begin the analysis.")

left_col, right_col = st.columns([1, 1], gap="large")

with left_col:
    st.subheader("Market Inputs")
    with st.form("market_inputs_form"):
        address = st.text_input("Address :red[*]", placeholder="Street address")
        city = st.text_input("City :red[*]", placeholder="City")
        state = st.selectbox("State :red[*]", list(STATE_ABBREVIATIONS.keys()), index=None, placeholder="Select state")
        zip_code = st.text_input("ZIP Code :red[*]", max_chars=5, placeholder="5-digit ZIP code")
        radius_miles = st.selectbox("Market Radius (miles)", [1, 3, 5], index=1)
        submit = st.form_submit_button("Map Market", type="primary", use_container_width=True)

    if submit:
        if not all([address.strip(), city.strip(), state, zip_code.strip()]):
            st.error("Please complete all location fields.")
        elif not (zip_code.isdigit() and len(zip_code) == 5):
            st.error("Please enter a valid 5-digit ZIP code.")
        else:
            query = f"{address.strip()}, {city.strip()}, {STATE_ABBREVIATIONS[state]}, {zip_code}, USA"
            try:
                result = geocode_address(query)
                if result is None:
                    st.session_state.pop("market_result", None)
                    st.error("We couldn't find this location. Please check the address and try again.")
                else:
                    lat, lon = result["latitude"], result["longitude"]
                    boundary_coordinates = make_circle_boundary(lat, lon, radius_miles)
                    area_sq_miles = math.pi * radius_miles**2
                    st.session_state["market_result"] = {
                        "input": {
                            "address": address.strip(), "city": city.strip(), "state": state,
                            "state_abbreviation": STATE_ABBREVIATIONS[state], "zip_code": zip_code,
                            "radius_miles": radius_miles,
                        },
                        "geocoding": result,
                        "market_geometry": {
                            "type": "Polygon", "coordinates": [boundary_coordinates],
                            "coordinate_order": "longitude, latitude (GeoJSON)",
                        },
                        "area_sq_miles": area_sq_miles,
                        "geocoding_source": "OpenStreetMap Nominatim",
                    }
                    st.success("Market mapped successfully.")
            except (GeocoderUnavailable, GeocoderTimedOut):
                st.error("The geocoding service is temporarily unavailable. Please try again shortly.")
            except Exception as exc:
                st.error(f"An error occurred while mapping the market: {exc}")

with right_col:
    st.subheader("Market Output")
    market = st.session_state.get("market_result")
    if not market:
        st.info("Enter the market details on the left and click **Map Market** to see the output here.")
    else:
        geo = market["geocoding"]
        inp = market["input"]
        lat, lon = geo["latitude"], geo["longitude"]
        radius = inp["radius_miles"]

        st.markdown(f"**Matched location:** {geo['matched_address']}")
        map_obj = folium.Map(location=[lat, lon], zoom_start=12, tiles="OpenStreetMap", control_scale=True)
        folium.Marker(
            [lat, lon], tooltip="Selected property", popup=geo["matched_address"],
            icon=folium.Icon(color="red", icon="home"),
        ).add_to(map_obj)
        folium.Circle(
            location=[lat, lon], radius=radius * 1609.344, color="#2563eb", weight=2,
            fill=True, fill_color="#2563eb", fill_opacity=0.12,
            tooltip=f"{radius}-mile radius",
        ).add_to(map_obj)
        folium.GeoJson(
            {"type": "Feature", "properties": {}, "geometry": market["market_geometry"]},
            name="Market boundary", style_function=lambda _: {"color": "#2563eb", "weight": 2, "fillOpacity": 0.04},
        ).add_to(map_obj)
        bounds = [[min(c[1] for c in market["market_geometry"]["coordinates"][0]), min(c[0] for c in market["market_geometry"]["coordinates"][0])],
                  [max(c[1] for c in market["market_geometry"]["coordinates"][0]), max(c[0] for c in market["market_geometry"]["coordinates"][0])]]
        map_obj.fit_bounds(bounds)
        st_folium(map_obj, height=430, use_container_width=True, key="market_map")

        metric1, metric2, metric3, metric4 = st.columns(4)
        metric1.metric("Latitude", f"{lat:.6f}")
        metric2.metric("Longitude", f"{lon:.6f}")
        metric3.metric("Market Radius", f"{radius} mi")
        metric4.metric("Approximate Market Area", f"{market['area_sq_miles']:.2f} sq. mi.")

        geojson = {
            "type": "Feature", "properties": {
                "address": inp["address"], "city": inp["city"], "state": inp["state"],
                "zip_code": inp["zip_code"], "radius_miles": radius,
            }, "geometry": market["market_geometry"],
        }
        st.download_button(
            "Download Market Boundary (GeoJSON)", data=json.dumps(geojson, indent=2),
            file_name="market_boundary.geojson", mime="application/geo+json", use_container_width=True,
        )
