import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import timedelta

# --- FUNGSI FISIS (VEKTOR) ---
def calculate_heat_index_vectorized(T_c, RH):
    T = (T_c * 9/5) + 32  
    c1, c2, c3, c4, c5, c6, c7, c8, c9 = [
        -42.379, 2.04901523, 10.14333127, -0.22475541, 
        -0.00683783, -0.05481717, 0.00122874, 0.00085282, -0.00000199
    ]
    hi_f_complex = (c1 + (c2 * T) + (c3 * RH) + (c4 * T * RH) + 
                    (c5 * (T**2)) + (c6 * (RH**2)) + (c7 * (T**2) * RH) + 
                    (c8 * T * (RH**2)) + (c9 * (T**2) * (RH**2)))
    hi_f_simple = 0.5 * (T + 61.0 + ((T - 68.0) * 1.2) + (RH * 0.094))
    heat_index_f = np.where(hi_f_simple < 80, hi_f_simple, hi_f_complex)
    return (heat_index_f - 32) * 5/9  

# --- DATA LOADER ---
@st.cache_data
def load_weather_data(file_path):
    df = pd.read_csv(file_path, sep=None, engine='python')
    df.columns = df.columns.str.strip()
    timestamp_col = [col for col in df.columns if 'timestamp' in col.lower() or 'time' in col.lower() or 'tanggal' in col.lower()]
    if timestamp_col:
        df['date'] = pd.to_datetime(df[timestamp_col[0]], format='%d/%m/%Y %H:%M', errors='coerce')
    else:
        st.error(f"Kolom Waktu tidak terdeteksi! Struktur kolom: {list(df.columns)}")
        st.stop()
    temp_col = [col for col in df.columns if 'temp' in col.lower() or 'dry' in col.lower()]
    rh_col = [col for col in df.columns if 'humidity' in col.lower() or 'rh' in col.lower()]
    
    df['heat_index_c'] = calculate_heat_index_vectorized(df[temp_col[0]], df[rh_col[0]])
    df['temp_drybulb_c_ttttt'] = df[temp_col[0]]
    return df

@st.cache_data
def load_twitter_data(file_path):
    df = pd.read_csv(file_path, sep=None, engine='python')
    df.columns = df.columns.str.strip()
    date_col = [col for col in df.columns if 'tanggal' in col.lower() or 'posting' in col.lower() or 'date' in col.lower()]
    if date_col:
        df['date'] = pd.to_datetime(df[date_col[0]], format='%d/%m/%Y', errors='coerce')
    else:
        st.error(f"Kolom Tanggal tidak terdeteksi! Struktur kolom: {list(df.columns)}")
        st.stop()
        
    if 'Total Interaksi' in df.columns:
        df['interaction_score'] = df['Total Interaksi'].fillna(0)
    else:
        retweet_col = [col for col in df.columns if 'retweet' in col.lower()]
        like_col = [col for col in df.columns if 'like' in col.lower() or 'suka' in col.lower()]
        rt_series = df[retweet_col[0]].fillna(0) if retweet_col else 0
        like_series = df[like_col[0]].fillna(0) if like_col else 0
        df['interaction_score'] = rt_series + like_series
    return df

# --- EKSEKUSI DATA ---
WEATHER_CSV = "data_cuaca_kemayoran.csv" 
TWITTER_CSV = "data_tweet_harian.csv"

try:
    temp_data = load_weather_data(WEATHER_CSV)
    twitter_data = load_twitter_data(TWITTER_CSV)
except FileNotFoundError as e:
    st.error(f"⚠️ **File CSV Utama Tidak Ditemukan!**")
    st.stop()

# --- FILTER CONTROL (SIDEBAR) ---
st.sidebar.subheader("🔧 Filter Parameter")
min_date = temp_data['date'].min().date()
max_date = temp_data['date'].max().date()

date_range = st.sidebar.date_input(
    "Rentang Waktu Observasi",
    value=(min_date, min_date + timedelta(days=14)), 
    min_value=min_date,
    max_value=max_date
)

