import streamlit as st
import geopandas as gpd
import pydeck as pdk
import pandas as pd
import numpy as np
import json

st.set_page_config(page_title="Denver GeoAI Digital Twin", layout="wide", initial_sidebar_state="expanded")

st.title("🏙️ Denver GeoAI Urban Digital Twin")
st.caption("A GeoAI-powered decision-support tool for downtown Denver — combining validated LiDAR building data with composite urban vulnerability and opportunity indices.")

@st.cache_data
def load_data():
    buildings = gpd.read_file('buildings_enriched.geojson')
    buildings = buildings.reset_index(drop=True)
    buildings['display_id'] = buildings.index + 1
    return buildings

with st.spinner("Loading digital twin..."):
    buildings_all = load_data()

TOTAL_BUILDINGS = len(buildings_all)

MODES = {
    "Building Height": {"col": "height_m", "desc": "Real LiDAR-derived building heights (validated: MAE 2.80m).", "cmap": "warm"},
    "Heat Vulnerability": {"col": "heat_vulnerability_score", "desc": "Priority zones for cooling interventions — combines surface heat, vegetation deficit, and population.", "cmap": "warm"},
    "Green Space Equity": {"col": "green_equity_score", "desc": "Underserved areas lacking walkable green space — combines park distance, vegetation, and population.", "cmap": "green"},
    "Solar Retrofit": {"col": "solar_retrofit_score", "desc": "Best candidates for solar panel installation — combines sun exposure and available roof area.", "cmap": "warm"},
    "Combined Livability": {"col": "livability_score", "desc": "Overall livability synthesis: heat, green access, and solar potential combined.", "cmap": "livability"},
}

CMAP_RANGES = {
    "warm": [[90, 24, 70], [144, 12, 63], [199, 0, 57], [227, 97, 28], [241, 146, 14], [255, 195, 0]],
    "green": [[29, 112, 0], [76, 153, 0], [140, 181, 0], [181, 138, 0], [140, 94, 0], [90, 46, 0]],
    "livability": [[144, 12, 63], [199, 0, 57], [241, 146, 14], [140, 181, 0], [76, 153, 0], [29, 112, 0]],
}

st.sidebar.header("🗺️ Analysis Mode")
mode = st.sidebar.radio("Select map to display:", list(MODES.keys()))
st.sidebar.caption(MODES[mode]["desc"])
col = MODES[mode]["col"]

st.sidebar.markdown("---")
top_n = st.sidebar.slider("Highlight top N priority buildings", 5, 50, 15)

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Filters")

building_types = sorted(buildings_all['building_type'].dropna().unique().tolist())
selected_types = st.sidebar.multiselect("Building type", building_types, default=building_types)

score_min = float(buildings_all[col].min())
score_max = float(buildings_all[col].max())
score_range = st.sidebar.slider(f"{mode} score range", score_min, score_max, (score_min, score_max))

buildings = buildings_all[
    buildings_all['building_type'].isin(selected_types) &
    buildings_all[col].between(score_range[0], score_range[1])
].copy()

st.sidebar.caption(f"Showing {len(buildings):,} of {TOTAL_BUILDINGS:,} buildings")

if len(buildings) == 0:
    st.warning("No buildings match the current filters. Try widening your selection in the sidebar.")
    st.stop()

cmap = np.array(CMAP_RANGES[MODES[mode]["cmap"]])
vmin, vmax = buildings[col].quantile(0.02), buildings[col].quantile(0.98)
norm = ((buildings[col].clip(vmin, vmax) - vmin) / (vmax - vmin)).fillna(0)
idx = (norm * (len(cmap) - 1)).astype(int).clip(0, len(cmap) - 1)
buildings['color_r'] = cmap[idx, 0]
buildings['color_g'] = cmap[idx, 1]
buildings['color_b'] = cmap[idx, 2]

ascending = mode == "Combined Livability"
priority = buildings.nsmallest(top_n, col) if ascending else buildings.nlargest(top_n, col)
priority_ids = set(priority['display_id'])
buildings['is_priority'] = buildings['display_id'].isin(priority_ids)

display_cols = list(dict.fromkeys(['display_id', 'height_m', 'building_type', col]))

buildings_json = json.loads(buildings.to_json())

layers = [
    pdk.Layer(
        "GeoJsonLayer",
        buildings_json,
        opacity=0.85,
        stroked=True,
        filled=True,
        extruded=True,
        wireframe=False,
        get_elevation="properties.height_m",
        get_fill_color="[properties.color_r, properties.color_g, properties.color_b, properties.is_priority ? 255 : 160]",
        get_line_color="properties.is_priority ? [255,255,255,255] : [255,255,255,40]",
        line_width_min_pixels=1,
        pickable=True,
    )
]

