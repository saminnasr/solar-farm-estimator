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
import matplotlib.patches as patches
import numpy as np
from shapely.geometry import  Polygon, Point, box
from shapely.errors import TopologicalError

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

def get_irradiance_from_pvgis(lat):
    url = f"https://re.jrc.ec.europa.eu/api/v5_2/PVcalc?lat={lat}&lon=60&peakpower=1&loss=14&outputformat=json"
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

irradiance = get_irradiance_from_pvgis(lat)
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

selected_spacing = st.number_input(
    "Enter Exact Row Spacing (m)",
    min_value=min_spacing,
    max_value=max_spacing,
    value=min_spacing,
    step=0.01,
    format="%.2f"
)

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
st.write(f"✅ Possible Rows: {rows_possible_exact} ")
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

# ----------------------------- LAYOUT ESTIMATOR -----------------------------

st.header("🧱 Layout Estimator: Panel & Row Count by Geometry")

st.subheader("📏 Layout Inputs")
col_layout1, col_layout2 = st.columns(2)

with col_layout1:
    layout_land_length = st.number_input("Layout Land Length (m)", value=230.0, format="%.1f")
    layout_panel_length = st.number_input("Panel Length (m)", value=2.0, format="%.2f", key="layout_panel_length")
    layout_row_spacing = st.number_input("Row Spacing (m)", value=8.0, format="%.2f", key="layout_row_spacing")

with col_layout2:
    layout_land_width = st.number_input("Layout Land Width (m)", value=200.0, format="%.1f")
    layout_panel_width = st.number_input("Panel Width (m)", value=1.1, format="%.2f", key="layout_panel_width")
    layout_panel_gap = st.number_input("Gap Between Panels (Width) (m)", value=0.2, format="%.2f")

panels_per_row_layout = math.floor(layout_land_width / (layout_panel_width + layout_panel_gap))
rows_possible_layout = math.floor(layout_land_length / layout_row_spacing)
total_panels_layout = panels_per_row_layout * rows_possible_layout

st.subheader("📊 Layout Output")
st.write(f"✅ Panels per Row: {panels_per_row_layout}")
st.write(f"✅ Rows Possible: {rows_possible_layout}")
st.write(f"✅ Total Panels by Layout: {total_panels_layout}")

# ----------------------------- POLYGON LAND INPUT -----------------------------
def latlon_to_meters(lat, lon, lat0, lon0):
    R = 6378137 
    dlat = np.radians(lat - lat0)
    dlon = np.radians(lon - lon0)
    x = R * dlon * np.cos(np.radians(lat0))
    y = R * dlat
    return x, y

def validate_polygon(coords):
    if len(coords) < 4:
        return False
    if coords[0] != coords[-1]:
        return False
    return True

def polygon_area(coords):
    x = np.array([p[0] for p in coords])
    y = np.array([p[1] for p in coords])
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))



st.header("🌍 Define Land by Polygon Coordinates (Geographic)")

def latlon_to_meters(lat, lon, lat0, lon0):
    R = 6378137
    dlat = np.radians(lat - lat0)
    dlon = np.radians(lon - lon0)
    x = R * dlon * np.cos(np.radians(lat0))
    y = R * dlat
    return x, y

with st.expander("➕ Enter Land Polygon Coordinates (Longitude, Latitude)"):
    num_points = st.number_input("Number of Points (Minimum 3)", min_value=3, value=4, step=1, key="num_points_poly")
    lon_coords = []
    lat_coords = []
    for i in range(num_points):
        colx, coly = st.columns(2)
        with colx:
            lon = st.number_input(f"Longitude {i+1}", key=f"lon_{i}", format="%.6f", step=0.00001)
        with coly:
            lat = st.number_input(f"Latitude {i+1}", key=f"lat_{i}", format="%.6f", step=0.00001)
        lon_coords.append(lon)
        lat_coords.append(lat)

    lon_coords.append(lon_coords[0])
    lat_coords.append(lat_coords[0])
    lat0, lon0 = lat_coords[0], lon_coords[0]

    x_coords = []
    y_coords = []
    for lon, lat in zip(lon_coords, lat_coords):
        x_m, y_m = latlon_to_meters(lat, lon, lat0, lon0)
        x_coords.append(x_m)
        y_coords.append(y_m)

original_polygon = Polygon(list(zip(x_coords, y_coords)))

if not original_polygon.is_valid or original_polygon.is_empty or len(original_polygon.exterior.coords) < 4:
    st.error("❌ Coordinates must form a closed polygon with at least 3 sides.")