heat_threshold_c = st.sidebar.slider(
    "Ambang Batas Alergi Peringatan (°C)", 
    min_value=25, max_value=45, value=35
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_d, end_d = date_range[0], date_range[1]
    filtered_temp = temp_data[(temp_data['date'].dt.date >= start_d) & (temp_data['date'].dt.date <= end_d)]
    filtered_twitter = twitter_data[(twitter_data['date'].dt.date >= start_d) & (twitter_data['date'].dt.date <= end_d)]
else:
    st.stop()

# --- TAMPILAN UTAMA PROYEK 1 ---
st.title("🌡️ Heat Index & Public Response Monitor")
st.markdown("Integrasi parameter fisis atmosfer permukaan dengan dinamika ekspresi sosiologis masyarakat wilayah DKI Jakarta.")

# Tampilan Metrik Sejajar
m1, m2, m3, m4 = st.columns(4)
with m1:
    if not filtered_temp.empty:
        st.metric("Rata-rata Suhu Udara", f"{filtered_temp['temp_drybulb_c_ttttt'].mean():.1f} °C")
with m2:
    if not filtered_temp.empty:
        st.metric("Rata-rata Indeks Panas", f"{filtered_temp['heat_index_c'].mean():.1f} °C")
with m3:
    st.metric("Total Sampel Cuitan", f"{len(filtered_twitter):,} Tweet")
with m4:
    st.metric("Total Akumulasi Interaksi", f"{filtered_twitter['interaction_score'].sum():,}")

st.markdown("---")

# Menggunakan ikon emoji murni pada penamaan tab agar terhindar dari pemotongan visual teks CSS
tab1, tab2, tab3, tab4 = st.tabs(["📈 Tren Waktu", "🗺️ Cakupan Peta", "📊 Karakteristik Respon", "📋 Arsip Data"])

with tab1:
    st.subheader("Analisis Sinkronisasi Temporal")
    if not filtered_temp.empty:
        daily_weather = filtered_temp.groupby(filtered_temp['date'].dt.date).mean(numeric_only=True).reset_index()
        text_col = [col for col in filtered_twitter.columns if 'teks' in col.lower() or 'tweet' in col.lower() or 'text' in col.lower()]
        actual_text_col = text_col[0] if text_col else filtered_twitter.columns[0]
        
        daily_twitter = filtered_twitter.groupby(filtered_twitter['date'].dt.date).agg(
            jumlah_tweet=(actual_text_col, 'count'),
            total_interaksi=('interaction_score', 'sum')
        ).reset_index()
        
        merged_daily = pd.merge(daily_weather, daily_twitter, on='date', how='left').fillna(0)
        merged_daily['total_respon'] = merged_daily['jumlah_tweet'] + merged_daily['total_interaksi']
        
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=merged_daily['date'], y=merged_daily['heat_index_c'], name="Indeks Panas (°C)", line=dict(color='#E74C3C', width=3)), secondary_y=False)
        fig.add_trace(go.Scatter(x=merged_daily['date'], y=merged_daily['total_respon'], name="Respon Netizen Terkait Panas", line=dict(color='#2980B9', width=2.5, dash='dot')), secondary_y=True)
        
        # PERBAIKAN GRAFIK: Mengubah total tema Plotly menjadi Putih Bersih (plotly_white)
        fig.update_layout(
            template="plotly_white", 
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=40, r=40, t=30, b=30),
            # Mengunci warna teks global & legenda menjadi gelap
            font=dict(color='#1A252F'),
            legend=dict(font=dict(color='#1A252F'))
        )
        
        # 1. Perbaikan Sumbu X
        fig.update_xaxes(
            showgrid=True, 
            gridcolor='#EAEAEA', 
            tickfont=dict(color='#1A252F'), # Warna angka skala X
            title=dict(
                text="Kala Waktu Analisis",
                font=dict(color='#1A252F') # Warna judul sumbu X
            )
        )
        
        # 2. Perbaikan Sumbu Y Utama (Kiri - Indeks Panas)
        fig.update_yaxes(
            showgrid=True, 
            gridcolor='#EAEAEA', 
            tickfont=dict(color='#1A252F'), # Warna angka skala Y Kiri
            title=dict(
                text="Indeks Panas (°C)",
                font=dict(color='#1A252F') # Warna judul sumbu Y Kiri
            ),
            secondary_y=False
        )
        
        # 3. Perbaikan Sumbu Y Sekunder (Kanan - Skala Respon)
        fig.update_yaxes(
            showgrid=False, 
            tickfont=dict(color='#1A252F'), # Warna angka skala Y Kanan (Kunci Utama Perbaikan)
            title=dict(
                text="Skala Respon (Tweet + Engagement)",
                font=dict(color='#1A252F') # Warna judul sumbu Y Kanan
            ),
            secondary_y=True
        )
        
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Batas Geografis Representatif")
    jkt_lat, jkt_lon = -6.2088, 106.8456
    angles = np.linspace(0, 2*np.pi, 100)
    r_earth = 6371.0 
    radius_target = 15.0 
    lat_offsets = (radius_target / r_earth) * (180 / np.pi) * np.sin(angles)
    lon_offsets = (radius_target / r_earth) * (180 / np.pi) * np.cos(angles) / np.cos(jkt_lat * np.pi / 180)
    
    circle_lats = jkt_lat + lat_offsets
    circle_lons = jkt_lon + lon_offsets 

    fig_map = go.Figure()
    fig_map.add_trace(go.Scattermapbox(lat=circle_lats, lon=circle_lons, mode='lines', fill='toself', fillcolor='rgba(231, 76, 60, 0.12)', line=dict(color='#C0392B', width=2), name="Radius Area Jakarta (~15 Km)"))
    fig_map.add_trace(go.Scattermapbox(lat=[jkt_lat], lon=[jkt_lon], mode='markers', marker=go.scattermapbox.Marker(size=12, color='#C0392B'), showlegend=False))

    fig_map.update_layout(
        mapbox=dict(style="open-street-map", center=go.layout.mapbox.Center(lat=jkt_lat, lon=jkt_lon), zoom=10),
        margin={"r":0,"t":10,"l":0,"b":0}, 
        height=500
    )
    st.plotly_chart(fig_map, use_container_width=True)

