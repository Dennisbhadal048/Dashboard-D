import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
import io

# --- CHECK LIBRARY CARTOPY & RASTERIO ---
try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
except ImportError:
    st.error("⚠️ Library 'cartopy' belum terinstal. Jalankan di terminal: pip install cartopy")
    st.stop()

try:
    import rasterio
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

# --- PATH DATA DEFAULT & AUTO-CREATE FOLDER ---
DATA_DIRS = ["Data/archive", "Data"]
for d in DATA_DIRS:
    os.makedirs(d, exist_ok=True)

# --- FUNGSI CACHING UNTUK KECEPATAN EKSTREM ---
@st.cache_data(show_spinner=False)
def load_csv_data(file_path, delimiter=','):
    """Membaca CSV dengan cache agar tidak reload dari disk saat ganti warna/judul."""
    return pd.read_csv(file_path, sep=delimiter)

@st.cache_data(show_spinner=False)
def load_geotiff_data(file_path):
    """Membaca GeoTIFF dengan auto-downsampling jika gambar terlalu besar agar render cepat."""
    with rasterio.open(file_path) as src:
        h, w = src.shape
        # Jika dimensi melebihi 1200px, lakukan subsampling otomatis agar super cepat!
        step = max(1, int(max(h, w) / 1200))
        
        # Baca data band 1 dengan subsampling jika diperlukan
        data = src.read(1, out_shape=(1, int(h // step), int(w // step)))
        bounds = src.bounds
        nodata = src.nodata
    return data, bounds, nodata

def get_local_files():
    """Mengambil daftar file CSV dan GeoTIFF dari folder lokal."""
    files = []
    for d in DATA_DIRS:
        if os.path.exists(d):
            for f in os.listdir(d):
                if f.lower().endswith(('.csv', '.tif', '.tiff')):
                    files.append(os.path.join(d, f))
    return sorted(list(set(files)))

def run_proyek3():
    # --- HEADER BMKG STYLE ---
    st.markdown("""
    <div style="background: linear-gradient(135deg, #00509E 0%, #003366 100%); padding: 28px; border-radius: 12px; color: white; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 22px;">
        <h2 style='color: #ffffff !important; margin: 0; font-size: 2.1rem;'>🗺️ Studio Peta Otomatis BMKG</h2>
        <p style='margin: 8px 0 0 0; font-size: 1rem; opacity: 0.95;'>Generator Peta Operasional Cepat & Akurat (Dukungan CSV Multi-Delimiter & GeoTIFF)</p>
    </div>
    """, unsafe_allow_html=True)

    col_setting, col_map = st.columns([1.2, 2.3], gap="large")

    # ==========================================
    # 1. KOLOM PENGATURAN (SIDE BAR KIRI)
    # ==========================================
    with col_setting:
        st.markdown("<h3 style='color: #00509E;'>🎛️ Pengaturan Peta & Data</h3>", unsafe_allow_html=True)
        
        # --- A. PEMILIHAN SUMBER DATA ---
        st.markdown("<div style='background-color: #f0fdf4; padding: 10px; border-radius: 6px; margin-top: 10px;'><p style='color: #15803d; margin: 0; font-weight: 600;'>📂 1. Sumber Data</p></div>", unsafe_allow_html=True)
        data_source_type = st.radio("Pilih metode input data:", ["Pilih dari Folder Lokal", "Upload File Baru"], horizontal=True)
        
        selected_file_path = None
        file_type = None
        df_csv = None
        raster_data, raster_bounds, raster_nodata = None, None, None

        # DELIMITER SELECTOR (Khusus CSV)
        delimiter_map = {", (Koma)": ",", "; (Titik Koma)": ";", "\\t (Tab)": "\t"}
        selected_delim_label = st.selectbox("Pilih Pemisah Kolom (Delimiter CSV):", list(delimiter_map.keys()), index=0)
        sep_char = delimiter_map[selected_delim_label]

        if data_source_type == "Pilih dari Folder Lokal":
            local_files = get_local_files()
            if not local_files:
                st.warning("Belum ada file di folder `Data` atau `Data/archive`.")
            else:
                selected_file_path = st.selectbox("Pilih File Tersimpan:", local_files)
                if selected_file_path:
                    file_type = "tif" if selected_file_path.lower().endswith(('.tif', '.tiff')) else "csv"
        else:
            uploaded_file = st.file_uploader("Upload file (.csv, .tif, .tiff)", type=['csv', 'tif', 'tiff'])
            if uploaded_file is not None:
                file_type = "tif" if uploaded_file.name.lower().endswith(('.tif', '.tiff')) else "csv"
                
                # --- AUTO-SAVE FILE UPLOAD KE FOLDER LOKAL ---
                save_dir = "Data/archive"
                os.makedirs(save_dir, exist_ok=True)
                save_path = os.path.join(save_dir, uploaded_file.name)
                
                # Simpan fisik file ke hard disk jika belum ada atau diperbarui
                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                selected_file_path = save_path
                st.success(f"💾 File berhasil di-upload dan otomatis tersimpan di: `{save_path}`")

        # --- PROSES PEMBACAAN DATA AWAL & AUTO BOUNDS ---
        default_lon_min, default_lon_max = 95.0, 141.0
        default_lat_min, default_lat_max = -11.0, 6.0
        
        lon_col, lat_col, val_col = None, None, None

        if selected_file_path is not None:
            if file_type == "csv":
                try:
                    # Menggunakan fungsi ber-cache dan delimiter pilihan user
                    df_csv = load_csv_data(selected_file_path, delimiter=sep_char)
                    st.info(f"✔ CSV Termuat: {df_csv.shape[0]} baris × {df_csv.shape[1]} kolom")
                    
                    # Selektor Kolom Spasial
                    st.write("**Penentuan Kolom Spasial:**")
                    cols = list(df_csv.columns)
                    
                    idx_lon = next((i for i, c in enumerate(cols) if any(k in str(c).lower() for k in ['lon', 'x', 'lng', 'bujur'])), 0)
                    idx_lat = next((i for i, c in enumerate(cols) if any(k in str(c).lower() for k in ['lat', 'y', 'lintang'])), min(1, len(cols)-1))
                    idx_val = next((i for i, c in enumerate(cols) if any(k in str(c).lower() for k in ['val', 'curah', 'hujan', 'suhu', 'temp', 'ch', 'rr', 'z'])), min(2, len(cols)-1))
                    
                    c1, c2 = st.columns(2)
                    lon_col = c1.selectbox("Kolom Longitude (X):", cols, index=idx_lon)
                    lat_col = c2.selectbox("Kolom Latitude (Y):", cols, index=idx_lat)
                    val_col = st.selectbox("Kolom Nilai / Parameter (Z):", cols, index=idx_val)

                    # Update Default Bounds dari Data CSV
                    default_lon_min, default_lon_max = float(df_csv[lon_col].min()) - 0.5, float(df_csv[lon_col].max()) + 0.5
                    default_lat_min, default_lat_max = float(df_csv[lat_col].min()) - 0.5, float(df_csv[lat_col].max()) + 0.5

                except Exception as e:
                    st.error(f"Gagal membaca CSV! Pastikan Pilihan Delimiter Anda tepat. Error: {e}")

            elif file_type == "tif":
                if not HAS_RASTERIO:
                    st.error("⚠️ Library 'rasterio' belum terinstal untuk membaca GeoTIFF. Jalankan: `pip install rasterio`")
                else:
                    try:
                        # Menggunakan fungsi ber-cache & auto-downsampling
                        raster_data, raster_bounds, raster_nodata = load_geotiff_data(selected_file_path)
                        st.info(f"✔ GeoTIFF Termuat (Grid Teroptimasi: {raster_data.shape[1]}x{raster_data.shape[0]})")
                        
                        # Update Default Bounds dari GeoTIFF
                        default_lon_min, default_lon_max = float(raster_bounds.left), float(raster_bounds.right)
                        default_lat_min, default_lat_max = float(raster_bounds.bottom), float(raster_bounds.top)
                    except Exception as e:
                        st.error(f"Gagal memuat GeoTIFF: {e}")

        # --- B. BATAS KOORDINAT (BOUNDING BOX) ---
        st.markdown("<div style='background-color: #f0f9ff; padding: 10px; border-radius: 6px; margin: 15px 0 10px 0;'><p style='color: #0c4a6e; margin: 0; font-weight: 600;'>📍 2. Batas Koordinat / Zoom (Bounding Box)</p></div>", unsafe_allow_html=True)
        col_lon1, col_lon2 = st.columns(2)
        lon_min = col_lon1.number_input("Min Lon (Batas Barat)", value=float(default_lon_min), format="%.2f")
        lon_max = col_lon2.number_input("Max Lon (Batas Timur)", value=float(default_lon_max), format="%.2f")
        
        col_lat1, col_lat2 = st.columns(2)
        lat_min = col_lat1.number_input("Min Lat (Batas Selatan)", value=float(default_lat_min), format="%.2f")
        lat_max = col_lat2.number_input("Max Lat (Batas Utara)", value=float(default_lat_max), format="%.2f")

        # --- C. GAYA VISUAL & JUDUL ---
        st.markdown("<div style='background-color: #fef3c7; padding: 10px; border-radius: 6px; margin: 15px 0 10px 0;'><p style='color: #78350f; margin: 0; font-weight: 600;'>🎨 3. Gaya Visual & Atribut</p></div>", unsafe_allow_html=True)
        
        map_title = st.text_input("Judul Utama Peta:", "PETA DISTRIBUSI SPASIAL OPERASIONAL BMKG")
        legend_title = st.text_input("Judul Legenda / Satuan:", "Curah Hujan (mm) / Suhu (°C)")
        
        cmap_choice = st.selectbox("Palette Warna (Colormap):", ["turbo", "jet", "viridis", "RdYlBu_r", "Blues", "YlGnBu", "Spectral_r"], index=0)
        
        color_mode = st.radio("Metode Rentang Warna:", ["Stretched (Kontinu)", "Classified (Diskret)"], horizontal=True)
        num_classes = 5
        if color_mode == "Classified (Diskret)":
            num_classes = st.slider("Jumlah Kelas Warna:", min_value=3, max_value=15, value=6)

    # ==========================================
    # 2. KOLOM VISUALISASI PETA (SIDE BAR KANAN)
    # ==========================================
    with col_map:
        if (file_type == "csv" and df_csv is not None) or (file_type == "tif" and raster_data is not None):
            with st.spinner("⚡ Sedang memproses visualisasi kartografi super cepat..."):
                # Inisiasi Figure Cartopy
                fig = plt.figure(figsize=(11, 7.5))
                ax = plt.axes(projection=ccrs.PlateCarree())
                
                # Terapkan Bounding Box
                ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

                # Layer Background Standar BMKG (Lautan Putih, Daratan Abu, Garis Hitam)
                ax.add_feature(cfeature.OCEAN, facecolor='#ffffff', zorder=0)
                ax.add_feature(cfeature.LAND, facecolor='#eaeaea', zorder=1)
                ax.add_feature(cfeature.COASTLINE, edgecolor='#000000', linewidth=0.9, zorder=3)
                ax.add_feature(cfeature.BORDERS, edgecolor='#333333', linestyle='--', linewidth=0.6, zorder=3)
                
                # Gridlines
                gl = ax.gridlines(draw_labels=True, linewidth=0.5, color='gray', alpha=0.5, linestyle=':')
                gl.top_labels = False
                gl.right_labels = False
                gl.xlabel_style = {'size': 9, 'color': '#333333'}
                gl.ylabel_style = {'size': 9, 'color': '#333333'}

                # Tentukan Colormap & Normalisasi
                if color_mode == "Classified (Diskret)":
                    cmap = plt.get_cmap(cmap_choice, num_classes)
                else:
                    cmap = plt.get_cmap(cmap_choice)

                # ----------------------------------------------------
                # RENDER DATA CSV (Warna Murni Tanpa Overlay Hitam!)
                # ----------------------------------------------------
                if file_type == "csv" and df_csv is not None:
                    x = df_csv[lon_col]
                    y = df_csv[lat_col]
                    z = df_csv[val_col]
                    
                    # Dinamis: Ukuran titik menyesuaikan jumlah data agar tetap elegan
                    pt_size = np.clip(2000 / len(df_csv), 12, 65)
                    
                    # PENTING: edgecolor='none' dan alpha=0.9 mencegah titik hitam menumpuk!
                    plot_obj = ax.scatter(
                        x, y, c=z, cmap=cmap, s=pt_size, 
                        transform=ccrs.PlateCarree(), 
                        edgecolor='none',  # Hapus border hitam yang merusak warna
                        alpha=0.9,         # Halus dan menyatu dengan warna cbar
                        zorder=2
                    )

                # ----------------------------------------------------
                # RENDER DATA GEOTIFF (Raster Image)
                # ----------------------------------------------------
                elif file_type == "tif" and raster_data is not None:
                    img_data = raster_data.copy().astype(float)
                    if raster_nodata is not None:
                        img_data[img_data == raster_nodata] = np.nan
                    
                    extent = [raster_bounds.left, raster_bounds.right, raster_bounds.bottom, raster_bounds.top]
                    
                    plot_obj = ax.imshow(
                        img_data, origin='upper', extent=extent,
                        cmap=cmap, transform=ccrs.PlateCarree(), zorder=2, alpha=0.9
                    )

                # --- COLORBAR (LEGENDA) ---
                cbar = plt.colorbar(plot_obj, ax=ax, orientation='horizontal', pad=0.07, aspect=45, shrink=0.85)
                cbar.set_label(legend_title, fontweight='bold', fontsize=11, color='#003366')
                cbar.ax.tick_params(labelsize=9)

                # --- JUDUL PETA ---
                plt.title(map_title.upper(), pad=18, fontweight='bold', fontsize=13, color='#003366')

                # Tampilkan ke Streamlit
                st.pyplot(fig)

                # --- TOMBOL DOWNLOAD RESOLUSI TINGGI (300 DPI) ---
                buf = io.BytesIO()
                fig.savefig(buf, format="png", dpi=300, bbox_inches="tight", facecolor='white')
                
                st.download_button(
                    label="⬇️ Download Peta Standar BMKG (Resolusi Tinggi 300 DPI)",
                    data=buf.getvalue(),
                    file_name="Peta_Operasional_BMKG.png",
                    mime="image/png",
                    use_container_width=True
                )
        else:
            st.markdown("""
            <div style="background-color: #f8fafc; border: 2px dashed #cbd5e1; border-radius: 10px; padding: 60px 20px; text-align: center; margin-top: 10px;">
                <h4 style="color: #64748b; margin-bottom: 10px;">🛰️ Area Preview Peta Kartografi</h4>
                <p style="color: #94a3b8; font-size: 0.95rem;">Silakan pilih sumber data (CSV atau GeoTIFF) pada panel pengaturan di sebelah kiri untuk mulai menghasilkan peta operasional.</p>
            </div>
            """, unsafe_allow_html=True)

if __name__ == "__main__":
    run_proyek3()