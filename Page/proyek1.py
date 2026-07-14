import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import calendar
from html import escape

# --- CUSTOM CSS UNTUK KONTRAS TINGGI & ANTI-TABRAKAN WARNA ---
st.markdown("""
    <style>
    /* 1. Paksa Latar Belakang & Font Utama Aplikasi agar Stabil */
    .stApp {
        background-color: #f8fafc !important;
        color: #0f172a !important;
    }
    
    /* 2. Perbaiki Warna Teks Paragraf & Label Global */
    p, span, label, .stMarkdown div {
        color: #1e293b;
    }

    /* 3. Perbaiki Kontras Tombol Tab Navigasi */
    button[data-baseweb="tab"] {
        color: #475569 !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #00509E !important;
        border-bottom: 3px solid #00509E !important;
    }

    /* 4. Enhancement Metric Box (Latar Putih Bersih, Font Biru/Hitam Pekat) */
    [data-testid="metric-container"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-left: 5px solid #00509E !important;
        padding: 16px 20px !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05) !important;
    }
    [data-testid="metric-container"] label {
        color: #475569 !important;
        font-weight: 700 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase;
    }
    [data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #00509E !important;
        font-size: 1.85rem !important;
        font-weight: 800 !important;
    }

    /* 5. Perbaiki Kotak Expander & Tabel agar Font Tidak Putih */
    [data-testid="stExpander"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
    }
    [data-testid="stExpander"] summary span {
        color: #00509E !important;
        font-weight: 700 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- PLOTLY THEME (SOLID WHITE BACKGROUND AGAR GARIS & FONT JELAS) ---
PLOT_THEME = dict(
    template="plotly_white",
    font=dict(color="#0f172a", family="Inter, 'Segoe UI', sans-serif", size=12),
    paper_bgcolor="#ffffff", # WAJIB PUTIH SOLID (Bukan transparan)
    plot_bgcolor="#ffffff",  # WAJIB PUTIH SOLID AGAR GRID JELAS
    margin=dict(l=40, r=30, t=60, b=40),
    hoverlabel=dict(bgcolor="#ffffff", font_size=13, font_color="#00509E", bordercolor="#cbd5e1"),
)

def polish_figure(fig, height=None):
    fig.update_layout(**PLOT_THEME)
    fig.update_xaxes(
        showgrid=True, gridcolor="#f1f5f9", gridwidth=1.5,
        zeroline=False, showline=True, linecolor="#cbd5e1", linewidth=1.5,
        tickfont=dict(color="#334155", size=11, weight="bold"),
        title_font=dict(color="#0f172a", size=13, family="Segoe UI", weight="bold")
    )
    fig.update_yaxes(
        showgrid=True, gridcolor="#f1f5f9", gridwidth=1.5,
        zeroline=False, showline=True, linecolor="#cbd5e1", linewidth=1.5,
        tickfont=dict(color="#334155", size=11, weight="bold"),
        title_font=dict(color="#0f172a", size=13, family="Segoe UI", weight="bold")
    )
    if height:
        fig.update_layout(height=height)
    return fig

def section_header(title, caption=None):
    st.markdown(f"<h3 style='color: #00509E !important; margin-top: 20px; margin-bottom: 5px; font-weight: 800;'>{title}</h3>", unsafe_allow_html=True)
    if caption:
        st.markdown(f"<p style='color:#475569 !important; font-size:0.95rem; margin-bottom: 18px; font-weight: 500;'>{caption}</p>", unsafe_allow_html=True)

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
        st.error("Kolom Waktu tidak terdeteksi!")
        st.stop()
    temp_col = [col for col in df.columns if 'temp' in col.lower() or 'dry' in col.lower()]
    rh_col = [col for col in df.columns if 'humidity' in col.lower() or 'rh' in col.lower()]
    
    df['air_temperature'] = df[temp_col[0]]
    df['relative_humidity'] = df[rh_col[0]]
    df['heat_index_c'] = calculate_heat_index_vectorized(df['air_temperature'], df['relative_humidity'])
    return df

@st.cache_data
def load_twitter_data(file_path):
    df = pd.read_csv(file_path, sep=None, engine='python')
    df.columns = df.columns.str.strip()
    date_col = [col for col in df.columns if 'tanggal' in col.lower() or 'posting' in col.lower() or 'date' in col.lower()]
    if date_col:
        df['date'] = pd.to_datetime(df[date_col[0]], format='%d/%m/%Y', errors='coerce')
    else:
        st.error("Kolom Tanggal tidak terdeteksi!")
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
except FileNotFoundError:
    st.error("⚠️ **File CSV Utama Tidak Ditemukan! Periksa direktori Data/.**")
    st.stop()

# --- FILTER CONTROL (SIDEBAR) ---
min_date = temp_data['date'].min().date()
max_date = temp_data['date'].max().date()

st.sidebar.markdown("---")
st.sidebar.markdown("<span style='color:#00509E; font-weight:bold; font-size:1rem;'>⚙️ PARAMETER KONTROL</span>", unsafe_allow_html=True)
date_range = st.sidebar.date_input(
    "Rentang Observasi Temporal", value=(min_date, max_date), min_value=min_date, max_value=max_date
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_d, end_d = date_range[0], date_range[1]
    filtered_temp = temp_data[(temp_data['date'].dt.date >= start_d) & (temp_data['date'].dt.date <= end_d)].copy()
    filtered_twitter = twitter_data[(twitter_data['date'].dt.date >= start_d) & (twitter_data['date'].dt.date <= end_d)].copy()
else:
    filtered_temp = temp_data.copy()
    filtered_twitter = twitter_data.copy()

# --- AGREGASI DATA GLOBAL ---
if not filtered_temp.empty:
    daily_weather = filtered_temp.groupby(filtered_temp['date'].dt.date)[['air_temperature', 'relative_humidity', 'heat_index_c']].mean().reset_index()
    
    text_col = [col for col in filtered_twitter.columns if 'teks' in col.lower() or 'tweet' in col.lower() or 'text' in col.lower()]
    actual_text_col = text_col[0] if text_col else filtered_twitter.columns[0]
    daily_twitter = filtered_twitter.groupby(filtered_twitter['date'].dt.date).agg(
        jumlah_tweet=(actual_text_col, 'count'),
        total_interaksi=('interaction_score', 'sum')
    ).reset_index()

    merged_daily = pd.merge(daily_weather, daily_twitter, on='date', how='left').fillna(0)
    merged_daily['total_respon'] = merged_daily['jumlah_tweet'] + merged_daily['total_interaksi']
else:
    merged_daily = pd.DataFrame()

# --- HEADER TAMPILAN (HERO BANNER) ---
selected_days = (end_d - start_d).days + 1 if 'start_d' in locals() and 'end_d' in locals() else (max_date - min_date).days + 1
peak_hi = filtered_temp['heat_index_c'].max() if not filtered_temp.empty else np.nan
filtered_tweet_count = len(filtered_twitter)

st.markdown(
    f"""
    <style>
        .metric-chip {{
            display: inline-block;
            padding: 8px 16px;
            margin: 6px 6px 0 0;
            border-radius: 8px;
            font-weight: 700;
            font-size: 0.85rem;
            border: 2px solid;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
    </style>
    <div style="
        background: linear-gradient(135deg, #00509E 0%, #003366 100%);
        border-radius: 12px; padding: 25px; margin-bottom: 22px;
        box-shadow: 0 6px 18px rgba(0,80,158,0.15); border: 1px solid #003366;
    ">
        <div style="color: #93c5fd !important; font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">
            ● Status: Connected | Kemayoran Station Radar
        </div>
        <h2 style="color: #ffffff !important; margin: 0 0 12px 0; font-size: 1.8rem; font-weight: 800; text-shadow: 0 2px 4px rgba(0,0,0,0.4);">
            ANALISIS INDEKS TERMAL & VALIDASI SOSIAL
        </h2>
        <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px;">
            <span class="metric-chip" style="background: #ffffff !important; color: #00509E !important; border-color: #93c5fd !important;">⏱️ TIME WINDOW: {selected_days:,} DAYS</span>
            <span class="metric-chip" style="background: #fee2e2 !important; color: #991b1b !important; border-color: #f87171 !important;">🔴 PEAK HI: {peak_hi:.1f} °C</span>
            <span class="metric-chip" style="background: #dcfce7 !important; color: #166534 !important; border-color: #4ade80 !important;">💬 TOTAL CUITAN: {filtered_tweet_count:,}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# --- METRIK HUD UTAMA ---
m1, m2, m3, m4 = st.columns(4)
with m1:
    if not filtered_temp.empty: st.metric("Rata-rata Suhu", f"{filtered_temp['air_temperature'].mean():.1f} °C")
with m2:
    if not filtered_temp.empty: st.metric("Rata-rata Heat Index", f"{filtered_temp['heat_index_c'].mean():.1f} °C")
with m3:
    st.metric("Total Sampel Cuitan", f"{len(filtered_twitter):,}")
with m4:
    st.metric("Akumulasi Interaksi", f"{filtered_twitter['interaction_score'].sum():,}")

# --- PEMBAGIAN TAB KONTROL ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 TREN HARIAN", 
    "📅 ANALISIS BULANAN", 
    "🏆 TOP 10 LOG TWEET", 
    "🔬 METODOLOGI & DATA"
])

# ==================== TAB 1: ANALISIS HARIAN ====================
with tab1:
    section_header("Sinkronisasi Temporal Harian", "Analisis runtun waktu parameter fisis atmosfer versus volume cuitan publik per hari.")
    
    if merged_daily.empty:
        st.warning("Tidak ada data pada rentang waktu yang dipilih.")
    else:
        # Grafik Harian dengan Garis Tebal & Warna Kontras
        fig_count = px.line(merged_daily, x='date', y='jumlah_tweet', title='Volume Cuitan Harian (Indikator Utama)')
        fig_count.update_traces(line=dict(width=3, color='#00509E'))
        polish_figure(fig_count, 320)
        
        fig_hi = px.line(merged_daily, x='date', y='heat_index_c', title='Fluktuasi Indeks Termal Harian (°C)')
        fig_hi.update_traces(line=dict(width=3, color='#dc2626'))
        polish_figure(fig_hi, 320)

        corr_val = merged_daily['heat_index_c'].corr(merged_daily['jumlah_tweet'])
        corr_text = f"r = {corr_val:.2f}" if not np.isnan(corr_val) else 'r = N/A'
        
        fig_corr = px.scatter(merged_daily, x='heat_index_c', y='jumlah_tweet', title=f'Korelasi Scatter Harian ({corr_text})', trendline="ols")
        fig_corr.update_traces(marker=dict(size=8, color='#7c3aed', opacity=0.8, line=dict(width=1, color='#4c1d95')))
        polish_figure(fig_corr, 320)
        
        fig_count_inter = px.line(merged_daily, x='date', y='total_respon', title='Aktivitas Akumulasi Interaksi (Rentang Bias)')
        fig_count_inter.update_traces(line=dict(width=3, color='#059669'))
        polish_figure(fig_count_inter, 320)

        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(fig_count, use_container_width=True)
        with c2: st.plotly_chart(fig_hi, use_container_width=True)

        c3, c4 = st.columns(2)
        with c3: st.plotly_chart(fig_corr, use_container_width=True)
        with c4: st.plotly_chart(fig_count_inter, use_container_width=True)

        st.markdown("<br><h4 style='color:#00509E !important; font-weight:700;'>📋 Ringkasan Statistik Deskriptif Harian</h4>", unsafe_allow_html=True)
        s1, s2 = st.columns(2)
        with s1:
            st.markdown("""
            <div style="background:#ffffff; padding:15px; border:1px solid #cbd5e1; border-radius:8px; color:#0f172a;">
                <strong style="color:#00509E;">🌡️ Parameter Fisis (Heat Index Harian):</strong><br><br>
                • Rata-rata (Mean): <b>{mean:.2f} °C</b><br>
                • Nilai Tengah (Median): <b>{median:.2f} °C</b><br>
                • Minimum: <b>{min:.2f} °C</b><br>
                • Maksimum: <b>{max:.2f} °C</b>
            </div>
            """.format(
                mean=merged_daily['heat_index_c'].mean(),
                median=merged_daily['heat_index_c'].median(),
                min=merged_daily['heat_index_c'].min(),
                max=merged_daily['heat_index_c'].max()
            ), unsafe_allow_html=True)
        with s2:
            st.markdown("""
            <div style="background:#ffffff; padding:15px; border:1px solid #cbd5e1; border-radius:8px; color:#0f172a;">
                <strong style="color:#00509E;">💬 Parameter Sosial (Volume Cuitan Harian):</strong><br><br>
                • Rata-rata (Mean): <b>{mean:.1f} Tweet/hari</b><br>
                • Nilai Tengah (Median): <b>{median:.1f} Tweet/hari</b><br>
                • Standar Deviasi: <b>{std:.1f}</b><br>
                • Puncak Cuitan Tertinggi: <b>{max} Tweet</b>
            </div>
            """.format(
                mean=merged_daily['jumlah_tweet'].mean(),
                median=merged_daily['jumlah_tweet'].median(),
                std=merged_daily['jumlah_tweet'].std(),
                max=merged_daily['jumlah_tweet'].max()
            ), unsafe_allow_html=True)

# ==================== TAB 2: ANALISIS BULANAN ====================
with tab2:
    section_header("Karakteristik & Pola Makro Bulanan", "Agregasi jangka panjang untuk melihat tren musiman dan anomali bulanan.")
    
    if filtered_twitter.empty:
        st.warning("Tidak ada data untuk analisis bulanan.")
    else:
        twitter_month = filtered_twitter.copy()
        twitter_month['month'] = twitter_month['date'].dt.to_period('M').dt.to_timestamp()
        monthly_counts = twitter_month.groupby('month').size().reset_index(name='jumlah_bulanan')

        monthly_temp = filtered_temp.copy()
        monthly_temp['month'] = monthly_temp['date'].dt.to_period('M').dt.to_timestamp()
        avg_hi_monthly = monthly_temp.groupby('month')['heat_index_c'].mean().reset_index()

        merged_monthly = pd.merge(avg_hi_monthly, monthly_counts, on='month', how='inner')

        fig_monthly = px.line(merged_monthly, x='month', y='jumlah_bulanan', title='Akumulasi Volume Cuitan per Bulan', markers=True)
        fig_monthly.update_traces(line=dict(width=3.5, color='#00509E'), marker=dict(size=8, color='#00509E'))
        polish_figure(fig_monthly, 340)
        
        fig_monthly_hi = px.line(merged_monthly, x='month', y='heat_index_c', title='Rata-Rata Bulanan Heat Index (°C)', markers=True)
        fig_monthly_hi.update_traces(line=dict(width=3.5, color='#dc2626'), marker=dict(size=8, color='#dc2626'))
        polish_figure(fig_monthly_hi, 340)
        
        corr_m = merged_monthly['heat_index_c'].corr(merged_monthly['jumlah_bulanan'])
        fig_corr_m = px.scatter(merged_monthly, x='heat_index_c', y='jumlah_bulanan', title=f'Korelasi Tingkat Bulanan (r = {corr_m:.2f})', trendline="ols")
        fig_corr_m.update_traces(marker=dict(size=9, color='#7c3aed', opacity=0.9, line=dict(width=1.5, color='#4c1d95')))
        polish_figure(fig_corr_m, 340)

        tw_full = twitter_data.copy()
        tw_full['year'] = tw_full['date'].dt.year
        tw_full['month_num'] = tw_full['date'].dt.month
        monthly_full = tw_full.groupby(['year', 'month_num']).size().reset_index(name='count')
        pivot = monthly_full.pivot_table(index='year', columns='month_num', values='count', fill_value=0)
        
        if not pivot.empty:
            pivot = pivot.reindex(columns=range(1,13), fill_value=0)
            x_labels = [calendar.month_abbr[m] for m in pivot.columns]
            fig_heat = px.imshow(pivot.values, x=x_labels, y=pivot.index.tolist(), color_continuous_scale='Blues', aspect='auto')
            fig_heat.update_layout(title="Matriks Kepadatan Volume Cuitan Historis (Tahun vs Bulan)")
            polish_figure(fig_heat, 340)

        cx1, cx2 = st.columns(2)
        with cx1: st.plotly_chart(fig_monthly, use_container_width=True)
        with cx2: st.plotly_chart(fig_monthly_hi, use_container_width=True)

        cx3, cx4 = st.columns(2)
        with cx3: st.plotly_chart(fig_corr_m, use_container_width=True)
        with cx4: st.plotly_chart(fig_heat, use_container_width=True)

        st.markdown("<br><h4 style='color:#00509E !important; font-weight:700;'>📋 Ringkasan Statistik Deskriptif Bulanan</h4>", unsafe_allow_html=True)
        sb1, sb2 = st.columns(2)
        with sb1:
            st.markdown("""
            <div style="background:#ffffff; padding:15px; border:1px solid #cbd5e1; border-radius:8px; color:#0f172a;">
                <strong style="color:#00509E;">📊 Statistik Heat Index Bulanan:</strong><br><br>
                • Rata-rata Nilai Bulanan: <b>{mean:.2f} °C</b><br>
                • Standar Deviasi Bulanan: <b>{std:.2f} °C</b>
            </div>
            """.format(mean=merged_monthly['heat_index_c'].mean(), std=merged_monthly['heat_index_c'].std()), unsafe_allow_html=True)
        with sb2:
            st.markdown("""
            <div style="background:#ffffff; padding:15px; border:1px solid #cbd5e1; border-radius:8px; color:#0f172a;">
                <strong style="color:#00509E;">📈 Statistik Volume Cuitan Bulanan:</strong><br><br>
                • Rata-rata Volume Bulanan: <b>{mean:.1f} Tweet/bulan</b><br>
                • Total Akumulasi Terpilih: <b>{sum:,} Tweet</b>
            </div>
            """.format(mean=merged_monthly['jumlah_bulanan'].mean(), sum=merged_monthly['jumlah_bulanan'].sum()), unsafe_allow_html=True)

# ==================== TAB 3: TOP 10 LOG TWEET ====================
with tab3:
    section_header("Terminal Arsip Log Cuitan Terpopuler", "10 sampel cuitan masyarakat dengan skor interaksi (hype) tertinggi sebagai bahan kendali bias data.")
    
    text_cols = [col for col in filtered_twitter.columns if 'teks' in col.lower() or 'tweet' in col.lower() or 'text' in col.lower()]
    user_cols = [col for col in filtered_twitter.columns if 'user' in col.lower() or 'nama' in col.lower()]
    rt_cols = [col for col in filtered_twitter.columns if 'retweet' in col.lower()]
    like_cols = [col for col in filtered_twitter.columns if 'like' in col.lower() or 'suka' in col.lower()]
    
    t_key = text_cols[0] if text_cols else filtered_twitter.columns[0]
    u_key = user_cols[0] if user_cols else filtered_twitter.columns[0]
    rt_key = rt_cols[0] if rt_cols else None
    lk_key = like_cols[0] if like_cols else None

    if not filtered_twitter.empty and t_key in filtered_twitter.columns:
        top_10_tweets = filtered_twitter.nlargest(10, 'interaction_score')
        
        for rank, (_, tweet) in enumerate(top_10_tweets.iterrows(), 1):
            date_str = pd.to_datetime(tweet['date']).strftime('%Y-%m-%d') if 'date' in tweet and not pd.isna(tweet['date']) else ''
            user_name = escape(str(tweet[u_key]))
            tweet_text = escape(str(tweet[t_key]))
            interaction = int(tweet['interaction_score'])
            
            st.markdown(
                f"""
                <div style="
                    background: #ffffff !important; 
                    border: 1px solid #cbd5e1 !important; 
                    border-left: 5px solid #00509E !important; 
                    border-radius: 8px; padding: 16px; margin-bottom: 14px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                ">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-family: monospace; font-size: 0.95rem;">
                        <span style="color: #00509E !important; font-weight: 700;">RANK #{rank} @{user_name}</span>
                        <span style="color: #475569 !important; font-weight: 600;">{date_str} | 🔥 Score: {interaction:,} (🔁 {int(tweet[rt_key]) if rt_key else 0} | ❤️ {int(tweet[lk_key]) if lk_key else 0})</span>
                    </div>
                    <div style="color: #0f172a !important; line-height: 1.6; font-size: 1rem; font-style: italic; background: #f8fafc !important; padding: 12px; border-radius: 6px; border: 1px dashed #cbd5e1;">
                        "{tweet_text}"
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

# ==================== TAB 4: METODOLOGI & DATA ====================
with tab4:
    section_header("Dokumentasi Metodologi & Sumber Data", "Formulasi fisik matematika indeks termal dan verifikasi integritas struktur berkas berkas yang digunakan.")
    
    st.markdown("#### 🔬 Formulasi Fisis (Persamaan Kompleks Regresi Rothfusz)")
    st.latex(r"HI = c_1 + c_2T + c_3R + c_4TR + c_5T^2 + c_6R^2 + c_7T^2R + c_8TR^2 + c_9T^2R^2")
    
    st.markdown("#### 📐 Persamaan Pendekatan Sederhana (*Simple Equation*)")
    st.latex(r"HI_{\text{simple}} = 0.5 \times \left[T + 61.0 + ((T - 68.0) \times 1.2) + (R \times 0.094)\right]")
    
    st.markdown("""
    **Keterangan Variabel & Konstanta Konversi:**
    * $HI$ = *Heat Index* / Indeks Panas fisis ($^{\circ}\\text{C}$).
    * $T$ = Temperatur udara permukaan hasil konversi ke unit Fahrenheit ($^{\circ}\\text{F} = \\frac{9}{5}T_{\\text{C}} + 32$).
    * $R$ = Kelembapan Relatif / *Relative Humidity* ($RH$) dalam format persentase skala basis 100.
    * Matriks konstanta empiris fisis:
    """)
    
    st.code("""
    c1 = -42.379      c2 = 2.04901523   c3 = 10.14333127
    c4 = -0.22475541  c5 = -0.00683783  c6 = -0.05481717
    c7 = 0.00122874   c8 = 0.00085282   c9 = -0.00000199
    """, language="python")

    st.markdown("<br>#### 🔍 Peninjauan Integrasi Dataset Tergabung", unsafe_allow_html=True)
    if not merged_daily.empty:
        with st.expander("Klik untuk Meninjau Matriks Gabungan Variabel Harian"):
            display_df = merged_daily[['date', 'air_temperature', 'relative_humidity', 'heat_index_c', 'jumlah_tweet']].copy()
            display_df.columns = ['tanggal', 'air_temperature', 'relative_humidity', 'heat_index', 'jumlah cuitan harian']
            
            st.dataframe(display_df, use_container_width=True)
    else:
        st.warning("Gagal memuat matriks gabungan karena tidak ada data pada filter waktu terpilih.")