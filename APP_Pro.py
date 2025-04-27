# Solar Farm Estimator App - Streamlit Version
# Author: SaminNasr | April 2025
# Description:
# This app calculates the estimated number of rows and panels, and the total annual energy yield
# for a fixed-size solar farm based on user input (location, tilt, row spacing, panel dimensions).
# Irradiance data is pulled live from PVGIS (https://re.jrc.ec.europa.eu/pvg_tools/en/#TMY) and results are visualized.



import streamlit as st
import requests
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# ----------------------------- CONFIGURATION -----------------------------
st.set_page_config(page_title="Solar Farm Estimator", layout="centered")
st.title("🔆 Solar Farm Energy Estimator")

# ----------------------------- INTRO SECTION -----------------------------
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
with st.expander("❓ How to Use This App"):
    st.markdown("""
    This app helps you simulate and optimize solar farm layout and performance. Here's what each section does:

    - **📦 Table Structure**: Define how many panels are installed per mounting table, and how many mounts are used in each row.
    - **🔧 System Configuration**: Set technical parameters like panel power, optional override for total panels.
    - **🧮 Input Parameters**: Site-specific data like location, tilt, panel dimensions, and layout.
    - **📐 Row Spacing Range**: Define the minimum and maximum row spacing to analyze different design scenarios.
    - **📊 Output Summary**: See the result for the exact spacing you enter, including total panels, system capacity, shading loss, and energy yield.
    - **📈 Chart**: Visual comparison of how row spacing affects energy production and panel count.
    - **📘 Final Summary**: Transparent overview of methods, assumptions, and reliability of each part of the model.

    👉 Use this tool to compare design options, understand trade-offs, and support layout decisions.
    """)

# ----------------------------- USER INPUTS -----------------------------
st.header("🧮 Input Parameters")

st.subheader("🔧 System Configuration")

st.subheader("📦 Table Structure")
panels_per_mount = st.number_input("Number of Panels per Table (Mount)", value=10, step=1)
mounts_per_row = st.number_input("Number of Mounts per Row", value=5, step=1)
panel_capacity_kw = st.number_input("Panel Capacity (kW per panel)", value=0.55, step=0.01, format="%.2f")
user_defined_panels = st.number_input("Override Total Number of Panels (optional)", value=0, step=1)

col1, col2 = st.columns(2)
with col1:
    lat = st.number_input("Latitude (°N)", value=28.28, format="%.4f")
    lon = st.number_input("Longitude (°E)", value=60.00, format="%.4f")
    panel_tilt = st.number_input("Tilt Angle (°)", value=25)
    panel_height = st.number_input("Panel Height (m)", value=1.5, format="%.2f")
    panel_length = st.number_input("Panel Length (m)", value=2.0, format="%.2f")
    pr = st.number_input("Performance Ratio (0-1)", min_value=0.5, max_value=0.95, value=0.82)

with col2:
    land_length = st.number_input("Land Length (m)", value=230, format="%.1f")
    land_width = st.number_input("Land Width (m)", value=200, format="%.1f")
    panel_width = st.number_input("Panel Width (m)", value=1.1, format="%.2f")
    panel_gap = st.number_input("Gap Between Panels (m)", value=0.2, format="%.2f")

# ----------------------------- HELPER FUNCTIONS -----------------------------
def get_irradiance_from_pvgis(lat, lon):
    url = f"https://re.jrc.ec.europa.eu/api/v5_2/PVcalc?lat={lat}&lon={lon}&peakpower=1&loss=14&outputformat=json"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        annual_irradiance = data['outputs']['totals']['fixed']['E_y']
        return annual_irradiance
    except:
        return None

def critical_solar_angle(lat):
    return 90 - lat + 23.45

def shadow_length(panel_tilt, panel_len, theta_deg):
    effective_height = panel_len * math.sin(math.radians(panel_tilt))
    return effective_height / math.tan(math.radians(theta_deg))

def estimate_shading_loss(spacing, shadow):
    gcr = panel_width / spacing
    if gcr >= 0.7:
        return 0.12
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

def frange(start, stop, step):
    while start <= stop:
        yield round(start, 2)
        start += step

# تبدیل درجه به متر برای مختصات
def deg2meter(x_deg_list, y_deg_list, ref_lat=None, ref_lon=None):
    if ref_lat is None:
        ref_lat = y_deg_list[0]
    if ref_lon is None:
        ref_lon = x_deg_list[0]
    lat_factor = 111_000
    lon_factor = 111_000 * np.cos(np.radians(ref_lat))
    x_m = [(x - ref_lon) * lon_factor for x in x_deg_list]
    y_m = [(y - ref_lat) * lat_factor for y in y_deg_list]
    return x_m, y_m

def validate_polygon(coords):
    if len(coords) < 4:
        return False
    if coords[0] != coords[-1]:
        return False
    return True

def polygon_area(coords):
    x = np.array([p[0] for p in coords])
    y = np.array([p[1] for p in coords])
    return 0.5 * np.abs(np.dot(x,np.roll(y,1)) - np.dot(y,np.roll(x,1)))



# ----------------------------- USABLE LAND SETTINGS -----------------------------

st.subheader("🏗️ Land Usable Area Settings")

use_percentage = st.checkbox("Use Usable Land Percentage (%)", value=True)
use_manual_area = st.checkbox("Or Enter Usable Land Area Directly (m²)")

effective_land_area = land_length * land_width  # Default

