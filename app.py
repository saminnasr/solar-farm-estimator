# Solar Farm Estimator App - Streamlit Version
# Author: SaminNasr | April 2025
# Description:
# This app calculates the estimated number of rows and panels, and the total annual energy yield
# for a fixed-size solar farm based on user input (location, tilt, row spacing, panel dimensions).
# Irradiance data is pulled live from PVGIS (https://re.jrc.ec.europa.eu/pvg_tools/en/#TMY) and results are visualized.

import streamlit as st
import requests
import math
import matplotlib.pyplot as plt

# ----------------------------- CONFIGURATION -----------------------------
st.set_page_config(page_title="Solar Farm Estimator", layout="centered")
st.title("🔆 Solar Farm Energy Estimator")


st.markdown("""
### ☀️ Welcome to the Solar Farm Energy Estimator App
This tool helps you explore how **row spacing** and **panel layout** impact total energy production in a solar farm.

🔧 Enter your design parameters below, adjust the spacing range, and analyze how it affects:
- Number of rows and total panels
- Ground Coverage Ratio (GCR)
- Shading losses based on solar geometry
- Total energy output (using live irradiance data from PVGIS)

📈 You'll also see a dynamic chart to compare scenarios and an engineering summary at the end.

---
""")


# ----------------------------- USER INPUTS -----------------------------
st.header("🧮 Input Parameters")

col1, col2 = st.columns(2)
with col1:
    lat = st.number_input("Latitude (°N)", value=28.28, format="%.4f")
    panel_tilt = st.number_input("Tilt Angle (°)", value=25)
    panel_height = st.number_input("Panel Height (m)", value=1.5, format="%.2f")
    pr = st.number_input("Performance Ratio (0-1)", min_value=0.5, max_value=0.95, value=0.82)

with col2:
    land_length = st.number_input("Land Length (m)", value=230, format="%.1f")
    land_width = st.number_input("Land Width (m)", value=200, format="%.1f")
    panel_width = st.number_input("Panel Width (m)", value=1.1, format="%.2f")
    panel_gap = st.number_input("Gap Between Panels (m)", value=0.2, format="%.2f")

panel_area = 2.0  # m^2 per panel

# ----------------------------- HELPER FUNCTIONS -----------------------------

def get_irradiance_from_pvgis(lat):
    url = f"https://re.jrc.ec.europa.eu/api/v5_2/PVcalc?lat={lat}&lon=60&peakpower=1&loss=14&outputformat=json"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        annual_irradiance = data['outputs']['totals']['fixed']['E_y']  # kWh/year per kWp
        return annual_irradiance
    except:
        return None

def critical_solar_angle(lat):
    return 90 - lat + 23.45

def shadow_length(height_m, theta_deg):
    return height_m / math.tan(math.radians(theta_deg))

def estimate_shading_loss(spacing, shadow):
    """
    Estimate shading loss based on Ground Coverage Ratio (GCR) rather than just shadow ratio.
    Source: Adapted from PVsyst and NREL shading guidelines.
    """
    gcr = panel_width / spacing  # Ground Coverage Ratio (simplified)
    if gcr >= 0.7:
        return 0.12  # High GCR → significant shading
    elif gcr >= 0.6:
        return 0.08
    elif gcr >= 0.5:
        return 0.05
    elif gcr >= 0.4:
        return 0.03
    elif gcr >= 0.3:
        return 0.015
    else:
        return 0.01

# ----------------------------- COMPUTATION -----------------------------

st.subheader("📐 Define Row Spacing Range")
min_spacing = st.number_input("Minimum Row Spacing (m)", value=4.0, min_value=1.0, step=0.5)
max_spacing = st.number_input("Maximum Row Spacing (m)", value=12.0, min_value=min_spacing + 0.5, step=0.5)

# Helper for float range
def frange(start, stop, step):
    while start <= stop:
        yield round(start, 2)
        start += step

row_spacings = [round(s, 2) for s in frange(min_spacing, max_spacing + 0.1, 1.0)]

# Helper for float range
def frange(start, stop, step):
    while start <= stop:
        yield round(start, 2)
        start += step

irradiance = get_irradiance_from_pvgis(lat)
if irradiance is None:
    st.error("Failed to retrieve irradiance data from PVGIS.")
    st.stop()

solar_angle = critical_solar_angle(lat)
shadow_len = shadow_length(panel_height, solar_angle)

  # spacing from 4 to 12 meters
spacing_results = []

for spacing in row_spacings:
    rows_possible = math.floor(land_length / spacing)
    panel_spacing_width = panel_width + panel_gap
    panels_per_row = math.floor(land_width / panel_spacing_width)
    total_panels = panels_per_row * rows_possible
    shading_loss = estimate_shading_loss(spacing, shadow_len)
    yield_per_panel = irradiance * pr * (1 - shading_loss)
    total_energy = yield_per_panel * total_panels
    spacing_results.append((spacing, total_panels, total_energy))

# ----------------------------- OUTPUT -----------------------------


st.header("📊 Output Summary for Selected Spacing")

selected_spacing = st.slider("Select Row Spacing (m)", min_value=int(min_spacing), max_value=int(max_spacing), value=int(min_spacing))
match = next((item for item in spacing_results if item[0] == selected_spacing), None)
if match:
    gcr_selected = panel_width / match[0]
    shading_selected = estimate_shading_loss(match[0], shadow_len)
    st.write(f"✅ GCR: {gcr_selected:.2f}")
    st.write(f"✅ Shading Loss: {shading_selected * 100:.1f}%")
    st.write(f"✅ Row Spacing: {match[0]} m")
    st.write(f"✅ Total Panels: {match[1]}")
    st.write(f"⚡ Total Energy Output: {match[2]:,.0f} kWh/year")

# ----------------------------- PLOT -----------------------------
st.header("📈 Energy vs. Row Spacing")

spacings = [x[0] for x in spacing_results]
total_panels = [x[1] for x in spacing_results]
total_energies = [x[2] for x in spacing_results]

fig, ax1 = plt.subplots()
ax2 = ax1.twinx()
ax1.plot(spacings, total_panels, 'g-o', label="Total Panels")
ax2.plot(spacings, total_energies, 'b-s', label="Total Energy")

ax1.set_xlabel("Row Spacing (m)")
ax1.set_ylabel("Total Panels", color='g')
ax2.set_ylabel("Total Energy (kWh/year)", color='b')
plt.title("Effect of Row Spacing on Panel Count and Energy Output")

st.pyplot(fig)
