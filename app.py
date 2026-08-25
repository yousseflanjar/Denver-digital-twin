import streamlit as st
import geopandas as gpd
import pydeck as pdk
import json

st.set_page_config(page_title="Denver GeoAI Digital Twin", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main .block-container {padding-top: 2rem;}
    </style>
""", unsafe_allow_html=True)

st.title("🏙️ Denver GeoAI Urban Digital Twin")
st.caption("An interactive 2.5D digital twin of downtown Denver — LiDAR-derived buildings combined with AI-driven environmental indicators.")

@st.cache_data
def load_data():
    buildings = gpd.read_file('buildings_final.geojson.json')
    lst = gpd.read_file('lst_points.geojson')
    ndvi = gpd.read_file('ndvi_points.geojson')
    solar = gpd.read_file('solar_points.geojson')

    # Rename to match our expected column names
    buildings = buildings.rename(columns={'MAX': 'height_m', 'FIRST_BLDG_TYPE': 'building_type'})

    max_h = buildings['height_m'].quantile(0.98)
    buildings['color_r'] = 255
    buildings['color_g'] = (255 - (buildings['height_m'].clip(0, max_h) / max_h * 220)).astype(int)
    buildings['color_b'] = 40

    lst['color_r'] = 255
    lst['color_g'] = (255 - (lst['LST_celsius'].clip(30, 60) - 30) / 30 * 255).astype(int)
    lst['color_b'] = 60

    ndvi_min, ndvi_max = ndvi['NDVI'].quantile(0.02), ndvi['NDVI'].quantile(0.98)
    ndvi['color_g'] = (60 + (ndvi['NDVI'].clip(ndvi_min, ndvi_max) - ndvi_min) / (ndvi_max - ndvi_min) * 180).astype(int)
    ndvi['color_r'] = (150 - (ndvi['NDVI'].clip(ndvi_min, ndvi_max) - ndvi_min) / (ndvi_max - ndvi_min) * 120).astype(int)

    solar_min, solar_max = solar['Solar_radiation'].quantile(0.02), solar['Solar_radiation'].quantile(0.98)
    solar['color_r'] = 255
    solar['color_g'] = (60 + (solar['Solar_radiation'].clip(solar_min, solar_max) - solar_min) / (solar_max - solar_min) * 195).astype(int)
    solar['color_b'] = 30

    return buildings, lst, ndvi, solar

with st.spinner("Loading digital twin data..."):
    buildings, lst, ndvi, solar = load_data()

st.sidebar.header("🗺️ Layer Controls")
show_lst = st.sidebar.checkbox("🔥 Heat Island (LST)", value=False)
show_ndvi = st.sidebar.checkbox("🌳 Green Space (NDVI)", value=False)
show_solar = st.sidebar.checkbox("☀️ Solar Potential", value=False)

st.sidebar.markdown("---")
st.sidebar.metric("Buildings Analyzed", f"{len(buildings):,}")
st.sidebar.metric("Study Area", "~5 km²")
st.sidebar.caption("**Data sources:** DRCOG LiDAR 2020, Denver Building Outlines 2022, Landsat 9, Sentinel-2, WorldPop")

buildings_json = json.loads(buildings.to_json())

buildings_layer = pdk.Layer(
    "GeoJsonLayer",
    buildings_json,
    opacity=0.85,
    stroked=True,
    filled=True,
    extruded=True,
    wireframe=False,
    get_elevation="properties.height_m",
    elevation_scale=1,
    get_fill_color="[properties.color_r, properties.color_g, properties.color_b, 210]",
    get_line_color=[255, 255, 255, 80],
    line_width_min_pixels=1,
    pickable=True,
)

layers = [buildings_layer]

if show_lst:
    layers.append(pdk.Layer(
        "ScatterplotLayer",
        lst,
        get_position=["longitude", "latitude"],
        get_fill_color=["color_r", "color_g", "color_b"],
        get_radius=18,
        opacity=0.55,
        pickable=False,
    ))

if show_ndvi:
    layers.append(pdk.Layer(
        "ScatterplotLayer",
        ndvi,
        get_position=["longitude", "latitude"],
        get_fill_color=["color_r", "color_g", 60],
        get_radius=9,
        opacity=0.5,
        pickable=False,
    ))

if show_solar:
    layers.append(pdk.Layer(
        "ScatterplotLayer",
        solar,
        get_position=["longitude", "latitude"],
        get_fill_color=["color_r", "color_g", "color_b"],
        get_radius=14,
        opacity=0.5,
        pickable=False,
    ))

view_state = pdk.ViewState(
    latitude=39.7444,
    longitude=-104.9954,
    zoom=14.5,
    pitch=55,
    bearing=15,
)

st.pydeck_chart(pdk.Deck(
    layers=layers,
    initial_view_state=view_state,
    map_style="mapbox://styles/mapbox/dark-v10",
    tooltip={"html": "<b>Height:</b> {height_m} m<br/><b>Type:</b> {building_type}"}
), height=700)

st.markdown("---")
col1, col2, col3 = st.columns(3)
col1.metric("Avg. Building Height", f"{buildings['height_m'].mean():.1f} m")
col2.metric("Height Validation MAE", "2.80 m")
col3.metric("Footprint Coverage", "~31%")

st.caption("Data sources: DRCOG LiDAR (2020), Denver Building Outlines (2022), Landsat 9, Sentinel-2, WorldPop — CC BY 3.0 / Public domain")