if use_percentage:
    land_usage_percent = st.number_input("Usable Land Percentage (%)", min_value=50, max_value=100, value=90)
    effective_land_area = (land_length * land_width) * (land_usage_percent / 100)
elif use_manual_area:
    effective_land_area = st.number_input("Effective Land Area (m²)", value=int(land_length * land_width * 0.9))

# ----------------------------- COMPUTATION -----------------------------

st.subheader("📐 Define Row Spacing Range")
min_spacing = st.number_input("Minimum Row Spacing (m)", value=4.0, min_value=1.0, step=0.5)
max_spacing = st.number_input("Maximum Row Spacing (m)", value=12.0, min_value=min_spacing + 0.5, step=0.5)
row_spacings = [round(s, 2) for s in frange(min_spacing, max_spacing + 0.01, 0.1)]

irradiance = get_irradiance_from_pvgis(lat, lon)
if irradiance is None:
    st.error("Failed to retrieve irradiance data from PVGIS.")
    st.stop()

solar_angle = critical_solar_angle(lat)
shadow_len = shadow_length(panel_tilt, panel_length, solar_angle)

spacing_results = []
for spacing in row_spacings:
    rows_possible = math.floor(land_length / spacing)
    panel_spacing_width = panel_width + panel_gap
    panels_per_row = math.floor(land_width / panel_spacing_width)
    gross_panels = panels_per_row * rows_possible
    area_per_panel = spacing * panel_spacing_width
    total_area_panels = gross_panels * area_per_panel

    if total_area_panels > effective_land_area:
        correction_factor = effective_land_area / total_area_panels
        total_panels = int(gross_panels * correction_factor)
    else:
        total_panels = gross_panels

    shading_loss = estimate_shading_loss(spacing, shadow_len)
    yield_per_panel = irradiance * pr * (1 - shading_loss)
    total_energy = yield_per_panel * total_panels
    spacing_results.append((spacing, total_panels, total_energy))

# ----------------------------- OUTPUT -----------------------------

st.header("📊 Output Summary for Selected Spacing")

selected_spacing = st.number_input("Enter Exact Row Spacing (m)",
    min_value=min_spacing,
    max_value=max_spacing,
    value=min_spacing,
    step=0.01,
    format="%.2f")

rows_possible_exact = math.floor(land_length / selected_spacing)
panels_per_row_exact = mounts_per_row * panels_per_mount
total_panels_exact = int(user_defined_panels) if user_defined_panels > 0 else panels_per_row_exact * rows_possible_exact
shading_selected = estimate_shading_loss(selected_spacing, shadow_len)
yield_per_panel_exact = irradiance * panel_capacity_kw * pr * (1 - shading_selected)
total_energy_exact = yield_per_panel_exact * total_panels_exact
system_capacity_kw = total_panels_exact * panel_capacity_kw
gcr_selected = panel_width / selected_spacing if spacing_results else None

st.write(f"✅ GCR: {gcr_selected:.2f}")
st.write(f"✅ Shading Loss: {shading_selected * 100:.1f}%")
st.write(f"✅ Row Spacing: {selected_spacing:.2f} m")
st.write(f"✅ Possible Rows: {rows_possible_exact}")
st.write(f"✅ Total Panels: {total_panels_exact}")
st.write(f"⚡ System Capacity: {system_capacity_kw:.2f} kW")
st.write(f"⚡ Total Energy Output: {total_energy_exact:,.0f} kWh/year")

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

# ----------------------------- POLYGON LAND INPUT -----------------------------

st.header("🌍 Define Land by Polygon Coordinates")

with st.expander("➕ Enter Land Polygon Coordinates (X, Y)"):
    st.markdown("""
    ➡️ Define your land boundary by entering X and Y coordinates separately.
    - Enter points in order (first and last point will automatically close).
    """)

    num_points = st.number_input("Number of Points (Minimum 3)", min_value=3, value=4, step=1)

    x_coords = []
    y_coords = []

    for i in range(num_points):
        colx, coly = st.columns(2)
        with colx:
            x = st.number_input(f"Longitude {i+1} (°)", key=f"x_{i}", format="%.6f", step=0.0001)
        with coly:
            y = st.number_input(f"Latitude {i+1} (°)", key=f"y_{i}", format="%.6f", step=0.0001)
        x_coords.append(x)
        y_coords.append(y)

    x_coords.append(x_coords[0])
    y_coords.append(y_coords[0])

    x_meters, y_meters = deg2meter(x_coords, y_coords)
    land_coords = list(zip(x_meters, y_meters))

    if validate_polygon(land_coords):
        st.success("✅ Polygon coordinates are valid (after conversion).")
        land_polygon_area = polygon_area(land_coords)
        st.write(f"📐 Land Area: {land_polygon_area:.1f} m²")

        fig_poly, ax_poly = plt.subplots()
        land_array = np.array(land_coords)
        ax_poly.plot(land_array[:, 0], land_array[:, 1], 'o-', label="Land Boundary")
        ax_poly.fill(land_array[:, 0], land_array[:, 1], alpha=0.3)
        ax_poly.set_xlabel("X (m)")
        ax_poly.set_ylabel("Y (m)")
        ax_poly.set_title("Land Polygon")
        ax_poly.axis('equal')
        st.pyplot(fig_poly)
    else:
        st.error("❌ Coordinates must form a closed polygon with at least 3 sides.")