with tab3:
    st.subheader("Karakteristik Komparasi Frekuensi Data")
    col_l, col_r = st.columns(2)
    with col_l:
        fig_hist = px.histogram(filtered_temp, x='heat_index_c', title="Kerapatan Distribusi Indeks Termal (°C)", color_discrete_sequence=['#F39C12'], template="plotly_white")
        fig_hist.update_layout(plot_bgcolor='rgba(255,255,255,1)', paper_bgcolor='rgba(255,255,255,1)', font=dict(color='#1A252F'))
        fig_hist.update_xaxes(showgrid=True, gridcolor='#EAEAEA')
        fig_hist.update_yaxes(showgrid=True, gridcolor='#EAEAEA')
        st.plotly_chart(fig_hist, use_container_width=True)
    with col_r:
        daily_interact_bar = filtered_twitter.groupby('date')['interaction_score'].sum().reset_index()
        fig_bar = px.bar(daily_interact_bar, x='date', y='interaction_score', title="Intensitas Keterlibatan Publik Harian", color_discrete_sequence=['#16A085'], template="plotly_white")
        fig_bar.update_layout(plot_bgcolor='rgba(255,255,255,1)', paper_bgcolor='rgba(255,255,255,1)', font=dict(color='#1A252F'))
        fig_bar.update_xaxes(showgrid=True, gridcolor='#EAEAEA')
        fig_bar.update_yaxes(showgrid=True, gridcolor='#EAEAEA')
        st.plotly_chart(fig_bar, use_container_width=True)

with tab4:
    st.subheader("Cuitan Terpopuler Wilayah Studi")
    text_cols = [col for col in filtered_twitter.columns if 'teks' in col.lower() or 'tweet' in col.lower() or 'text' in col.lower()]
    user_cols = [col for col in filtered_twitter.columns if 'user' in col.lower() or 'nama' in col.lower()]
    rt_cols = [col for col in filtered_twitter.columns if 'retweet' in col.lower()]
    like_cols = [col for col in filtered_twitter.columns if 'like' in col.lower() or 'suka' in col.lower()]
    
    t_key = text_cols[0] if text_cols else filtered_twitter.columns[0]
    u_key = user_cols[0] if user_cols else filtered_twitter.columns[0]
    rt_key = rt_cols[0] if rt_cols else None
    lk_key = like_cols[0] if like_cols else None

    if not filtered_twitter.empty and t_key in filtered_twitter.columns:
        top_tweets = filtered_twitter.nlargest(5, 'interaction_score')
        for _, tweet in top_tweets.iterrows():
            st.markdown(f"💬 **@{tweet[u_key]}** | 🔁 {int(tweet[rt_key]) if rt_key else 0} Retweets | ❤️ {int(tweet[lk_key]) if lk_key else 0} Likes")
            st.write(f"> *\"{tweet[t_key]}\"*")
            st.write("---")
            
    st.subheader("🔍 Pengecekan Integritas Dataset")
    with st.expander("Klik untuk Meninjau Data Mentah Historis"):
        choice = st.selectbox("Pilih Tabel Sumber:", ["Meteorologi Dasar per Jam", "Respon Publik Media Sosial"])
        if choice == "Meteorologi Dasar per Jam":
            st.dataframe(filtered_temp, use_container_width=True)
        else:
            st.dataframe(filtered_twitter, use_container_width=True)