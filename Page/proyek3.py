import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap, to_hex
from matplotlib.ticker import FuncFormatter
from scipy.interpolate import griddata, Rbf
from shapely.geometry import Point
import contextily as ctx
from PIL import Image
import os
import io
import folium
from streamlit_folium import st_folium
import branca.colormap as cm
import base64

# --- TENTUKAN PATH DEFAULT UNTUK ARSIP DATA ---
ARCHIVE_DIR = os.path.join("Data", "archive")
os.makedirs(ARCHIVE_DIR, exist_ok=True)

# --- TEMA MATPLOTLIB KARTOGRAFI FORMAL ---
plt.style.use('default')
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "axes.edgecolor": "black",
    "axes.linewidth": 1.2
})

def lon_fmt(x, pos):
    return f"{abs(x):.0f}°E"
def lat_fmt(y, pos):
    return f"{abs(y):.0f}°{'S' if y < 0 else 'N'}"

# --- HEADER HALAMAN ---
st.markdown(
    """
    <div style="background-color: #F8F9FA; border-left: 4px solid #1A252F; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
        <h2 style="color: #1A252F; margin: 0 0 10px 0; font-size: 2rem;">🗺️ GIS Cartography & Spatial Interpolator</h2>
        <p style="color: #5A6A75; margin: 0; font-size: 1.05rem;">
            Modul pemetaan interaktif cepat dengan sistem memori internal (caching), anti-crash untuk data segaris, dan optimasi tata letak cetak Kanvas A4.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# --- PALET WARNA KHUSUS (8 Warna) ---
CUSTOM_COLORS = ['#ED1C24', '#F26522', '#F7941D', '#FFF200', '#D7DF23', '#8DC63F', '#39B54A', '#006837']
custom_cmap = LinearSegmentedColormap.from_list("climate_trend", CUSTOM_COLORS)

# --- STEP 1: INGESTION FILE ---
st.markdown("<h3 style='color: #1A252F;'>📂 Step 1: Input Data Spasial & Peta Administrasi</h3>", unsafe_allow_html=True)
c_input1, c_input2 = st.columns(2)
df_spatial = None
loaded_file_name = ""

with c_input1:
    st.markdown("**Sumber Data Pengamatan:**")
    data_source = st.radio("Metode Input Data:", ["Pilih dari Arsip Server", "Unggah Berkas Baru"], horizontal=True)
    separator = ","
    
    if data_source == "Pilih dari Arsip Server":
        available_files = [f for f in os.listdir(ARCHIVE_DIR) if f.endswith(('.csv', '.xlsx'))]
        if not available_files:
            st.warning(f"Belum ada berkas pendukung di direktori `{ARCHIVE_DIR}`.")
        else:
            selected_file = st.selectbox("Pilih berkas dari arsip:", available_files)
            if selected_file and selected_file.endswith('.csv'):
                sep_mode = st.selectbox("Delimiter:", ["Titik Koma ( ; )", "Koma ( , )", "Tab ( \\t )", "Spasi"], key="sep_archive")
                separator = ";" if sep_mode == "Titik Koma ( ; )" else "," if sep_mode == "Koma ( , )" else "\t" if sep_mode == "Tab ( \\t )" else " "

            if selected_file:
                file_path = os.path.join(ARCHIVE_DIR, selected_file)
                try:
                    df_spatial = pd.read_csv(file_path, sep=separator, engine='python') if selected_file.endswith('.csv') else pd.read_excel(file_path)
                    loaded_file_name = selected_file
                except Exception as e:
                    st.error(f"Gagal membaca file: {e}")
    else:
        uploaded_file = st.file_uploader("Unggah Berkas (.csv / .xlsx)", type=["csv", "xlsx"])
        if uploaded_file is not None:
            if uploaded_file.name.endswith('.csv'):
                sep_mode = st.selectbox("Delimiter:", ["Titik Koma ( ; )", "Koma ( , )", "Tab ( \\t )", "Spasi"], key="sep_upload")
                separator = ";" if sep_mode == "Titik Koma ( ; )" else "," if sep_mode == "Koma ( , )" else "\t" if sep_mode == "Tab ( \\t )" else " "

            save_path = os.path.join(ARCHIVE_DIR, uploaded_file.name)
            try:
                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success("✔️ Berkas diamankan ke Arsip.")
                df_spatial = pd.read_csv(save_path, sep=separator, engine='python') if uploaded_file.name.endswith('.csv') else pd.read_excel(save_path)
                loaded_file_name = uploaded_file.name
            except Exception as e:
                st.error(f"Gagal menyimpan: {e}")

with c_input2:
    st.markdown("**Peta Administrasi Pembatas (SHP):**")
    shp_mode = st.radio("Tingkat Batas Administrasi:", ["Provinsi", "Kabupaten/Kota"], horizontal=True)
    file_mapping = {"Provinsi": "INDONESIA_PROP.shp", "Kabupaten/Kota": "INDONESIA_KAB.shp"}
    shp_path_input = os.path.join("Data", "shp", file_mapping[shp_mode])
    
    if os.path.exists(shp_path_input):
        st.success(f"✔️ SHP Aktif: `{shp_path_input}`")
        shp_ready = True
    else:
        st.error(f"❌ SHP Tidak Ditemukan: `{shp_path_input}`")
        shp_ready = False

if df_spatial is not None:
    df_spatial.columns = df_spatial.columns.str.strip()
    
    # --- STEP 2: METADATA & MAP LAYOUT ---
    st.markdown("---")
    st.markdown("<h3 style='color: #1A252F;'>⚙️ Step 2: Konfigurasi Parameter & Atribut Kartografi</h3>", unsafe_allow_html=True)
    
    c_cfg1, c_cfg2, c_cfg3 = st.columns(3)
    with c_cfg1:
        lon_col = st.selectbox("Kolom Longitude (X):", list(df_spatial.columns))
    with c_cfg2:
        lat_col = st.selectbox("Kolom Latitude (Y):", list(df_spatial.columns))
    with c_cfg3:
        available_val_cols = [c for c in df_spatial.columns if c not in [lon_col, lat_col]]
        val_col = st.selectbox("Parameter Data:", available_val_cols) if available_val_cols else None

    if lon_col is None or lat_col is None or val_col is None:
        st.error("❌ Kolom penanda data spasial tidak lengkap.")
        st.stop()

    # FILTER OTOMATIS: Bersihkan Null dan data bernilai NOL (0) langsung sebelum proses komputasi
    initial_count = len(df_spatial)
    df_spatial = df_spatial.dropna(subset=[lon_col, lat_col, val_col])
    df_spatial = df_spatial[df_spatial[val_col] != 0].copy()
    filtered_count = len(df_spatial)
    
    if filtered_count < initial_count:
        st.info(f"⚡ Otomatisasi Eliminasi: `{initial_count - filtered_count}` baris data bernilai 0/Null berhasil dibersihkan untuk mempercepat komputasi.")

    st.markdown("**Pengaturan Layout Etiket Peta (Untuk Mode Cetak/Download)**")
    c_layout1, c_layout2 = st.columns(2)
    with c_layout1:
        map_title = st.text_area("Judul Peta (Atas Logo):", value="PETA LAJU PERUBAHAN\nCURAH HUJAN TAHUNAN INDONESIA\nPERIODE 2021 - 2050")
        author_info = st.text_area("Informasi Penyusun (Bawah Logo):", value="DENNIS BHADAL PERMANA\n21.23.0020")
    with c_layout2:
        legend_title = st.text_input("Judul Legenda / Colorbar:", value="LAJU PERUBAHAN CURAH HUJAN (MM/TAHUN)")
        logo_upload = st.file_uploader("Upload Logo Instansi (PNG/JPG):", type=['png', 'jpg', 'jpeg'])

    # --- STEP 3: INTERPOLASI & SIMBOLOGI ---
    st.markdown("---")
    st.markdown("<h3 style='color: #1A252F;'>🎨 Step 3: Pengaturan Algoritma & Skala Warna</h3>", unsafe_allow_html=True)
    
    c_set1, c_set2 = st.columns(2)
    with c_set1:
        viz_method = st.selectbox("Tipe Visualisasi:", ["Interpolasi IDW (SciPy Fast)", "Interpolasi Kriging (Rbf Proxy)", "Titik Pengamatan Saja"])
            
    with c_set2:
        colorbar_type = st.radio("Tipe Tampilan Colorbar:", ["Classified (Kotak Diskret)", "Stretched (Memanjang Kontinu)"], horizontal=True)
        if colorbar_type == "Classified (Kotak Diskret)":
            num_classes = st.slider("Jumlah Kelas Gradasi (Maks 8):", min_value=3, max_value=8, value=8)
        else:
            min_val_f = float(df_spatial[val_col].min())
            max_val_f = float(df_spatial[val_col].max())
            v_bounds = st.slider("Ambang Batas Colorbar:", min_val_f, max_val_f, (min_val_f, max_val_f))

    # --- OPTIMASI EFISIENSI: CACHING BERBASIS STATE ---
    current_state_trigger = f"{loaded_file_name}_{val_col}_{viz_method}_{colorbar_type}_{num_classes if colorbar_type == 'Classified (Kotak Diskret)' else 'stretched'}_{shp_mode}"
    
    if 'last_state_trigger' not in st.session_state or st.session_state['last_state_trigger'] != current_state_trigger:
        st.session_state['last_state_trigger'] = current_state_trigger
        
        gdf_mask = gpd.read_file(shp_path_input) if shp_ready else None
        if gdf_mask is not None and (gdf_mask.crs is None or gdf_mask.crs.to_string() != "EPSG:4326"):
            gdf_mask = gdf_mask.to_crs("EPSG:4326")
            
        x_data = df_spatial[lon_col].values
        y_data = df_spatial[lat_col].values
        z_data = df_spatial[val_col].values
        
        if gdf_mask is not None:
            minx, miny, maxx, maxy = gdf_mask.total_bounds
        else:
            minx, miny, maxx, maxy = x_data.min() - 0.5, y_data.min() - 0.5, x_data.max() + 0.5, y_data.max() + 0.5

        # Format teks dinamis adaptif interval desimal (Mencegah bug teks kembar)
        val_range = z_data.max() - z_data.min() if len(z_data) > 0 else 0
        fmt_str = "{:.3f}" if val_range < 1.0 else "{:.2f}" if val_range < 10.0 else "{:.1f}"

        grid_x, grid_y, grid_z = None, None, None
        boundaries, norm = None, None

        if viz_method != "Titik Pengamatan Saja":
            # Resolusi 120j untuk Web Viewer
            grid_x, grid_y = np.mgrid[minx-0.1:maxx+0.1:120j, miny-0.1:maxy+0.1:120j]
            
            # PENGGUNAAN FAST SCIPY INTERPOLATION DENGAN PENGAMAN QHULL ERROR
            if "Kriging" in viz_method:
                try:
                    rbf = Rbf(x_data, y_data, z_data, function='linear')
                    grid_z = rbf(grid_x, grid_y)
                except Exception:
                    # Fallback jika RBF singular
                    try:
                        grid_z = griddata((x_data, y_data), z_data, (grid_x, grid_y), method='linear')
                    except Exception:
                        grid_z = griddata((x_data, y_data), z_data, (grid_x, grid_y), method='nearest')
            else:
                # Blok Try-Except untuk menangani QhullError (data segaris lurus)
                try:
                    grid_z = griddata((x_data, y_data), z_data, (grid_x, grid_y), method='linear')
                except Exception:
                    grid_z = griddata((x_data, y_data), z_data, (grid_x, grid_y), method='nearest')
                
                grid_z_near = griddata((x_data, y_data), z_data, (grid_x, grid_y), method='nearest')
                grid_z = np.where(np.isnan(grid_z), grid_z_near, grid_z)

            # MASKING STANDAR
            if gdf_mask is not None:
                flat_x, flat_y = grid_x.ravel(), grid_y.ravel()
                gdf_grid = gpd.GeoDataFrame(geometry=[Point(lon, lat) for lon, lat in zip(flat_x, flat_y)], crs="EPSG:4326")
                joined = gpd.sjoin(gdf_grid, gdf_mask, how='left', predicate='within')
                mask_matrix = (~joined['index_right'].isna()).values.reshape(grid_x.shape)
                grid_z[~mask_matrix] = np.nan

        # PENTING: Batas diambil dari data ASLI
        z_valid_min = z_data.min() if len(z_data) > 0 else 0
        z_valid_max = z_data.max() if len(z_data) > 0 else 100
        
        if colorbar_type == "Classified (Kotak Diskret)":
            boundaries = np.linspace(z_valid_min, z_valid_max, num_classes + 1)
            norm = BoundaryNorm(boundaries, custom_cmap.N)

        st.session_state['c_gdf_mask'] = gdf_mask
        st.session_state['c_x'] = x_data
        st.session_state['c_y'] = y_data
        st.session_state['c_z'] = z_data
        st.session_state['c_minx'] = minx
        st.session_state['c_miny'] = miny
        st.session_state['c_maxx'] = maxx
        st.session_state['c_maxy'] = maxy
        st.session_state['c_grid_x'] = grid_x
        st.session_state['c_grid_y'] = grid_y
        st.session_state['c_grid_z'] = grid_z
        st.session_state['c_boundaries'] = boundaries
        st.session_state['c_norm'] = norm
        st.session_state['c_fmt_str'] = fmt_str
        st.session_state['c_z_min'] = z_valid_min
        st.session_state['c_z_max'] = z_valid_max

    gdf_mask = st.session_state['c_gdf_mask']
    x = st.session_state['c_x']
    y = st.session_state['c_y']
    z = st.session_state['c_z']
    minx, miny, maxx, maxy = st.session_state['c_minx'], st.session_state['c_miny'], st.session_state['c_maxx'], st.session_state['c_maxy']
    grid_x, grid_y, grid_z = st.session_state['c_grid_x'], st.session_state['c_grid_y'], st.session_state['c_grid_z']
    boundaries = st.session_state['c_boundaries']
    norm = st.session_state['c_norm']
    fmt_str = st.session_state['c_fmt_str']
    z_valid_min = st.session_state['c_z_min']
    z_valid_max = st.session_state['c_z_max']

    # --- STEP 4: RENDER PETA INTERAKTIF (FOLIUM VIEW MODE) ---
    st.markdown("---")
    st.markdown("<h3 style='color: #1A252F;'>🗺️ Step 4: Peta Interaktif & Legenda Spasial</h3>", unsafe_allow_html=True)
    
    mean_lat, mean_lon = np.mean([miny, maxy]), np.mean([minx, maxx])
    m = folium.Map(location=[mean_lat, mean_lon], zoom_start=5, tiles='OpenStreetMap')

    if gdf_mask is not None:
        folium.GeoJson(
            gdf_mask,
            style_function=lambda x: {'fillColor': '#ffffff', 'color': '#333333', 'weight': 1.2, 'fillOpacity': 0.0}
        ).add_to(m)

    # PEMBUATAN COLORBAR INTERAKTIF UNTUK FOLIUM (Bebas Error IndexError)
    clean_caption = legend_title.replace('\n', ' ')
    if colorbar_type == "Classified (Kotak Diskret)":
        dynamic_colors = [to_hex(custom_cmap(i / (num_classes - 1))) for i in range(num_classes)]
        
        folium_cmap = cm.StepColormap(
            colors=dynamic_colors,
            vmin=z_valid_min,
            vmax=z_valid_max,
            index=list(boundaries),
            caption=clean_caption
        )
    else:
        folium_cmap = cm.LinearColormap(
            colors=CUSTOM_COLORS,
            vmin=v_bounds[0],
            vmax=v_bounds[1],
            caption=clean_caption
        )
    folium_cmap.add_to(m)

    if viz_method == "Titik Pengamatan Saja":
        for i in range(len(x)):
            color_val = '#000000'
            if colorbar_type == "Classified (Kotak Diskret)":
                for j in range(len(boundaries)-1):
                    if boundaries[j] <= z[i] <= boundaries[j+1]:
                        color_val = to_hex(custom_cmap(j / (num_classes - 1)))
                        break
            else:
                ratio = (z[i] - v_bounds[0]) / (v_bounds[1] - v_bounds[0] + 1e-12)
                ratio = max(0.0, min(1.0, ratio))
                color_val = to_hex(custom_cmap(ratio))

            folium.CircleMarker(
                location=[y[i], x[i]], radius=5, color='black', weight=1, fill=True, fillColor=color_val, fillOpacity=1.0,
                tooltip=f"{val_col}: {z[i]}"
            ).add_to(m)
    else:
        # Menghindari error kanvas kosong matplotlib
        if grid_z is not None and not np.isnan(grid_z).all():
            fig_img, ax_img = plt.subplots(figsize=(8, 8))
            ax_img.set_axis_off()
            fig_img.subplots_adjust(left=0, right=1, bottom=0, top=1)
            
            if colorbar_type == "Classified (Kotak Diskret)":
                ax_img.contourf(grid_x, grid_y, grid_z, levels=boundaries, cmap=custom_cmap, norm=norm, alpha=1.0)
            else:
                ax_img.contourf(grid_x, grid_y, grid_z, levels=50, cmap=custom_cmap, vmin=v_bounds[0], vmax=v_bounds[1], alpha=1.0)
                
            ax_img.set_xlim(minx - 0.05, maxx + 0.05)
            ax_img.set_ylim(miny - 0.05, maxy + 0.05)
            
            buf = io.BytesIO()
            plt.savefig(buf, format="png", transparent=True, pad_inches=0, bbox_inches='tight')
            buf.seek(0)
            b64_img = base64.b64encode(buf.read()).decode('utf-8')
            img_url = f"data:image/png;base64,{b64_img}"
            plt.close(fig_img)

            folium.raster_layers.ImageOverlay(
                image=img_url, bounds=[[miny - 0.05, minx - 0.05], [maxy + 0.05, maxx + 0.05]], opacity=1.0
            ).add_to(m)

    st_folium(m, width=900, height=500)

    # --- STEP 5: GENERATE PETA STATIS (DOWNLOAD MODE HARDCOPY A4 - PNG) ---
    st.markdown("---")
    st.markdown("<h3 style='color: #1A252F;'>📥 Step 5: Ekspor Layout Peta Cetak (A4 Gambar PNG)</h3>", unsafe_allow_html=True)
    
    if st.button("🖼️ Render Tata Letak Peta Cetak A4", use_container_width=True):
        with st.spinner("Merender layout kartografi resolusi tinggi..."):
            
            grid_x_high, grid_y_high, grid_z_high = None, None, None
            if viz_method != "Titik Pengamatan Saja":
                # Resolusi tinggi 180j untuk cetak
                grid_x_high, grid_y_high = np.mgrid[minx-0.1:maxx+0.1:180j, miny-0.1:maxy+0.1:180j]
                
                # PENGAMAN QHULL ERROR UNTUK MODE CETAK A4
                if "Kriging" in viz_method:
                    try:
                        rbf_h = Rbf(x, y, z, function='linear')
                        grid_z_high = rbf_h(grid_x_high, grid_y_high)
                    except Exception:
                        try:
                            grid_z_high = griddata((x, y), z, (grid_x_high, grid_y_high), method='linear')
                        except Exception:
                            grid_z_high = griddata((x, y), z, (grid_x_high, grid_y_high), method='nearest')
                else:
                    try:
                        grid_z_high = griddata((x, y), z, (grid_x_high, grid_y_high), method='linear')
                    except Exception:
                        grid_z_high = griddata((x, y), z, (grid_x_high, grid_y_high), method='nearest')
                        
                    grid_z_near = griddata((x, y), z, (grid_x_high, grid_y_high), method='nearest')
                    grid_z_high = np.where(np.isnan(grid_z_high), grid_z_near, grid_z_high)

                if gdf_mask is not None:
                    flat_x_h, flat_y_h = grid_x_high.ravel(), grid_y_high.ravel()
                    gdf_grid_h = gpd.GeoDataFrame(geometry=[Point(lon, lat) for lon, lat in zip(flat_x_h, flat_y_h)], crs="EPSG:4326")
                    joined_h = gpd.sjoin(gdf_grid_h, gdf_mask, how='left', predicate='within')
                    mask_matrix_h = (~joined_h['index_right'].isna()).values.reshape(grid_x_high.shape)
                    grid_z_high[~mask_matrix_h] = np.nan
            
            fig = plt.figure(figsize=(11.69, 8.27))
            fig.patch.set_facecolor('white')
            
            # PENGATURAN KOTAK PRESISI AGAR TIDAK TUMPANG TINDIH
            ax_map = fig.add_axes([0.05, 0.27, 0.9, 0.70]) # Blank space atas dikurangi
            ax_box1 = fig.add_axes([0.05, 0.03, 0.28, 0.20]) # Tinggi kotak ditambah
            ax_box2 = fig.add_axes([0.36, 0.03, 0.28, 0.20])
            ax_box3 = fig.add_axes([0.67, 0.03, 0.28, 0.20])

            ax_map.set_xlim(minx - 0.5, maxx + 0.5)
            ax_map.set_ylim(miny - 0.5, maxy + 0.5)

            if viz_method == "Titik Pengamatan Saja":
                if colorbar_type == "Classified (Kotak Diskret)":
                    ax_map.scatter(x, y, c=z, cmap=custom_cmap, norm=norm, s=60, edgecolors='black', linewidths=0.5, zorder=3)
                else:
                    ax_map.scatter(x, y, c=z, cmap=custom_cmap, vmin=v_bounds[0], vmax=v_bounds[1], s=60, edgecolors='black', linewidths=0.5, zorder=3)
            else:
                if grid_z_high is not None and colorbar_type == "Classified (Kotak Diskret)":
                    ax_map.contourf(grid_x_high, grid_y_high, grid_z_high, levels=boundaries, cmap=custom_cmap, norm=norm, alpha=1.0, zorder=2)
                elif grid_z_high is not None:
                    ax_map.contourf(grid_x_high, grid_y_high, grid_z_high, levels=50, cmap=custom_cmap, vmin=v_bounds[0], vmax=v_bounds[1], alpha=1.0, zorder=2)

            if gdf_mask is not None:
                gdf_mask.plot(ax=ax_map, facecolor='none', edgecolor='black', linewidth=0.5, zorder=4)

            try:
                ctx.add_basemap(ax_map, crs="EPSG:4326", source=ctx.providers.OpenStreetMap.Mapnik, alpha=0.8, zorder=1)
            except Exception:
                pass

            ax_map.grid(True, linestyle='--', color='gray', alpha=0.6, zorder=5)
            ax_map.xaxis.set_major_formatter(FuncFormatter(lon_fmt))
            ax_map.yaxis.set_major_formatter(FuncFormatter(lat_fmt))
            ax_map.tick_params(axis='both', which='major', labelsize=10, labelcolor='black')
            
            for ax_box in [ax_box1, ax_box2, ax_box3]:
                ax_box.set_xticks([])
                ax_box.set_yticks([])
                ax_box.set_facecolor('white')
                for spine in ax_box.spines.values():
                    spine.set_linewidth(1.5)
                    spine.set_color('black')

            # --- KOTAK I LAYOUT ---
            ax_box1.text(0.5, 0.92, map_title, ha='center', va='top', fontsize=10, weight='bold', color='black', transform=ax_box1.transAxes)
            if logo_upload is not None:
                try:
                    img = Image.open(logo_upload)
                    ax_img = ax_box1.inset_axes([0.37, 0.25, 0.26, 0.32]) 
                    ax_img.imshow(img)
                    ax_img.axis('off')
                except: pass
            ax_box1.text(0.5, 0.06, author_info, ha='center', va='bottom', fontsize=9, weight='bold', color='black', transform=ax_box1.transAxes)

            # --- KOTAK II LAYOUT ---
            ax_box2.text(0.5, 0.92, legend_title, ha='center', va='top', fontsize=9.5, weight='bold', color='black', transform=ax_box2.transAxes)
            if colorbar_type == "Classified (Kotak Diskret)":
                cols = 2
                box_w, box_h = 0.14, 0.12 
                start_x, start_y = 0.08, 0.62 
                for i in range(num_classes):
                    col_idx, row_idx = i % cols, i // cols
                    pos_x = start_x + (col_idx * 0.46)
                    pos_y = start_y - (row_idx * 0.23) 
                    
                    color_val = custom_cmap(i / (num_classes - 1))
                    rect = patches.Rectangle((pos_x, pos_y), box_w, box_h, linewidth=1, edgecolor='black', facecolor=color_val, transform=ax_box2.transAxes)
                    ax_box2.add_patch(rect)
                    
                    label_text = f"{fmt_str.format(boundaries[i])} - {fmt_str.format(boundaries[i+1])}"
                    ax_box2.text(pos_x + 0.18, pos_y + (box_h/2), label_text, va='center', fontsize=8.5, color='black', transform=ax_box2.transAxes)
            else:
                cax = ax_box2.inset_axes([0.1, 0.32, 0.8, 0.16])
                sm = plt.cm.ScalarMappable(cmap=custom_cmap, norm=plt.Normalize(vmin=v_bounds[0], vmax=v_bounds[1]))
                fig.colorbar(sm, cax=cax, orientation='horizontal').ax.tick_params(labelsize=9, colors='black')

            # --- KOTAK III LAYOUT ---
            ax_box3.text(0.05, 0.92, "KETERANGAN (LEGEND)", ha='left', va='top', fontsize=10, weight='bold', color='black', transform=ax_box3.transAxes)
            
            rect_batas = patches.Rectangle((0.05, 0.65), 0.18, 0.14, linewidth=1, edgecolor='black', facecolor='white', transform=ax_box3.transAxes)
            ax_box3.add_patch(rect_batas)
            ax_box3.text(0.28, 0.72, f"BATAS {shp_mode.upper()}", va='center', fontsize=9, color='black', transform=ax_box3.transAxes)

            ax_box3.text(0.5, 0.45, "N", ha='center', va='center', fontsize=13, weight='bold', color='black', transform=ax_box3.transAxes)
            ax_box3.annotate('', xy=(0.5, 0.38), xytext=(0.5, 0.16), arrowprops=dict(facecolor='black', width=1.8, headwidth=9, headlength=11), transform=ax_box3.transAxes)
            ax_box3.text(0.36, 0.27, "W", ha='center', va='center', fontsize=10, color='black', transform=ax_box3.transAxes)
            ax_box3.text(0.64, 0.27, "E", ha='center', va='center', fontsize=10, color='black', transform=ax_box3.transAxes)
            ax_box3.text(0.5, 0.06, "S", ha='center', va='center', fontsize=10, color='black', transform=ax_box3.transAxes)
            
            ax_box3.plot([0.65, 0.95], [0.15, 0.15], color='black', lw=2, transform=ax_box3.transAxes)
            ax_box3.plot([0.65, 0.65], [0.12, 0.18], color='black', lw=1.5, transform=ax_box3.transAxes)
            ax_box3.plot([0.8, 0.8], [0.12, 0.18], color='black', lw=1.5, transform=ax_box3.transAxes)
            ax_box3.plot([0.95, 0.95], [0.12, 0.18], color='black', lw=1.5, transform=ax_box3.transAxes)
            ax_box3.text(0.65, 0.08, "0", ha='center', va='top', fontsize=8, color='black', transform=ax_box3.transAxes)
            ax_box3.text(0.8, 0.08, "500", ha='center', va='top', fontsize=8, color='black', transform=ax_box3.transAxes)
            ax_box3.text(0.95, 0.08, "1000 KM", ha='center', va='top', fontsize=8, color='black', transform=ax_box3.transAxes)

            st.pyplot(fig)
            
            png_buf = io.BytesIO()
            fig.savefig(png_buf, format='png', dpi=300, bbox_inches='tight')
            st.download_button(
                label="📥 Download Gambar Peta Cetak A4 (Format PNG)", 
                data=png_buf.getvalue(), 
                file_name="peta_cetak_formal_a4.png", 
                mime="image/png", 
                use_container_width=True
            )