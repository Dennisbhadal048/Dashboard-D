import streamlit as st
import pandas as pd
import numpy as np
import os
import io
import base64
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# --- CHECK & IMPORT GIS LIBRARIES ---
try:
    import folium
    from streamlit_folium import st_folium
    import branca.colormap as cm
except ImportError:
    st.error("⚠️ Library 'folium' / 'streamlit-folium' / 'branca' belum terinstal. Jalankan: `pip install folium streamlit-folium branca`")
    st.stop()

try:
    import geopandas as gpd
except ImportError:
    st.error("⚠️ Library 'geopandas' belum terinstal untuk membaca Shapefile. Jalankan: `pip install geopandas`")
    st.stop()

try:
    import rasterio
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

# --- SETUP DIREKTORI DATA ---
GIS_DIR = os.path.join("Data", "GIS_Lanjut")
os.makedirs(GIS_DIR, exist_ok=True)

# --- FUNGSI CACHING & OPTIMASI KECEPATAN ---
@st.cache_data(show_spinner=False)
def load_shapefile(file_path):
    """Membaca Shapefile / GeoJSON dengan caching & re-proyeksi otomatis ke EPSG:4326."""
    gdf = gpd.read_file(file_path)
    if gdf.crs is not None and gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")
    return gdf

@st.cache_data(show_spinner=False)
def load_geotiff_overlay(file_path, cmap_name="turbo"):
    """
    Membaca GeoTIFF dengan optimasi downsampling ekstrem,
    mengubahnya menjadi gambar RGBA Base64 untuk overlay Folium super cepat.
    """
    with rasterio.open(file_path) as src:
        h, w = src.shape
        # Downsampling otomatis jika dimensi melebihi 1000px agar render kilat!
        step = max(1, int(max(h, w) / 1000))
        data = src.read(1, out_shape=(1, int(h // step), int(w // step)))
        bounds = src.bounds
        nodata = src.nodata

    # Masking nilai NoData & NaN
    img_data = data.copy().astype(float)
    if nodata is not None:
        img_data[img_data == nodata] = np.nan

    # Normalisasi rentang 0.0 - 1.0 untuk colormapping
    d_min, d_max = np.nanmin(img_data), np.nanmax(img_data)
    if d_max > d_min:
        norm_data = (img_data - d_min) / (d_max - d_min)
    else:
        norm_data = np.zeros_like(img_data)

    # Terapkan Colormap Matplotlib
    cmap = plt.get_cmap(cmap_name)
    rgba = cmap(norm_data) # Matriks float (H, W, 4)

    # Buat area NoData / NaN menjadi transparan total (Alpha = 0)
    rgba[np.isnan(img_data), 3] = 0.0

    # Konversi ke gambar PIL dan encode ke Base64 PNG
    rgba_uint8 = (rgba * 255).astype(np.uint8)
    img = Image.fromarray(rgba_uint8, mode="RGBA")
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    img_url = f"data:image/png;base64,{img_base64}"

    # Format bounds untuk Folium: [[lat_min, lon_min], [lat_max, lon_max]]
    folium_bounds = [[bounds.bottom, bounds.left], [bounds.top, bounds.right]]
    
    return img_url, folium_bounds, d_min, d_max

def get_gis_files():
    """Mengambil daftar file SHP, GeoJSON, TIF, TIFF, dan ZIP dari folder Data/GIS_Lanjut."""
    files = []
    if os.path.exists(GIS_DIR):
        for f in os.listdir(GIS_DIR):
            if f.lower().endswith((".shp", ".geojson", ".tif", ".tiff", ".zip")):
                files.append(os.path.join(GIS_DIR, f))
    return sorted(list(set(files)))

def run_proyek4():
    # --- HEADER GAYA BMKG ---
    st.markdown("""
    <div style="background: linear-gradient(135deg, #00509E 0%, #003366 100%); padding: 25px; border-radius: 12px; color: white; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px;">
        <h2 style='color: #ffffff !important; margin: 0; font-size: 2.1rem;'>🛰️ GIS Spasial Interaktif (Raster & Vektor)</h2>
        <p style='margin: 8px 0 0 0; font-size: 1rem; opacity: 0.95;'>Platform Overlay Data GeoTIFF & Shapefile Kecepatan Tinggi via Carto OpenStreetMap</p>
    </div>
    """, unsafe_allow_html=True)

    col_setting, col_map = st.columns([1.2, 2.5], gap="large")

    # ==========================================
    # 1. PANEL KIRI: PENGATURAN DATA & LAYER
    # ==========================================
    with col_setting:
        st.markdown("<h3 style='color: #00509E;'>🎛️ Kontrol Layer & Wilayah</h3>", unsafe_allow_html=True)

        # --- A. SUMBER DATA ---
        st.markdown("<div style='background-color: #f0fdf4; padding: 10px; border-radius: 6px; margin-top: 10px;'><p style='color: #15803d; margin: 0; font-weight: 600;'>📂 1. Pilih / Upload Data GIS</p></div>", unsafe_allow_html=True)
        data_source_mode = st.radio("Sumber file:", ["Folder Data/GIS_Lanjut", "Upload File Baru"], horizontal=True)

        selected_file_path = None
        file_ext = None

        if data_source_mode == "Folder Data/GIS_Lanjut":
            gis_files = get_gis_files()
            if not gis_files:
                st.warning(f"Belum ada file di folder `{GIS_DIR}`.")
            else:
                selected_file_path = st.selectbox("Pilih File Tersimpan:", gis_files)
                if selected_file_path:
                    file_ext = os.path.splitext(selected_file_path)[1].lower()
        else:
            st.caption("💡 *Tips: Untuk Shapefile (.shp), upload dalam format **.zip** yang berisi file .shp, .shx, .dbf, .prj.*")
            uploaded_file = st.file_uploader("Upload (.tif, .shp, .geojson, .zip)", type=['tif', 'tiff', 'shp', 'geojson', 'zip'])
            if uploaded_file is not None:
                save_path = os.path.join(GIS_DIR, uploaded_file.name)
                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                selected_file_path = save_path
                file_ext = os.path.splitext(save_path)[1].lower()
                st.success(f"💾 Tersimpan ke: `{save_path}`")

        # --- B. BOUNDING BOX WILAYAH (DEFAULT INDONESIA) ---
        st.markdown("<div style='background-color: #f0f9ff; padding: 10px; border-radius: 6px; margin: 15px 0 10px 0;'><p style='color: #0c4a6e; margin: 0; font-weight: 600;'>📍 2. Batas Koordinat / Bounding Box</p></div>", unsafe_allow_html=True)
        st.caption("Default fokus kotak wilayah maritim Indonesia:")
        
        c_lon1, c_lon2 = st.columns(2)
        lon_min = c_lon1.number_input("Min Lon (West)", value=95.0, step=1.0, format="%.2f")
        lon_max = c_lon2.number_input("Max Lon (East)", value=140.0, step=1.0, format="%.2f")
        
        c_lat1, c_lat2 = st.columns(2)
        lat_min = c_lat1.number_input("Min Lat (South)", value=-15.0, step=1.0, format="%.2f")
        lat_max = c_lat2.number_input("Max Lat (North)", value=15.0, step=1.0, format="%.2f")

        auto_zoom_box = st.checkbox("🎯 Auto-Fit Zoom ke Bounding Box ini", value=True)

        # --- C. PENGATURAN TAMPILAN LAYER & COLORBAR ---
        st.markdown("<div style='background-color: #fef3c7; padding: 10px; border-radius: 6px; margin: 15px 0 10px 0;'><p style='color: #78350f; margin: 0; font-weight: 600;'>🎨 3. Gaya Basemap & Overlay</p></div>", unsafe_allow_html=True)
        
        basemap_choice = st.selectbox("Pilih Basemap Latar:", [
            "CartoDB positron (Clean Putih/Abu BMKG)",
            "OpenStreetMap (Standar Klasik)",
            "CartoDB dark_matter (Mode Gelap)"
        ], index=0)

        layer_opacity = st.slider("Transparansi Layer (Opacity):", 0.1, 1.0, 0.8, 0.05)

        # Pengaturan khusus jika file yang dipilih adalah Raster / GeoTIFF
        cmap_choice = "turbo"
        legend_title = "Nilai Parameter Raster"
        if file_ext in [".tif", ".tiff"]:
            cmap_choice = st.selectbox("Palet Warna Raster (Colormap):", [
                "turbo", "jet", "viridis", "RdYlBu_r", "Blues", "Spectral_r", "YlGnBu"
            ], index=0)
            legend_title = st.text_input("Judul Legenda / Satuan (Colorbar):", "Curah Hujan (mm) / Suhu (°C)")

        # Pengaturan khusus jika file yang dipilih adalah Shapefile
        shp_color = "#00509E"
        if file_ext in [".shp", ".geojson", ".zip"]:
            shp_color = st.color_picker("Warna Vektor Poligon/Garis:", "#00509E")

    # ==========================================
    # 2. PANEL KANAN: PETA INTERAKTIF FOLIUM
    # ==========================================
    with col_map:
        # Inisiasi Peta Dasar Folium
        tiles_param = "OpenStreetMap"
        if "positron" in basemap_choice:
            tiles_param = "CartoDB positron"
        elif "dark_matter" in basemap_choice:
            tiles_param = "CartoDB dark_matter"

        # Titik tengah kamera awal (Indonesia)
        center_lat = (lat_min + lat_max) / 2.0
        center_lon = (lon_min + lon_max) / 2.0
        
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=5,
            tiles=tiles_param,
            control_scale=True
        )

        # Terapkan Fit Bounds jika diaktifkan
        if auto_zoom_box:
            m.fit_bounds([[lat_min, lon_min], [lat_max, lon_max]])

        # Gambar kotak batas (Bounding Box Visual Guide)
        folium.Rectangle(
            bounds=[[lat_min, lon_min], [lat_max, lon_max]],
            color="#ff0000",
            weight=1.5,
            dash_array="5, 5",
            fill=False,
            tooltip="Batas Bounding Box Aktif"
        ).add_to(m)

        # --- LOGIKA OVERLAY DATA (RASTER ATAU VEKTOR) ---
        render_success = False
        layer_legend_info = ""

        if selected_file_path and os.path.exists(selected_file_path):
            with st.spinner("⚡ Sedang memuat & merender layer GIS interaktif..."):
                try:
                    # ----------------------------------------------------
                    # A. KASUS GEOTIFF (RASTER OVERLAY + COLORBAR)
                    # ----------------------------------------------------
                    if file_ext in [".tif", ".tiff"]:
                        if not HAS_RASTERIO:
                            st.error("⚠️ Library 'rasterio' belum terinstal.")
                        else:
                            img_url, bounds, val_min, val_max = load_geotiff_overlay(selected_file_path, cmap_name=cmap_choice)
                            
                            # 1. Tambahkan ImageOverlay ke Folium
                            folium.raster_layers.ImageOverlay(
                                image=img_url,
                                bounds=bounds,
                                opacity=layer_opacity,
                                name=f"Raster: {os.path.basename(selected_file_path)}",
                                interactive=True,
                                cross_origin=False,
                                zindex=1
                            ).add_to(m)
                            
                            # 2. Buat Colorbar (cbar) Interaktif via Branca Colormap
                            cmap_obj = plt.get_cmap(cmap_choice)
                            # Sampling 20 warna dari colormap agar transisi mulus
                            hex_colors = [mcolors.to_hex(cmap_obj(i)) for i in np.linspace(0, 1, 20)]
                            
                            colorbar = cm.LinearColormap(
                                colors=hex_colors,
                                vmin=val_min,
                                vmax=val_max
                            )
                            colorbar.caption = legend_title
                            m.add_child(colorbar) # Tambahkan colorbar ke peta Folium
                            
                            # Fit bounds kamera langsung ke extent citra GeoTIFF tersebut
                            m.fit_bounds(bounds)
                            render_success = True
                            layer_legend_info = f"📊 **Rentang Nilai Raster:** Min = `{val_min:.2f}` | Max = `{val_max:.2f}`"

                    # ----------------------------------------------------
                    # B. KASUS SHAPEFILE / GEOJSON (VEKTOR OVERLAY)
                    # ----------------------------------------------------
                    elif file_ext in [".shp", ".geojson", ".zip"]:
                        gdf = load_shapefile(selected_file_path)
                        
                        tooltip_cols = list(gdf.columns[:min(5, len(gdf.columns))])
                        if 'geometry' in tooltip_cols:
                            tooltip_cols.remove('geometry')

                        folium.GeoJson(
                            gdf,
                            name=f"Vektor: {os.path.basename(selected_file_path)}",
                            style_function=lambda x: {
                                'fillColor': shp_color,
                                'color': '#000000',
                                'weight': 2,
                                'fillOpacity': layer_opacity
                            },
                            tooltip=folium.GeoJsonTooltip(fields=tooltip_cols) if tooltip_cols else None
                        ).add_to(m)

                        total_bounds = gdf.total_bounds # [xmin, ymin, xmax, ymax]
                        m.fit_bounds([[total_bounds[1], total_bounds[0]], [total_bounds[3], total_bounds[2]]])
                        render_success = True
                        layer_legend_info = f"🗺️ **Total Fitur Vektor Termuat:** `{len(gdf)}` poligon/garis/titik."

                except Exception as e:
                    st.error(f"❌ Gagal memuat layer data: {e}")

        # Aktifkan Layer Control (Agar user bisa menyalakan/mematikan layer)
        folium.LayerControl(collapsed=False).add_to(m)

        # Render Peta di Streamlit
        st_folium(m, width="100%", height=580, returned_objects=[])

        # Tampilkan Informasi Legenda Ringkas di Bawah Peta
        if render_success:
            st.markdown(f"""
            <div style="background-color: #ffffff; padding: 12px 18px; border-radius: 8px; border: 1px solid #cbd5e1; margin-top: 10px; display: flex; justify-content: space-between; align-items: center;">
                <div><span style="color: #00509E; font-weight: bold;">🛰️ Status Layer:</span> Termuat Aktif</div>
                <div>{layer_legend_info}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("👈 Silakan pilih atau upload file GeoTIFF (`.tif`) / Shapefile (`.zip`/`.shp`) pada panel kiri untuk melihat overlay.")

    # ==========================================
    # 3. PANEL EKSPLORASI DATA TABULAR (OPTIONAL)
    # ==========================================
    if selected_file_path and file_ext in [".shp", ".geojson", ".zip"] and render_success:
        st.markdown("---")
        with st.expander("📋 Lihat Tabel Atribut Shapefile (Attribute Table)", expanded=False):
            gdf_table = load_shapefile(selected_file_path).drop(columns=['geometry'], errors='ignore')
            st.dataframe(gdf_table, use_container_width=True)

if __name__ == "__main__":
    run_proyek4()