else:
    land_polygon_area = original_polygon.area
    st.success("✅ Polygon coordinates are valid.")
    st.write(f"📐 Land Area: {land_polygon_area:.1f} m²")

    st.subheader("🏗️ Land Usable Area Settings (Polygon Based)")
    use_percentage_poly = st.checkbox("Use Usable Land Percentage for Polygon (%)", value=True, key="use_percentage_poly")
    use_manual_area_poly = st.checkbox("Or Enter Usable Land Area Directly (m²)", key="use_manual_area_poly")

    effective_land_area_poly = land_polygon_area
    usable_polygon = original_polygon

    if use_percentage_poly:
        land_usage_percent_poly = st.number_input("Usable Land Percentage (%)", min_value=50, max_value=100, value=90, key="land_usage_percent_poly")
        effective_land_area_poly = land_polygon_area * (land_usage_percent_poly / 100)

        def compute_offset_for_target_area(polygon, target_percent, tolerance=0.01):
            area_original = polygon.area
            target_area = area_original * target_percent / 100
            low = 0
            high = min(polygon.bounds[2] - polygon.bounds[0], polygon.bounds[3] - polygon.bounds[1]) / 2
            mid = 0
            for _ in range(30):
                mid = (low + high) / 2
                shrunk = polygon.buffer(-mid)
                if not shrunk.is_empty and shrunk.is_valid:
                    area = shrunk.area
                    if abs(area - target_area) / target_area < tolerance:
                        return mid
                    if area > target_area:
                        low = mid
                    else:
                        high = mid
            return mid

        try:
            offset = compute_offset_for_target_area(original_polygon, land_usage_percent_poly)
            usable_polygon = original_polygon.buffer(-offset)
            if usable_polygon.is_empty or not usable_polygon.is_valid:
                usable_polygon = original_polygon
                st.warning("⚠️ Usable polygon could not be created with requested percentage. Using full land.")
        except TopologicalError:
            st.warning("⚠️ Geometry error in buffering usable area. Using full land.")

    elif use_manual_area_poly:
        effective_land_area_poly = st.number_input("Effective Land Area (m²)", value=int(land_polygon_area * 0.9), key="polygon_effective_area")

    st.subheader("🗘️ Land and Usable Area Visualization")
    fig_poly, ax_poly = plt.subplots()
    land_array = np.array(original_polygon.exterior.coords)
    usable_array = np.array(usable_polygon.exterior.coords)
    ax_poly.plot(land_array[:,0], land_array[:,1], 'o-', label="Land Boundary")
    ax_poly.fill(land_array[:,0], land_array[:,1], alpha=0.2)
    ax_poly.plot(usable_array[:,0], usable_array[:,1], 'o-', color='green', label="Usable Area")
    ax_poly.fill(usable_array[:,0], usable_array[:,1], alpha=0.3, color='green')
    ax_poly.set_xlabel("X (m)")
    ax_poly.set_ylabel("Y (m)")
    ax_poly.set_title("Land and Usable Polygon")
    ax_poly.axis('equal')
    ax_poly.legend()
    st.pyplot(fig_poly)

    st.write(f"✅ Usable Area: {usable_polygon.area:.1f} m²")

    st.subheader("📊 Panel Layout Inside Usable Area")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        panel_width = st.number_input("Panel Width (m)", value=1.0, step=0.1, key="panel_width_poly")
        panel_gap = st.number_input("Gap Between Panels (m)", value=0.5, step=0.1, key="panel_gap_poly")
    with col_p2:
        panel_height = st.number_input("Panel Height (m)", value=2.0, step=0.1, key="panel_height_poly")
        row_spacing = st.number_input("Row Spacing (m)", value=3.0, step=0.1, key="row_spacing_poly")

    panel_spacing_width = panel_width + panel_gap

    usable_minx, usable_miny, usable_maxx, usable_maxy = usable_polygon.bounds
    total_height = usable_maxy - usable_miny
    total_width = usable_maxx - usable_minx

    possible_rows = int(total_height // row_spacing)
    panels_per_row = int(total_width // panel_spacing_width)
    total_panels_possible = possible_rows * panels_per_row

    st.write(f"✅ Possible Rows: {possible_rows}")
    st.write(f"✅ Panels per Row: {panels_per_row}")

    fig_layout, ax_layout = plt.subplots()
    ax_layout.plot(usable_array[:,0], usable_array[:,1], 'o-', label="Usable Area")
    ax_layout.fill(usable_array[:,0], usable_array[:,1], alpha=0.1, color='green')

    panel_count = 0
    for row in range(possible_rows):
        y = usable_miny + row * row_spacing
        for col in range(panels_per_row):
            x = usable_minx + col * panel_spacing_width
            panel = box(x, y, x + panel_width, y + panel_height)
            if usable_polygon.contains(panel):
                ax_layout.add_patch(patches.Rectangle((x, y), panel_width, panel_height, edgecolor='black', facecolor='blue', alpha=0.6))
                panel_count += 1

    ax_layout.set_xlabel("X (m)")
    ax_layout.set_ylabel("Y (m)")
    ax_layout.set_title("Perfect Grid Layout Based on Calculated Rows")
    ax_layout.set_aspect('equal')
    ax_layout.legend()
    st.pyplot(fig_layout)

    st.success(f"✅ Panels Placed: {panel_count}")

    st.subheader("📊 Output Summary for This Polygon")
    performance_ratio = st.slider("Performance Ratio (0.5 to 0.95)", min_value=0.5, max_value=0.95, value=0.82, step=0.01, key="pr_poly")
    panel_capacity_kw = st.number_input("Panel Capacity (kW per panel)", value=0.55, step=0.01, key="p_kw_poly")
    irradiance = st.number_input("Annual Irradiance (kWh/m²/year)", value=2000, step=10, key="irr_poly")

    estimated_energy_per_panel = irradiance * panel_capacity_kw * performance_ratio
    total_energy = panel_count * estimated_energy_per_panel
    total_capacity = panel_count * panel_capacity_kw

    st.write(f"⚡ System Capacity: {total_capacity:.2f} kW")
    st.write(f"⚡ Estimated Annual Energy: {total_energy:,.0f} kWh")
