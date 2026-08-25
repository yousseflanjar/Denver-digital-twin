   import streamlit as st
   import streamlit.components.v1 as components

   st.set_page_config(page_title="Denver GeoAI Digital Twin", layout="wide")

   st.title("🏙️ Denver GeoAI Urban Digital Twin")
   st.markdown("An interactive 2.5D digital twin of downtown Denver, combining LiDAR-derived building data with AI-driven urban indicators.")

   with open('denver_digital_twin_final.html', 'r', encoding='utf-8') as f:
       html_content = f.read()

   components.html(html_content, height=750, scrolling=True)

   st.markdown("---")
   st.markdown("**Data sources:** DRCOG LiDAR (2020), Denver Building Outlines (2022), Landsat 9, Sentinel-2, WorldPop")