map_col, detail_col = st.columns([2.2, 1])

with map_col:
    map_placeholder = st.empty()
    legend_placeholder = st.container()

with detail_col:
    detail_placeholder = st.container()

st.markdown(f"### 📋 Top {top_n} Priority Buildings — {mode}")

priority_display = priority[display_cols].rename(
    columns={'display_id': 'Building #', 'height_m': 'Height (m)', 'building_type': 'Type', col: mode}
).reset_index(drop=True)

event = st.dataframe(
    priority_display.round(2),
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row"
)

view_state = pdk.ViewState(latitude=39.7444, longitude=-104.9954, zoom=14.5, pitch=55, bearing=15)
selected_building = None

selected_rows = event.selection.rows if event and event.selection else []
if selected_rows:
    selected_building = priority.reset_index(drop=True).iloc[selected_rows[0]]
    centroid = selected_building.geometry.centroid
    view_state = pdk.ViewState(latitude=centroid.y, longitude=centroid.x, zoom=18, pitch=60, bearing=15)

map_placeholder.pydeck_chart(pdk.Deck(
    layers=layers,
    initial_view_state=view_state,
    map_provider="carto",
    map_style="dark",
    tooltip={"html": "<b>Building #{display_id}</b><br/>Type: {building_type}<br/>Height: {height_m} m<br/>Score: {" + col + "}"}
), height=650)

with legend_placeholder:
    legend_cols = st.columns(6)
    legend_labels = ["Very Low", "Low", "Med-Low", "Med-High", "High", "Very High"]
    for i, (lc, label) in enumerate(zip(legend_cols, legend_labels)):
        color = cmap[i]
        lc.markdown(
            f'<div style="background-color:rgb({color[0]},{color[1]},{color[2]}); '
            f'padding:6px; border-radius:4px; text-align:center; color:white; font-size:11px;">{label}</div>',
            unsafe_allow_html=True
        )

with detail_placeholder:
    st.markdown("#### 🏢 Building Details")
    if selected_building is not None:
        st.markdown(f"**Building #{int(selected_building['display_id'])}**")
        st.markdown(f"**Type:** {selected_building['building_type']}")
        st.divider()
        st.metric("Height", f"{selected_building['height_m']:.1f} m")
        st.metric("Footprint Area", f"{selected_building['Shape_Area']:.0f} m²")
        st.metric("Volume", f"{selected_building['Volume_m3']:,.0f} m³")
        st.divider()
        st.markdown("**Scores**")
        st.progress(min(float(selected_building['heat_vulnerability_score']), 1.0), text=f"Heat Vulnerability: {selected_building['heat_vulnerability_score']:.2f}")
        st.progress(min(float(selected_building['green_equity_score']), 1.0), text=f"Green Equity Gap: {selected_building['green_equity_score']:.2f}")
        st.progress(min(float(selected_building['solar_retrofit_score']), 1.0), text=f"Solar Retrofit: {selected_building['solar_retrofit_score']:.2f}")
        st.progress(min(float(selected_building['livability_score']), 1.0), text=f"Livability: {selected_building['livability_score']:.2f}")
        st.divider()
        st.markdown("**Underlying Data**")
        st.caption(f"Surface Temp: {selected_building['lst_celsius']:.1f} °C")
        st.caption(f"NDVI: {selected_building['ndvi']:.2f}")
        st.caption(f"Distance to nearest park: {selected_building['dist_to_park_m']:.0f} m")
        st.caption(f"Nearby population estimate: {selected_building['population_nearby']:.0f}")
    else:
        st.info("👆 Click a row in the table below to see full building details here.")

csv = priority_display.to_csv(index=False).encode('utf-8')
st.download_button("⬇️ Download this table as CSV", csv, f"{mode.replace(' ', '_')}_priority.csv", "text/csv")

st.markdown("---")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Buildings Shown", f"{len(buildings):,}")
c2.metric("Height Validation MAE", "2.80 m")
c3.metric("Footprint Coverage", "~31%")
c4.metric("Study Area", "~5 km²")

st.caption("Data: DRCOG LiDAR (2020, CC BY 3.0), Denver Building Outlines (2022, CC BY 3.0), Landsat 9, Sentinel-2, WorldPop, OpenStreetMap (ODbL)")
