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

# --- SETUP DIREKTORI DATA & SUBFOLDER ---
BASE_DATA_DIR = "Data"
DEFAULT_SUBFOLDERS = ["GIS_Lanjut", "archive", "AVI", "Cuaca_Harian"]
for sf in DEFAULT_SUBFOLDERS:
    os.makedirs(os.path.join(BASE_DATA_DIR, sf), exist_ok=True)

def get_subfolders(base_dir):
    """Mengambil daftar seluruh subfolder di dalam direktori Data/."""
    subfolders = []
    if os.path.exists(base_dir):
        for d in os.listdir(base_dir):
            full_path = os.path.join(base_dir, d)
            if os.path.isdir(full_path):
                subfolders.append(d)
    return sorted(list(set(subfolders)))

def get_files_in_folder(folder_path):
    """Mengambil daftar file SHP, GeoJSON, TIF, TIFF, ZIP, dan CSV dari folder tertentu."""
    files = []
    if os.path.exists(folder_path):
        for f in os.listdir(folder_path):
            if f.lower().endswith((".shp", ".geojson", ".tif", ".tiff", ".zip", ".csv")):
                files.append(os.path.join(folder_path, f))
    return sorted(list(set(files)))

# --- FUNGSI CACHING & DATA LOADER ---
@st.cache_data(show_spinner=False)
def load_vector_data(file_path, ext, sep=','):
    """Membaca Shapefile / GeoJSON / CSV menjadi GeoDataFrame dengan penanganan CRS naive."""
    os.environ['SHAPE_RESTORE_SHX'] = 'YES'
    
    if ext == ".csv":
        df = pd.read_csv(file_path, sep=sep)
        return df, "csv"
    else:
        gdf = gpd.read_file(file_path)
        if gdf.crs is None:
            gdf.set_crs("EPSG:4326", inplace=True)
        elif gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")
        return gdf, "vector"

