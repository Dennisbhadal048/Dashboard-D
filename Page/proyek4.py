import os
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy.interpolate import griddata, Rbf

# 1. Konfigurasi Halaman
st.set_page_config(page_title="Spatial Map Interpolator", page_icon="🛰️", layout="wide")

# --- FUNGSI ---
@st.cache_data
def load_gsmap_data(file_path, sep=','):
    if file_path.endswith(".csv"): return pd.read_csv(file_path, sep=sep)
    return pd.read_excel(file_path)

# --- SIDEBAR ---
ARCHIVE_DIR = os.path.join("Data", "archive")
available_files = sorted([f for f in os.listdir(ARCHIVE_DIR) if f.lower().endswith((".csv", ".xls", ".xlsx"))])
selected_file = st.sidebar.selectbox("Pilih file data:", available_files)
file_path = os.path.join(ARCHIVE_DIR, selected_file)

# FITUR SEP (Delimiter)
sep = ","
if selected_file.endswith(".csv"):
    sep = st.sidebar.selectbox("Pilih Delimiter (untuk CSV):", [",", ";", "\t"], index=0)

df_raw = load_gsmap_data(file_path, sep=sep)

st.sidebar.markdown("---")
st.sidebar.subheader("🛠️ Mapping Kolom")
all_cols = list(df_raw.columns)
actual_lon = st.sidebar.selectbox("Longitude:", all_cols, index=all_cols.index('lon') if 'lon' in all_cols else 0)
actual_lat = st.sidebar.selectbox("Latitude:", all_cols, index=all_cols.index('lat') if 'lat' in all_cols else 0)
actual_ch = st.sidebar.selectbox("Parameter (CH):", all_cols, index=all_cols.index('ch') if 'ch' in all_cols else 0)

# --- PROSES DATA DENGAN ELIMINASI ---
for col in [actual_lon, actual_lat, actual_ch]: 
    df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce')

initial_count = len(df_raw)
df_clean = df_raw.dropna(subset=[actual_lon, actual_lat, actual_ch]).copy()
df_clean = df_clean[df_clean[actual_ch] != 0].copy() 

if len(df_clean) < initial_count:
    st.sidebar.info(f"⚡ Eliminasi: {initial_count - len(df_clean)} baris data nol/null dibersihkan.")

# --- VISUALISASI ---
st.title("🛰️ Spatial Map Interpolator")

# Statistik Deskriptif di Atas
st.subheader("📈 Statistik Deskriptif")
stats = df_clean[actual_ch].describe()

col_stat1, col_stat2, col_stat3, col_stat4, col_stat5 = st.columns(5)
with col_stat1:
    st.metric("Mean", f"{stats['mean']:.2f}")
with col_stat2:
    st.metric("Median", f"{df_clean[actual_ch].median():.2f}")
with col_stat3:
    st.metric("Min", f"{stats['min']:.2f}")
with col_stat4:
    st.metric("Max", f"{stats['max']:.2f}")
with col_stat5:
    st.metric("Std Dev", f"{stats['std']:.2f}")

st.markdown("---")

# Peta Spasial
st.subheader("🗺️ Peta Spasial")
viz_mode = st.radio("Metode Peta:", ["Titik (Scatter)", "Interpolasi IDW", "Interpolasi Kriging (RBF)"], horizontal=True)

# Hitung bounds dari data untuk mencakup seluruh Indonesia
lon_min, lon_max = df_clean[actual_lon].min(), df_clean[actual_lon].max()
lat_min, lat_max = df_clean[actual_lat].min(), df_clean[actual_lat].max()

# Tambahkan margin untuk tampilan yang lebih luas
lon_margin = (lon_max - lon_min) * 0.1
lat_margin = (lat_max - lat_min) * 0.1

if viz_mode == "Titik (Scatter)":
    fig = px.scatter_mapbox(df_clean, lat=actual_lat, lon=actual_lon, color=actual_ch, 
                            color_continuous_scale="Jet", height=600)
    fig.update_layout(
        mapbox=dict(
            style="carto-positron",
            bounds=dict(
                west=lon_min - lon_margin,
                east=lon_max + lon_margin,
                south=lat_min - lat_margin,
                north=lat_max + lat_margin
            )
        )
    )
else:
    x, y, z = df_clean[actual_lon].values, df_clean[actual_lat].values, df_clean[actual_ch].values
    grid_x, grid_y = np.mgrid[x.min():x.max():100j, y.min():y.max():100j]
    
    if viz_mode == "Interpolasi IDW":
        grid_z = griddata((x, y), z, (grid_x, grid_y), method='linear')
    else:
        rbf = Rbf(x, y, z, function='linear')
        grid_z = rbf(grid_x, grid_y)
    
    # Buat filled contour plot yang solid
    fig = go.Figure(data=go.Contour(
        x=grid_x[0],
        y=grid_y[:, 0],
        z=grid_z,
        colorscale='Jet',
        contours=dict(coloring='heatmap'),
        colorbar=dict(title=actual_ch)
    ))
    fig.update_layout(
        title=f"{viz_mode}",
        xaxis_title="Longitude",
        yaxis_title="Latitude",
        height=600
    )

fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# Visualisasi Statistik
st.subheader("📊 Visualisasi Data")
col1, col2 = st.columns(2)

with col1:
    fig_hist = px.histogram(df_clean, x=actual_ch, title="Histogram - Distribusi", nbins=50)
    st.plotly_chart(fig_hist, use_container_width=True)
    
    fig_box = px.box(df_clean, y=actual_ch, title="Box Plot - Deteksi Outlier")
    st.plotly_chart(fig_box, use_container_width=True)

with col2:
    fig_violin = px.violin(df_clean, y=actual_ch, title="Violin Plot - Density")
    st.plotly_chart(fig_violin, use_container_width=True)
    
    fig_we = px.scatter(df_clean, x=actual_lon, y=actual_ch, title="Profil Barat - Timur", trendline="ols")
    st.plotly_chart(fig_we, use_container_width=True)

st.markdown("---")

with st.expander("Lihat Data Tabel"):
    st.dataframe(df_clean, use_container_width=True)