import streamlit as st
import geopandas as gpd
import pydeck as pdk
import json

st.set_page_config(page_title="Denver GeoAI Digital Twin", layout="wide")

st.title("🏙️ Denver GeoAI Urban Digital Twin")
st.markdown("An interactive 2.5D digital twin of downtown Denver, combining LiDAR-derived building data with AI-driven urban indicators.")

@st.cache_data
def load_data():
    buildings = gpd.read_file('buildings_final.geojson')
    lst = gpd.read_file('lst_points.geojson')
    ndvi = gpd.read_file('ndvi_points.geojson')
    solar = gpd.read_file('solar_points.geojson')
    return buildings, lst, ndvi, solar

buildings, lst, ndvi, solar = load_data()

st.sidebar.header("Layer Controls")
show_lst = st.sidebar.checkbox("Show Heat Island (LST)", value=False)
show_ndvi = st.sidebar.checkbox("Show Green Space (NDVI)", value=False)
show_solar = st.sidebar.checkbox("Show Solar Potential", value=False)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Buildings analyzed:** {len(buildings)}")
st.sidebar.markdown(f"**Data source:** DRCOG LiDAR 2020, Landsat 9, Sentinel-2")

buildings_json = json.loads(buildings.to_json())

buildings_layer = pdk.Layer(
    "GeoJsonLayer",
    buildings_json,
    opacity=0.8,
    stroked=True,
    filled=True,
    extruded=True,
    wireframe=True,
    get_elevation="properties.height_m",
    get_fill_color="[255, 140 - properties.height_m/2, 0, 200]",
    get_line_color=[255, 255, 255],
    pickable=True,
)

layers = [buildings_layer]

if show_lst:
    lst_layer = pdk.Layer(
        "ScatterplotLayer",
        lst,
        get_position=["longitude", "latitude"],
        get_fill_color="[255, 255 - LST_celsius*3, 0, 160]",
        get_radius=15,
        pickable=True,
    )
    layers.append(lst_layer)

if show_ndvi:
    ndvi_layer = pdk.Layer(
        "ScatterplotLayer",
        ndvi,
        get_position=["longitude", "latitude"],
        get_fill_color="[100, NDVI*500, 50, 160]",
        get_radius=8,
        pickable=True,
    )
    layers.append(ndvi_layer)

if show_solar:
    solar_layer = pdk.Layer(
        "ScatterplotLayer",
        solar,
        get_position=["longitude", "latitude"],
        get_fill_color="[255, 200 - Solar_radiation/8000, 0, 160]",
        get_radius=10,
        pickable=True,
    )
    layers.append(solar_layer)

view_state = pdk.ViewState(
    latitude=39.7444,
    longitude=-104.9954,
    zoom=14.5,
    pitch=50,
    bearing=0,
)

st.pydeck_chart(pdk.Deck(
    layers=layers,
    initial_view_state=view_state,
    map_style="dark",
    tooltip={"text": "Height: {properties.height_m} m\nType: {properties.building_type}"}
))

st.markdown("---")
st.markdown("**Data sources:** DRCOG LiDAR (2020), Denver Building Outlines (2022), Landsat 9, Sentinel-2, WorldPop")