@st.cache_data(show_spinner=False)
def load_geotiff_overlay(file_path, cmap_name="turbo"):
    """Membaca GeoTIFF & menghasilkan gambar RGBA Base64 untuk overlay Folium super cepat."""
    with rasterio.open(file_path) as src:
        h, w = src.shape
        step = max(1, int(max(h, w) / 1000))
        data = src.read(1, out_shape=(1, int(h // step), int(w // step)))
        bounds = src.bounds
        nodata = src.nodata

    img_data = data.copy().astype(float)
    if nodata is not None:
        img_data[img_data == nodata] = np.nan

    d_min, d_max = np.nanmin(img_data), np.nanmax(img_data)
    if d_max > d_min:
        norm_data = (img_data - d_min) / (d_max - d_min)
    else:
        norm_data = np.zeros_like(img_data)

    cmap = plt.get_cmap(cmap_name)
    rgba = cmap(norm_data)
    rgba[np.isnan(img_data), 3] = 0.0

    rgba_uint8 = (rgba * 255).astype(np.uint8)
    img = Image.fromarray(rgba_uint8, mode="RGBA")
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    img_url = f"data:image/png;base64,{img_base64}"
    folium_bounds = [[bounds.bottom, bounds.left], [bounds.top, bounds.right]]
    
    return img_url, folium_bounds, d_min, d_max

# --- GENERATOR POPUP DENGAN GRAFIK TIME-SERIES ---
def build_feature_popup_html(row, attr_cols, ts_cols, title="Informasi Fitur"):
    """Membuat HTML Popup berisi Tabel Atribut Vertikal dan Grafik Line Chart Time-Series."""
    html = f"""
    <div style="font-family: 'Segoe UI', Tahoma, sans-serif; font-size: 11px; width: 300px; max-height: 380px; overflow-y: auto;">
        <div style="background: #00509E; color: white; padding: 6px 10px; font-weight: bold; border-radius: 4px 4px 0 0; margin-bottom: 8px;">
            📌 {title}
        </div>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 12px;">
    """
    for col in attr_cols:
        val = row.get(col, "N/A")
        html += f"""
        <tr style="border-bottom: 1px solid #e2e8f0;">
            <td style="padding: 4px 6px; font-weight: 600; color: #475569; width: 45%; background: #f8fafc;">{col}</td>
            <td style="padding: 4px 6px; color: #0f172a; width: 55%;">{val}</td>
        </tr>
        """
    html += "</table>"
    
    # Generate Grafik Time-Series jika kolom temporal dipilih
    if ts_cols and len(ts_cols) > 1:
        try:
            ts_vals = [float(row[c]) for c in ts_cols]
            fig, ax = plt.subplots(figsize=(3.8, 1.8), dpi=90)
            ax.plot(ts_cols, ts_vals, marker='o', color='#00509E', linewidth=1.8, markersize=3.5, markerfacecolor='#38b69a')
            ax.set_title("📈 Tren Runtun Waktu (Time-Series)", fontsize=8.5, fontweight='bold', color='#00509E', pad=6)
            ax.tick_params(axis='x', rotation=35, labelsize=6.5)
            ax.tick_params(axis='y', labelsize=6.5)
            ax.grid(True, linestyle=':', alpha=0.6, color='#cbd5e1')
            
            # Ubah latar agar bersih
            fig.patch.set_facecolor('#f8fafc')
            ax.set_facecolor('#ffffff')
            for spine in ax.spines.values():
                spine.set_color('#cbd5e1')
                
            plt.tight_layout()
            buf = io.BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight')
            plt.close(fig)
            img_b64 = base64.b64encode(buf.getvalue()).decode()
            html += f'<div style="text-align: center; background: #f8fafc; padding: 6px; border: 1px solid #e2e8f0; border-radius: 4px;"><img src="data:image/png;base64,{img_b64}" style="width: 100%;"></div>'
        except Exception:
            html += '<div style="color: #ef4444; font-size: 10px; font-style: italic;">Gagal merender grafik time-series (pastikan nilai kolom berupa angka numerik).</div>'
            
    html += "</div>"
    return folium.Popup(html, max_width=320)

def run_proyek4():
    # --- HEADER GAYA BMKG ---
    st.markdown("""
    <div style="background: linear-gradient(135deg, #00509E 0%, #003366 100%); padding: 25px; border-radius: 12px; color: white; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px;">
        <h2 style='color: #ffffff !important; margin: 0; font-size: 2.1rem;'>🛰️ GIS Spasial Interaktif & Time-Series</h2>
        <p style='margin: 8px 0 0 0; font-size: 1rem; opacity: 0.95;'>Platform Overlay GeoTIFF, Shapefile, & CSV dengan Analisis Atribut Runtun Waktu</p>
    </div>
    """, unsafe_allow_html=True)

    col_setting, col_map = st.columns([1.3, 2.4], gap="large")

    # ==========================================
    # 1. PANEL KIRI: PENGATURAN DATA & LAYER
    # ==========================================
    with col_setting:
        st.markdown("<h3 style='color: #00509E;'>🎛️ Kontrol Layer & Direktori</h3>", unsafe_allow_html=True)

        # --- A. PEMILIHAN SUBFOLDER & SUMBER DATA ---
        st.markdown("<div style='background-color: #f0fdf4; padding: 10px; border-radius: 6px; margin-top: 10px;'><p style='color: #15803d; margin: 0; font-weight: 600;'>📂 1. Lokasi & Sumber Data</p></div>", unsafe_allow_html=True)
        
        subfolder_list = get_subfolders(BASE_DATA_DIR)
        selected_subfolder = st.selectbox("Pilih Folder Kerja (Sub-direktori):", subfolder_list, index=0)
        active_folder_path = os.path.join(BASE_DATA_DIR, selected_subfolder)

        data_source_mode = st.radio("Metode Input Data:", ["Pilih File di Folder Internal", "Upload File Baru"], horizontal=True)

        selected_file_path = None
        file_ext = None
        sep_char = ","

        if data_source_mode == "Pilih File di Folder Internal":
            gis_files = get_files_in_folder(active_folder_path)
            if not gis_files:
                st.warning(f"Belum ada file spasial/CSV di folder `{active_folder_path}`.")
            else:
                selected_file_path = st.selectbox("Pilih File Data:", gis_files)
                if selected_file_path:
                    file_ext = os.path.splitext(selected_file_path)[1].lower()
                    if file_ext == ".csv":
                        delim_label = st.selectbox("Delimiter CSV:", [", (Koma)", "; (Titik Koma)", "\\t (Tab)"], index=0)
                        sep_char = "," if "," in delim_label else (";" if ";" in delim_label else "\t")
        else:
            st.caption(f"💡 *File yang Anda upload akan langsung disimpan ke dalam folder: **`{active_folder_path}`***")
            uploaded_file = st.file_uploader("Upload File (.tif, .shp, .geojson, .zip, .csv)", type=['tif', 'tiff', 'shp', 'geojson', 'zip', 'csv'])
            if uploaded_file is not None:
                save_path = os.path.join(active_folder_path, uploaded_file.name)
                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                selected_file_path = save_path
                file_ext = os.path.splitext(save_path)[1].lower()
                st.success(f"💾 File berhasil disimpan di: `{save_path}`")
                if file_ext == ".csv":
                    delim_label = st.selectbox("Delimiter CSV Upload:", [", (Koma)", "; (Titik Koma)", "\\t (Tab)"], index=0)
                    sep_char = "," if "," in delim_label else (";" if ";" in delim_label else "\t")

        # --- B. PEMETAAN KOLOM SPASIAL & ATRIBUT (KHUSUS CSV / VEKTOR) ---
        gdf_loaded = None
        val_col, attr_cols, ts_cols = None, [], []
        lon_col, lat_col = None, None
        point_radius = 6

        if selected_file_path and os.path.exists(selected_file_path):
            if file_ext in [".shp", ".geojson", ".zip", ".csv"]:
                st.markdown("<div style='background-color: #f3e8ff; padding: 10px; border-radius: 6px; margin: 15px 0 10px 0;'><p style='color: #6b21a8; margin: 0; font-weight: 600;'>🛠️ 2. Konfigurasi Atribut & Time-Series</p></div>", unsafe_allow_html=True)
                try:
                    raw_data, data_type = load_vector_data(selected_file_path, file_ext, sep=sep_char)
                    
                    # Jika CSV, lakukan pemetaan koordinat menjadi GeoDataFrame
                    if data_type == "csv":
                        cols = list(raw_data.columns)
                        idx_lon = next((i for i, c in enumerate(cols) if any(k in str(c).lower() for k in ['lon', 'x', 'lng', 'bujur'])), 0)
                        idx_lat = next((i for i, c in enumerate(cols) if any(k in str(c).lower() for k in ['lat', 'y', 'lintang'])), min(1, len(cols)-1))
                        
                        c1, c2 = st.columns(2)
                        lon_col = c1.selectbox("Kolom Longitude (X):", cols, index=idx_lon)
                        lat_col = c2.selectbox("Kolom Latitude (Y):", cols, index=idx_lat)
                        
                        # Buat GeoDataFrame dari koordinat CSV
                        raw_data[lon_col] = pd.to_numeric(raw_data[lon_col], errors='coerce')
                        raw_data[lat_col] = pd.to_numeric(raw_data[lat_col], errors='coerce')
                        df_clean = raw_data.dropna(subset=[lon_col, lat_col]).copy()
                        gdf_loaded = gpd.GeoDataFrame(df_clean, geometry=gpd.points_from_xy(df_clean[lon_col], df_clean[lat_col]), crs="EPSG:4326")
                        st.caption(f"✔ CSV dikonversi menjadi {len(gdf_loaded)} titik spasial aktif.")
                    else:
                        gdf_loaded = raw_data
                        st.caption(f"✔ Vektor termuat: {len(gdf_loaded)} fitur spasial.")

                    # Selektor Kolom Nilai, Atribut Popup, dan Time Series
                    all_fields = [c for c in gdf_loaded.columns if c != 'geometry']
                    
                    # 1. Kolom Nilai untuk Pewarnaan
                    idx_val = next((i for i, c in enumerate(all_fields) if any(k in str(c).lower() for k in ['val', 'curah', 'suhu', 'ch', 'rr', 'temp', 'score'])), 0)
                    val_col = st.selectbox("🎨 Kolom Nilai Parameter (Untuk Warna):", ["-- Tanpa Warna Parameter --"] + all_fields, index=idx_val+1 if all_fields else 0)
                    
                    # 2. Kolom Atribut Popup Vertikal
                    default_attrs = all_fields[:min(6, len(all_fields))]
                    attr_cols = st.multiselect("📋 Kolom Atribut di Tabel Popup:", all_fields, default=default_attrs)
                    
                    # 3. Kolom Time-Series untuk Grafik
                    st.write("**📈 Kolom Runtun Waktu (Untuk Grafik Popup):**")
                    st.caption("*Pilih secara berurutan kolom yang mewakili waktu (misal: Jan, Feb, Mar atau T1, T2, T3)*")
                    ts_cols = st.multiselect("Kolom Time-Series:", all_fields, default=[])
                    
                    # Slider Ukuran Titik (Khusus Point)
                    if any(gdf_loaded.geometry.geom_type.str.contains("Point", na=False)):
                        point_radius = st.slider("⚫ Ukuran Radius Titik Stasiun:", min_value=3, max_value=15, value=6, step=1)

                except Exception as e:
                    st.error(f"❌ Gagal memvalidasi struktur data: {e}")

        # --- C. BOUNDING BOX & BASEMAP ---
        st.markdown("<div style='background-color: #f0f9ff; padding: 10px; border-radius: 6px; margin: 15px 0 10px 0;'><p style='color: #0c4a6e; margin: 0; font-weight: 600;'>📍 3. Batas Koordinat & Basemap</p></div>", unsafe_allow_html=True)
        
        # Default Indonesia
        def_lon_min, def_lon_max = 95.0, 140.0
        def_lat_min, def_lat_max = -15.0, 15.0
        
        if gdf_loaded is not None and not gdf_loaded.empty:
            tb = gdf_loaded.total_bounds # [xmin, ymin, xmax, ymax]
            def_lon_min, def_lon_max = float(tb[0])-0.2, float(tb[2])+0.2
            def_lat_min, def_lat_max = float(tb[1])-0.2, float(tb[3])+0.2

        c_lon1, c_lon2 = st.columns(2)
        lon_min = c_lon1.number_input("Min Lon (West)", value=def_lon_min, format="%.2f")
        lon_max = c_lon2.number_input("Max Lon (East)", value=def_lon_max, format="%.2f")
        
        c_lat1, c_lat2 = st.columns(2)
        lat_min = c_lat1.number_input("Min Lat (South)", value=def_lat_min, format="%.2f")
        lat_max = c_lat2.number_input("Max Lat (North)", value=def_lat_max, format="%.2f")

        auto_zoom_box = st.checkbox("🎯 Auto-Fit Zoom Kamera ke Data Aktif", value=True)

        basemap_choice = st.selectbox("Pilih Basemap Latar:", [
            "CartoDB positron (Clean Putih/Abu BMKG)",
            "OpenStreetMap (Standar Klasik)",
            "CartoDB dark_matter (Mode Gelap)"
        ], index=0)

        layer_opacity = st.slider("Transparansi Layer (Opacity):", 0.1, 1.0, 0.85, 0.05)

        cmap_choice = "turbo"
        legend_title = "Nilai Parameter"
        if file_ext in [".tif", ".tiff"] or (val_col and val_col != "-- Tanpa Warna Parameter --"):
            cmap_choice = st.selectbox("Palet Warna (Colormap):", [
                "turbo", "jet", "viridis", "RdYlBu_r", "Blues", "Spectral_r", "YlGnBu", "Reds"
            ], index=0)
            legend_title = st.text_input("Judul Legenda (Colorbar):", val_col if val_col and val_col != "-- Tanpa Warna Parameter --" else "Curah Hujan (mm) / Suhu (°C)")

    # ==========================================
    # 2. PANEL KANAN: PETA INTERAKTIF FOLIUM
    # ==========================================
    with col_map:
        tiles_param = "OpenStreetMap"
        if "positron" in basemap_choice:
            tiles_param = "CartoDB positron"
        elif "dark_matter" in basemap_choice:
            tiles_param = "CartoDB dark_matter"

        center_lat = (lat_min + lat_max) / 2.0
        center_lon = (lon_min + lon_max) / 2.0
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=6, tiles=tiles_param, control_scale=True)

        if auto_zoom_box and selected_file_path:
            m.fit_bounds([[lat_min, lon_min], [lat_max, lon_max]])

        render_success = False
        layer_legend_info = ""

        if selected_file_path and os.path.exists(selected_file_path):
            with st.spinner("⚡ Sedang merender kartografi interaktif & popup time-series..."):
                try:
                    # ----------------------------------------------------
                    # A. KASUS GEOTIFF (RASTER OVERLAY + COLORBAR)
                    # ----------------------------------------------------
                    if file_ext in [".tif", ".tiff"]:
                        if not HAS_RASTERIO:
                            st.error("⚠️ Library 'rasterio' belum terinstal.")
                        else:
                            img_url, bounds, val_min, val_max = load_geotiff_overlay(selected_file_path, cmap_name=cmap_choice)
                            
                            folium.raster_layers.ImageOverlay(
                                image=img_url, bounds=bounds, opacity=layer_opacity,
                                name=f"Raster: {os.path.basename(selected_file_path)}",
                                interactive=True, cross_origin=False, zindex=1
                            ).add_to(m)
                            
                            cmap_obj = plt.get_cmap(cmap_choice)
                            hex_colors = [mcolors.to_hex(cmap_obj(i)) for i in np.linspace(0, 1, 20)]
                            colorbar = cm.LinearColormap(colors=hex_colors, vmin=val_min, vmax=val_max)
                            colorbar.caption = legend_title
                            m.add_child(colorbar)
                            
                            m.fit_bounds(bounds)
                            render_success = True
                            layer_legend_info = f"📊 **Raster Aktif:** Rentang `{val_min:.2f}` — `{val_max:.2f}`"

                    # ----------------------------------------------------
                    # B. KASUS VEKTOR (SHP, GEOJSON, ZIP, CSV)
                    # ----------------------------------------------------
                    elif gdf_loaded is not None and not gdf_loaded.empty:
                        # Siapkan colormap jika kolom nilai dipilih
                        use_color_mapping = (val_col and val_col != "-- Tanpa Warna Parameter --" and val_col in gdf_loaded.columns)
                        colormap = None
                        if use_color_mapping:
                            # Pastikan kolom bernilai numerik
                            gdf_loaded[val_col] = pd.to_numeric(gdf_loaded[val_col], errors='coerce')
                            vmin, vmax = gdf_loaded[val_col].min(), gdf_loaded[val_col].max()
                            if pd.notna(vmin) and pd.notna(vmax) and vmin != vmax:
                                cmap_obj = plt.get_cmap(cmap_choice)
                                hex_colors = [mcolors.to_hex(cmap_obj(i)) for i in np.linspace(0, 1, 15)]
                                colormap = cm.LinearColormap(colors=hex_colors, vmin=vmin, vmax=vmax)
                                colormap.caption = legend_title
                                m.add_child(colormap)

                        # Buat Feature Group agar rapi
                        fg = folium.FeatureGroup(name=f"Vektor: {os.path.basename(selected_file_path)}")
                        
                        # Iterasi fitur untuk merender Popup Custom & Model Titik CircleMarker
                        # Batasi hingga 600 fitur untuk menjaga performa browser
                        max_render = 100000
                        for idx, row in gdf_loaded.head(max_render).iterrows():
                            geom = row.geometry
                            if geom is None or geom.is_empty:
                                continue
                            
                            # Tentukan Warna
                            fill_hex = "#00509E"
                            if use_color_mapping and colormap and pd.notna(row[val_col]):
                                fill_hex = colormap(row[val_col])

                            # Generate Popup Vertikal + Grafik Time Series
                            popup_obj = build_feature_popup_html(row, attr_cols, ts_cols, title=f"Fitur #{idx+1}")

                            # A. MODEL TITIK: CIRCLE MARKER MODERN (Anti-Black Border Clutter)
                            if geom.geom_type == 'Point':
                                folium.CircleMarker(
                                    location=[geom.y, geom.x],
                                    radius=point_radius,
                                    color="#222222",        # Garis tepi tipis abu gelap
                                    weight=0.8,
                                    fill=True,
                                    fill_color=fill_hex,
                                    fill_opacity=layer_opacity,
                                    popup=popup_obj
                                ).add_to(fg)
                            
                            # B. MODEL POLIGON & GARIS
                            else:
                                folium.GeoJson(
                                    geom.__geo_interface__,
                                    style_function=lambda x, col=fill_hex: {
                                        'fillColor': col,
                                        'color': '#1e293b',
                                        'weight': 1.2,
                                        'fillOpacity': layer_opacity
                                    },
                                    popup=popup_obj
                                ).add_to(fg)
                                
                        fg.add_to(m)
                        if len(gdf_loaded) > max_render:
                            st.warning(f"⚠️ Untuk menjaga kecepatan browser, visualisasi dibatasi pada {max_render} fitur pertama dari total {len(gdf_loaded)} data.")
                            
                        render_success = True
                        layer_legend_info = f"🗺️ **Vektor/CSV Aktif:** `{len(gdf_loaded)}` fitur spasial. *(Klik elemen di peta untuk lihat Tabel Atribut & Grafik Time-Series!)*"

                except Exception as e:
                    st.error(f"❌ Gagal memuat visualisasi peta: {e}")

        # Layer Control & Render
        folium.LayerControl(collapsed=False).add_to(m)
        st_folium(m, width="100%", height=590, returned_objects=[])

        # Status Footer
        if render_success:
            st.markdown(f"""
            <div style="background-color: #ffffff; padding: 12px 18px; border-radius: 8px; border: 1px solid #cbd5e1; margin-top: 10px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,0.04);">
                <div><span style="color: #00509E; font-weight: 800;">🛰️ STATUS RADAR:</span> Online & Ready</div>
                <div style="font-size: 0.95rem; color: #334155;">{layer_legend_info}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("👈 Silakan pilih folder dan file data pada panel pengaturan di sebelah kiri untuk menampilkan peta analisis.")

    # ==========================================
    # 3. PANEL EKSPLORASI TABULAR DI BAWAH PETA
    # ==========================================
    if gdf_loaded is not None and not gdf_loaded.empty and render_success:
        st.markdown("---")
        with st.expander("📋 Lihat Tabel Data Lengkap & Eksplorasi Nilai (Attribute Table)", expanded=False):
            df_display = gdf_loaded.drop(columns=['geometry'], errors='ignore')
            st.dataframe(df_display, use_container_width=True)
            
            # Tombol unduh kembali data yang sudah dibersihkan
            csv_buf = df_display.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ Download Tabel Atribut Sesi Ini (CSV)",
                data=csv_buf,
                file_name=f"atribut_{os.path.splitext(os.path.basename(selected_file_path))[0]}.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    run_proyek4()