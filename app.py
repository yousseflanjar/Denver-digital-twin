import streamlit as st
import geopandas as gpd
from keplergl import KeplerGl
import streamlit.components.v1 as components

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

# Build map config dynamically based on checkboxes
map1 = KeplerGl(height=700)
map1.add_data(data=buildings, name='Denver Buildings')
if show_lst:
    map1.add_data(data=lst, name='Heat Island (LST)')
if show_ndvi:
    map1.add_data(data=ndvi, name='Green Space (NDVI)')
if show_solar:
    map1.add_data(data=solar, name='Solar Potential')

map1.save_to_html(file_name='temp_map.html')
with open('temp_map.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

components.html(html_content, height=700)
