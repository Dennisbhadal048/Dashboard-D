import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import calendar
from html import escape

PLOT_THEME = dict(
    template="plotly_white",
    font=dict(color="#17212B", family="Segoe UI"),
    paper_bgcolor="rgba(255,255,255,0)",
    plot_bgcolor="rgba(255,255,255,0)",
    margin=dict(l=28, r=22, t=58, b=28),
    hoverlabel=dict(bgcolor="#17212B", font_size=12, font_color="#FFFFFF"),
)


def polish_figure(fig, height=None):
    fig.update_layout(**PLOT_THEME)
    fig.update_xaxes(showgrid=True, gridcolor="#E8EEF4", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#E8EEF4", zeroline=False)
    if height:
        fig.update_layout(height=height)
    return fig


def section_header(title, caption=None):
    st.markdown(f"### {title}")
    if caption:
        st.caption(caption)

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
WEATHER_CSV = "Data/data_cuaca_kemayoran.csv" 
TWITTER_CSV = "Data/data_tweet_harian.csv"

try:
    temp_data = load_weather_data(WEATHER_CSV)
    twitter_data = load_twitter_data(TWITTER_CSV)
except FileNotFoundError as e:
    st.error(f"⚠️ **File CSV Utama Tidak Ditemukan!**")
    st.stop()

# --- FILTER CONTROL (GLOBAL SIDEBAR DATE RANGE) ---
min_date = temp_data['date'].min().date()
max_date = temp_data['date'].max().date()

st.sidebar.subheader("Filter Waktu (berpengaruh ke seluruh halaman proyek)")
date_range = st.sidebar.date_input(
    "Pilih Rentang Tanggal", value=(min_date, max_date), min_value=min_date, max_value=max_date
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_d, end_d = date_range[0], date_range[1]
    filtered_temp = temp_data[(temp_data['date'].dt.date >= start_d) & (temp_data['date'].dt.date <= end_d)].copy()
    filtered_twitter = twitter_data[(twitter_data['date'].dt.date >= start_d) & (twitter_data['date'].dt.date <= end_d)].copy()
else:
    # fallback to full data
    filtered_temp = temp_data.copy()
    filtered_twitter = twitter_data.copy()

# --- TAMPILAN UTAMA PROYEK 1 ---
selected_days = (end_d - start_d).days + 1 if 'start_d' in locals() and 'end_d' in locals() else (max_date - min_date).days + 1
peak_hi = filtered_temp['heat_index_c'].max() if not filtered_temp.empty else np.nan
filtered_tweet_count = len(filtered_twitter)

st.markdown(
    f"""
    <div style="
        background: linear-gradient(135deg, #17212B 0%, #29475A 58%, #E4572E 100%);
        border-radius: 8px;
        padding: 28px 30px;
        margin-bottom: 20px;
        box-shadow: 0 18px 42px rgba(23,33,43,0.18);
    ">
        <div style="color: rgba(255,255,255,0.74); font-size: 0.92rem; font-weight: 650; text-transform: uppercase; letter-spacing: 0;">
            Kemayoran Climate Intelligence
        </div>
        <h1 style="color: #FFFFFF !important; margin: 8px 0 8px; font-size: 2.25rem;">
            Heat Index & Public Response Monitor
        </h1>
        <p style="color: rgba(255,255,255,0.86); max-width: 820px; font-size: 1.02rem; margin: 0;">
            Integrasi parameter fisis atmosfer permukaan dengan dinamika ekspresi masyarakat DKI Jakarta.
        </p>
        <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-top: 20px;">
            <span style="background: rgba(255,255,255,0.14); color: #FFFFFF; border: 1px solid rgba(255,255,255,0.18); border-radius: 999px; padding: 7px 12px; font-weight: 650;">
                {selected_days:,} hari data
            </span>
            <span style="background: rgba(255,255,255,0.14); color: #FFFFFF; border: 1px solid rgba(255,255,255,0.18); border-radius: 999px; padding: 7px 12px; font-weight: 650;">
                Puncak HI {peak_hi:.1f} C
            </span>
            <span style="background: rgba(255,255,255,0.14); color: #FFFFFF; border: 1px solid rgba(255,255,255,0.18); border-radius: 999px; padding: 7px 12px; font-weight: 650;">
                {filtered_tweet_count:,} cuitan terfilter
            </span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

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

# Peta ditempatkan di luar tab sesuai permintaan
section_header("Batas Geografis Representatif", "Radius observasi 15 km dari titik rujukan Kemayoran, Jakarta.")
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
    height=450
)
st.plotly_chart(fig_map, use_container_width=True)

# Menggunakan ikon emoji murni pada penamaan tab agar terhindar dari pemotongan visual teks CSS
tab1, tab_month, tab2, tab3 = st.tabs(["📈 Tren Waktu", "📅 Tren Bulanan & Heatmap", "📊 Karakteristik Respon", "📋 Arsip Data"])

with tab1:
    section_header("Analisis Sinkronisasi Temporal", "Membandingkan perubahan indeks panas dengan volume percakapan harian.")
    if filtered_temp.empty:
        st.warning("Tidak ada data pada rentang tanggal yang dipilih di sidebar.")
    else:
        # daily aggregates
        daily_weather = filtered_temp.groupby(filtered_temp['date'].dt.date).mean(numeric_only=True).reset_index()
        text_col = [col for col in filtered_twitter.columns if 'teks' in col.lower() or 'tweet' in col.lower() or 'text' in col.lower()]
        actual_text_col = text_col[0] if text_col else filtered_twitter.columns[0]
        daily_twitter = filtered_twitter.groupby(filtered_twitter['date'].dt.date).agg(
            jumlah_tweet=(actual_text_col, 'count'),
            total_interaksi=('interaction_score', 'sum')
        ).reset_index()

        merged_daily = pd.merge(daily_weather, daily_twitter, on='date', how='left').fillna(0)
        merged_daily['total_respon'] = merged_daily['jumlah_tweet'] + merged_daily['total_interaksi']

        # 1) Timeseries - Jumlah Cuitan
        fig_count = px.line(
            daily_twitter,
            x='date', y='jumlah_tweet',
            title='Jumlah Cuitan Harian',
            labels={'date': 'Tanggal', 'jumlah_tweet': 'Jumlah Cuitan'},
            template='plotly_white',
            color_discrete_sequence=['#1F77B4']
        )
        polish_figure(fig_count, 340)

        # 2) Timeseries - Jumlah Cuitan + Interaksi (Total Respon)
        fig_count_inter = px.line(
            merged_daily,
            x='date', y='total_respon',
            title='Jumlah Cuitan + Interaksi Harian',
            labels={'date': 'Tanggal', 'total_respon': 'Jumlah + Interaksi'},
            template='plotly_white',
            color_discrete_sequence=['#2CA02C']
        )
        polish_figure(fig_count_inter, 340)

        # 3) Timeseries - Heat Index
        fig_hi = px.line(
            merged_daily,
            x='date', y='heat_index_c',
            title='Heat Index Harian',
            labels={'date': 'Tanggal', 'heat_index_c': 'Indeks Panas (°C)'},
            template='plotly_white',
            color_discrete_sequence=['#E74C3C']
        )
        polish_figure(fig_hi, 340)

        # 4) Korelasi Heat Index vs Jumlah Cuitan
        corr_val = merged_daily['heat_index_c'].corr(merged_daily['jumlah_tweet'])
        corr_text = f"r={corr_val:.2f}" if not np.isnan(corr_val) else 'r=N/A'
        fig_corr = px.scatter(
            merged_daily,
            x='heat_index_c', y='jumlah_tweet',
            title=f'Korelasi Heat Index vs Jumlah Cuitan ({corr_text})',
            labels={'heat_index_c': 'Indeks Panas (°C)', 'jumlah_tweet': 'Jumlah Cuitan'},
            template='plotly_white',
            color_discrete_sequence=['#9467BD']
        )
        fig_corr.update_traces(marker=dict(size=9, opacity=0.78, line=dict(width=1, color="#FFFFFF")))
        polish_figure(fig_corr, 340)

        # Display 4 charts in a 2x2 grid
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(fig_count, use_container_width=True)
        with c2:
            st.plotly_chart(fig_count_inter, use_container_width=True)

        c3, c4 = st.columns(2)
        with c3:
            st.plotly_chart(fig_hi, use_container_width=True)
        with c4:
            st.plotly_chart(fig_corr, use_container_width=True)

        # Summary statistics
        def format_mode(series):
            mode_vals = series.mode()
            if mode_vals.empty:
                return 'N/A'
            return ', '.join([f'{v:.1f}' if isinstance(v, (int, float)) else str(v) for v in mode_vals.tolist()])

        heat_stats = filtered_temp['heat_index_c']
        tweet_stats = merged_daily['jumlah_tweet']

        st.markdown('#### Ringkasan Statistik')
        s1, s2 = st.columns(2)
        with s1:
            st.markdown('**Heat Index (seluruh data terfilter)**')
            st.write(f'- Mean: {heat_stats.mean():.2f} °C')
            st.write(f'- Median: {heat_stats.median():.2f} °C')
            st.write(f'- Mode: {format_mode(heat_stats)}')
            st.write(f'- Min: {heat_stats.min():.2f} °C')
            st.write(f'- Max: {heat_stats.max():.2f} °C')
        with s2:
            st.markdown('**Jumlah Cuitan Harian (agregat)**')
            st.write(f'- Mean: {tweet_stats.mean():.2f}')
            st.write(f'- Median: {tweet_stats.median():.2f}')
            st.write(f'- Mode: {format_mode(tweet_stats)}')
            st.write(f'- Min: {tweet_stats.min():.0f}')
            st.write(f'- Max: {tweet_stats.max():.0f}')

with tab_month:
    section_header("Tren Bulanan dan Peta Panas Jumlah Cuitan", "Melihat pola musiman percakapan publik dan indeks panas.")
    if filtered_twitter.empty:
        st.warning("Tidak ada data cuitan di rentang tanggal terpilih.")
    else:
        # Bulanan: jumlah cuitan per bulan
        twitter_month = filtered_twitter.copy()
        twitter_month['month'] = twitter_month['date'].dt.to_period('M').dt.to_timestamp()
        monthly_counts = twitter_month.groupby('month').size().reset_index(name='jumlah_bulanan')

        fig_monthly = px.line(
            monthly_counts,
            x='month', y='jumlah_bulanan',
            title='Jumlah Cuitan per Bulan',
            labels={'month': 'Bulan', 'jumlah_bulanan': 'Jumlah Cuitan'},
            template='plotly_white',
            color_discrete_sequence=['#1F77B4']
        )
        polish_figure(fig_monthly, 360)
        st.plotly_chart(fig_monthly, use_container_width=True)

        # Grafik rata-rata heat index bulanan
        monthly_temp = filtered_temp.copy()
        monthly_temp['month'] = monthly_temp['date'].dt.to_period('M').dt.to_timestamp()
        avg_hi_monthly = monthly_temp.groupby('month')['heat_index_c'].mean().reset_index()
        fig_monthly_hi = px.line(
            avg_hi_monthly,
            x='month', y='heat_index_c',
            title='Rata-Rata Heat Index Bulanan',
            labels={'month': 'Bulan', 'heat_index_c': 'Heat Index Rata-Rata (°C)'},
            template='plotly_white',
            color_discrete_sequence=['#E74C3C']
        )
        polish_figure(fig_monthly_hi, 340)

        # Grafik korelasi bulanan heat index dan jumlah cuitan
        monthly_twitter = filtered_twitter.copy()
        monthly_twitter['month'] = monthly_twitter['date'].dt.to_period('M').dt.to_timestamp()
        monthly_tweet_count = monthly_twitter.groupby('month').size().reset_index(name='jumlah_bulanan')
        monthly_corr = pd.merge(avg_hi_monthly, monthly_tweet_count, on='month', how='inner')
        corr_val_monthly = monthly_corr['heat_index_c'].corr(monthly_corr['jumlah_bulanan'])
        corr_text_monthly = f"r={corr_val_monthly:.2f}" if not np.isnan(corr_val_monthly) else 'r=N/A'
        fig_corr_monthly = px.scatter(
            monthly_corr,
            x='heat_index_c', y='jumlah_bulanan',
            title=f'Korelasi Bulanan Heat Index vs Jumlah Cuitan ({corr_text_monthly})',
            labels={'heat_index_c': 'Heat Index Rata-Rata (°C)', 'jumlah_bulanan': 'Jumlah Cuitan'},
            template='plotly_white',
            color_discrete_sequence=['#9467BD']
        )
        fig_corr_monthly.update_traces(marker=dict(size=10, opacity=0.78, line=dict(width=1, color="#FFFFFF")))
        polish_figure(fig_corr_monthly, 340)

        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(fig_monthly_hi, use_container_width=True)
        with c2:
            st.plotly_chart(fig_corr_monthly, use_container_width=True)

        # Heatmap per-bulan (tidak terpengaruh sidebar) -> gunakan keseluruhan dataset `twitter_data`
        tw_full = twitter_data.copy()
        tw_full['year'] = tw_full['date'].dt.year
        tw_full['month_num'] = tw_full['date'].dt.month
        monthly_full = tw_full.groupby(['year', 'month_num']).size().reset_index(name='count')
        # Pivot: rows = year, cols = month_num (1..12)
        pivot = monthly_full.pivot_table(index='year', columns='month_num', values='count', fill_value=0)
        if pivot.empty:
            st.info('Tidak ada data bulanan untuk heatmap.')
        else:
            # ensure months ordered 1..12 as columns
            pivot = pivot.reindex(columns=range(1,13), fill_value=0)
            x_labels = [calendar.month_name[m] for m in pivot.columns]
            y_labels = pivot.index.tolist()
            fig_heat = px.imshow(
                pivot.values,
                labels=dict(x='Bulan', y='Tahun', color='Jumlah Cuitan'),
                x=x_labels,
                y=y_labels,
                color_continuous_scale='Reds',
                aspect='auto',
                template='plotly_white'
            )
            polish_figure(fig_heat, 520)
            st.plotly_chart(fig_heat, use_container_width=True)

with tab2:
    section_header("Karakteristik Komparasi Frekuensi Data", "Distribusi indeks termal dan intensitas keterlibatan publik.")
    col_l, col_r = st.columns(2)
    with col_l:
        fig_hist = px.histogram(filtered_temp, x='heat_index_c', title="Kerapatan Distribusi Indeks Termal (°C)", color_discrete_sequence=['#F39C12'], template="plotly_white")
        polish_figure(fig_hist, 380)
        st.plotly_chart(fig_hist, use_container_width=True)
    with col_r:
        daily_interact_bar = filtered_twitter.groupby('date')['interaction_score'].sum().reset_index()
        fig_bar = px.bar(daily_interact_bar, x='date', y='interaction_score', title="Intensitas Keterlibatan Publik Harian", color_discrete_sequence=['#16A085'], template="plotly_white")
        polish_figure(fig_bar, 380)
        st.plotly_chart(fig_bar, use_container_width=True)

with tab3:
    section_header("Cuitan Terpopuler Wilayah Studi", "Cuitan dengan skor interaksi tertinggi pada rentang waktu aktif.")
    text_cols = [col for col in filtered_twitter.columns if 'teks' in col.lower() or 'tweet' in col.lower() or 'text' in col.lower()]
    user_cols = [col for col in filtered_twitter.columns if 'user' in col.lower() or 'nama' in col.lower()]
    rt_cols = [col for col in filtered_twitter.columns if 'retweet' in col.lower()]
    like_cols = [col for col in filtered_twitter.columns if 'like' in col.lower() or 'suka' in col.lower()]
    
    t_key = text_cols[0] if text_cols else filtered_twitter.columns[0]
    u_key = user_cols[0] if user_cols else filtered_twitter.columns[0]
    rt_key = rt_cols[0] if rt_cols else None
    lk_key = like_cols[0] if like_cols else None

    if not filtered_twitter.empty and t_key in filtered_twitter.columns:
        top_tweets = filtered_twitter.nlargest(10, 'interaction_score')
        for _, tweet in top_tweets.iterrows():
            date_str = pd.to_datetime(tweet['date']).strftime('%Y-%m-%d') if 'date' in tweet and not pd.isna(tweet['date']) else ''
            user_name = escape(str(tweet[u_key]))
            tweet_text = escape(str(tweet[t_key]))
            st.markdown(
                f"""
                <div style="background:#FFFFFF; border:1px solid #E6EAF0; border-radius:8px; padding:16px 18px; margin-bottom:12px; box-shadow:0 10px 22px rgba(17,24,39,0.05);">
                    <div style="display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap; color:#667085; font-size:0.9rem;">
                        <strong style="color:#17212B;">@{user_name}</strong>
                        <span>{date_str} | {int(tweet[rt_key]) if rt_key else 0} Retweets | {int(tweet[lk_key]) if lk_key else 0} Likes</span>
                    </div>
                    <div style="color:#293846; margin-top:10px; line-height:1.55;">{tweet_text}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
    section_header("Pengecekan Integritas Dataset")
    with st.expander("Klik untuk Meninjau Data Mentah Historis"):
        choice = st.selectbox("Pilih Tabel Sumber:", ["Meteorologi Dasar per Jam", "Respon Publik Media Sosial"])
        if choice == "Meteorologi Dasar per Jam":
            st.dataframe(filtered_temp, use_container_width=True)
        else:
            st.dataframe(filtered_twitter, use_container_width=True)
