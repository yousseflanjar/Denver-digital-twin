import streamlit as st
import geopandas as gpd
import pydeck as pdk
import pandas as pd
import numpy as np

st.set_page_config(page_title="Denver GeoAI Digital Twin", layout="wide", initial_sidebar_state="expanded")

st.title("🏙️ Denver GeoAI Urban Digital Twin")
st.caption("A GeoAI-powered decision-support tool for downtown Denver — combining validated LiDAR building data with composite urban vulnerability and opportunity indices.")

@st.cache_data
def load_data():
    buildings = gpd.read_file('buildings_enriched.geojson')
    lst = gpd.read_file('lst_points.geojson')
    ndvi = gpd.read_file('ndvi_points.geojson')
    solar = gpd.read_file('solar_points.geojson')

    def make_colors(df, col, invert=False):
        vmin, vmax = df[col].quantile(0.02), df[col].quantile(0.98)
        norm = ((df[col].clip(vmin, vmax) - vmin) / (vmax - vmin)).fillna(0)
        if invert:
            norm = 1 - norm
        df['color_r'] = (255 * norm).astype(int)
        df['color_g'] = (255 * (1 - norm)).astype(int)
        df['color_b'] = 60
        return df

    lst = make_colors(lst, 'LST_celsius')
    ndvi = make_colors(ndvi, 'NDVI', invert=True)
    solar = make_colors(solar, 'Solar_radiation')

    return buildings, lst, ndvi, solar

with st.spinner("Loading digital twin..."):
    buildings, lst, ndvi, solar = load_data()

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

st.sidebar.markdown("---")
show_lst = st.sidebar.checkbox("🔥 Overlay: Heat Island (LST)", value=False)
show_ndvi = st.sidebar.checkbox("🌳 Overlay: Green Space (NDVI)", value=False)
show_solar = st.sidebar.checkbox("☀️ Overlay: Solar Radiation", value=False)

st.sidebar.markdown("---")
top_n = st.sidebar.slider("Highlight top N priority buildings", 5, 50, 15)

col = MODES[mode]["col"]
cmap = np.array(CMAP_RANGES[MODES[mode]["cmap"]])

vmin, vmax = buildings[col].quantile(0.02), buildings[col].quantile(0.98)
norm = ((buildings[col].clip(vmin, vmax) - vmin) / (vmax - vmin)).fillna(0)
idx = (norm * (len(cmap) - 1)).astype(int).clip(0, len(cmap) - 1)
buildings['color_r'] = cmap[idx, 0]
buildings['color_g'] = cmap[idx, 1]
buildings['color_b'] = cmap[idx, 2]

ascending = mode == "Combined Livability"
priority = buildings.nsmallest(top_n, col) if ascending else buildings.nlargest(top_n, col)
priority_ids = set(priority['BUILDING_I'])
buildings['is_priority'] = buildings['BUILDING_I'].isin(priority_ids)

import json
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

if show_lst:
    layers.append(pdk.Layer("ScatterplotLayer", lst, get_position=["longitude", "latitude"],
                             get_fill_color=["color_r", "color_g", "color_b"], get_radius=18, opacity=0.45))
if show_ndvi:
    layers.append(pdk.Layer("ScatterplotLayer", ndvi, get_position=["longitude", "latitude"],
                             get_fill_color=["color_r", "color_g", "color_b"], get_radius=9, opacity=0.4))
if show_solar:
    layers.append(pdk.Layer("ScatterplotLayer", solar, get_position=["longitude", "latitude"],
                             get_fill_color=["color_r", "color_g", "color_b"], get_radius=14, opacity=0.4))

view_state = pdk.ViewState(latitude=39.7444, longitude=-104.9954, zoom=14.5, pitch=55, bearing=15)

st.pydeck_chart(pdk.Deck(
    layers=layers,
    initial_view_state=view_state,
    map_style="mapbox://styles/mapbox/dark-v10",
    tooltip={"html": "<b>{building_type}</b><br/>Height: {height_m} m<br/>Score: {" + col + "}"}
), height=650)

st.markdown(f"### 📋 Top {top_n} Priority Buildings — {mode}")
display_cols = list(dict.fromkeys(['BUILDING_I', 'height_m', 'building_type', col]))
st.dataframe(priority[display_cols].round(2), use_container_width=True)

csv = priority[display_cols].to_csv(index=False).encode('utf-8')
st.download_button("⬇️ Download this table as CSV", csv, f"{mode.replace(' ', '_')}_priority.csv", "text/csv")

st.markdown("---")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Buildings Analyzed", f"{len(buildings):,}")
c2.metric("Height Validation MAE", "2.80 m")
c3.metric("Footprint Coverage", "~31%")
c4.metric("Study Area", "~5 km²")

st.caption("Data: DRCOG LiDAR (2020, CC BY 3.0), Denver Building Outlines (2022, CC BY 3.0), Landsat 9, Sentinel-2, WorldPop, OpenStreetMap (ODbL)")
