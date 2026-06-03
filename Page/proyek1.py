import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import calendar
from html import escape

# --- TEMA PLOTLY FUTURISTIK (DARK MODE) ---
PLOT_THEME = dict(
    template="plotly_dark",
    font=dict(color="#94A3B8", family="Segoe UI"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=30, r=25, t=55, b=30),
    hoverlabel=dict(bgcolor="#0F172A", font_size=12, font_color="#00F0FF", bordercolor="#00F0FF"),
)

def polish_figure(fig, height=None):
    fig.update_layout(**PLOT_THEME)
    fig.update_xaxes(showgrid=True, gridcolor="#1E293B", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#1E293B", zeroline=False)
    if height:
        fig.update_layout(height=height)
    return fig

def section_header(title, caption=None):
    st.markdown(f"<h3 style='color: #00F0FF; margin-top: 20px; margin-bottom: 5px;'>{title}</h3>", unsafe_allow_html=True)
    if caption:
        st.markdown(f"<p style='color:#64748B; font-size:0.95rem; margin-bottom: 15px;'>{caption}</p>", unsafe_allow_html=True)

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
    
    # Standarisasi penamaan kolom fisis asli
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
st.sidebar.markdown("<span style='color:#00F0FF; font-weight:bold;'>⚙️ PARAMETER KONTROL</span>", unsafe_allow_html=True)
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

# --- AGREGASI DATA GLOBAL (PENTING: Dipakai Bersama oleh Tab 1, Tab 2, dan Tab 4) ---
if not filtered_temp.empty:
    # Agregat harian parameter cuaca (mean)
    daily_weather = filtered_temp.groupby(filtered_temp['date'].dt.date)[['air_temperature', 'relative_humidity', 'heat_index_c']].mean().reset_index()
    
    # Kuantifikasi harian parameter sosial
    text_col = [col for col in filtered_twitter.columns if 'teks' in col.lower() or 'tweet' in col.lower() or 'text' in col.lower()]
    actual_text_col = text_col[0] if text_col else filtered_twitter.columns[0]
    daily_twitter = filtered_twitter.groupby(filtered_twitter['date'].dt.date).agg(
        jumlah_tweet=(actual_text_col, 'count'),
        total_interaksi=('interaction_score', 'sum')
    ).reset_index()

    # Penggabungan dataframe harian secara utuh
    merged_daily = pd.merge(daily_weather, daily_twitter, on='date', how='left').fillna(0)
    merged_daily['total_respon'] = merged_daily['jumlah_tweet'] + merged_daily['total_interaksi']
else:
    merged_daily = pd.DataFrame()

# --- HEADER TAMPILAN ---
selected_days = (end_d - start_d).days + 1 if 'start_d' in locals() and 'end_d' in locals() else (max_date - min_date).days + 1
peak_hi = filtered_temp['heat_index_c'].max() if not filtered_temp.empty else np.nan
filtered_tweet_count = len(filtered_twitter)

st.markdown(
    f"""
    <div style="
        background: linear-gradient(135deg, rgba(16,24,39,0.85) 0%, rgba(30,41,59,0.65) 100%);
        border: 1px solid #1E293B; border-radius: 12px; padding: 25px; margin-bottom: 25px;
        box-shadow: 0 0 20px rgba(0,240,255,0.1); backdrop-filter: blur(10px);
    ">
        <div style="color: #00F0FF; font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 2px;">
            ● Telemetry Status: Connected | Kemayoran Station Radar
        </div>
        <h2 style="color: #FFFFFF; margin: 8px 0; font-size: 2.2rem; font-weight: 600;">
            ANALISIS INDEKS TERMAL & VALIDASI SOSIAL
        </h2>
        <div style="display: flex; gap: 15px; flex-wrap: wrap; margin-top: 15px;">
            <span style="background: rgba(0,240,255,0.1); color: #00F0FF; border: 1px solid rgba(0,240,255,0.3); border-radius: 4px; padding: 4px 10px; font-family: monospace; font-size:0.85rem;">
                TIME WINDOW: {selected_days:,} DAYS
            </span>
            <span style="background: rgba(255,0,85,0.1); color: #FF0055; border: 1px solid rgba(255,0,85,0.3); border-radius: 4px; padding: 4px 10px; font-family: monospace; font-size:0.85rem;">
                PEAK HI: {peak_hi:.1f} °C
            </span>
            <span style="background: rgba(0,255,136,0.1); color: #00FF88; border: 1px solid rgba(0,255,136,0.3); border-radius: 4px; padding: 4px 10px; font-family: monospace; font-size:0.85rem;">
                TOTAL CUITAN: {filtered_tweet_count:,} ROWS
            </span>
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
        # Grafik Utama Harian
        fig_count = px.line(merged_daily, x='date', y='jumlah_tweet', title='Volume Cuitan Harian (Indikator Utama)', color_discrete_sequence=['#00F0FF'])
        polish_figure(fig_count, 300)

        fig_hi = px.line(merged_daily, x='date', y='heat_index_c', title='Fluktuasi Indeks Termal Harian (°C)', color_discrete_sequence=['#FF0055'])
        polish_figure(fig_hi, 300)

        corr_val = merged_daily['heat_index_c'].corr(merged_daily['jumlah_tweet'])
        corr_text = f"r = {corr_val:.2f}" if not np.isnan(corr_val) else 'r = N/A'
        fig_corr = px.scatter(merged_daily, x='heat_index_c', y='jumlah_tweet', title=f'Korelasi Scatter Harian ({corr_text})', color_discrete_sequence=['#B900FF'], trendline="ols")
        polish_figure(fig_corr, 300)

        fig_count_inter = px.line(merged_daily, x='date', y='total_respon', title='Aktivitas Akumulasi Interaksi (Informasi Tambahan - Rentan Bias)', color_discrete_sequence=['#00FF88'])
        polish_figure(fig_count_inter, 300)

        # Layout Grid Grafik Harian
        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(fig_count, use_container_width=True)
        with c2: st.plotly_chart(fig_hi, use_container_width=True)

        c3, c4 = st.columns(2)
        with c3: st.plotly_chart(fig_corr, use_container_width=True)
        with c4: st.plotly_chart(fig_count_inter, use_container_width=True)

        # Deskripsi Statistik Harian
        st.markdown("<br><h4 style='color:#00F0FF;'>📋 Ringkasan Statistik Deskriptif Harian</h4>", unsafe_allow_html=True)
        s1, s2 = st.columns(2)
        with s1:
            st.markdown("**Parameter Fisis (Heat Index Harian):**")
            st.write(f"- Rata-rata (Mean): {merged_daily['heat_index_c'].mean():.2f} °C")
            st.write(f"- Nilai Tengah (Median): {merged_daily['heat_index_c'].median():.2f} °C")
            st.write(f"- Minimum: {merged_daily['heat_index_c'].min():.2f} °C")
            st.write(f"- Maksimum: {merged_daily['heat_index_c'].max():.2f} °C")
        with s2:
            st.markdown("**Parameter Sosial (Volume Cuitan Harian):**")
            st.write(f"- Rata-rata (Mean): {merged_daily['jumlah_tweet'].mean():.1f} Tweet/hari")
            st.write(f"- Nilai Tengah (Median): {merged_daily['jumlah_tweet'].median():.1f} Tweet/hari")
            st.write(f"- Standar Deviasi: {merged_daily['jumlah_tweet'].std():.1f}")
            st.write(f"- Puncak Cuitan Tertinggi: {merged_daily['jumlah_tweet'].max()} Tweet")

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

        # Grafik Bulanan
        fig_monthly = px.line(merged_monthly, x='month', y='jumlah_bulanan', title='Akumulasi Volume Cuitan per Bulan', color_discrete_sequence=['#00F0FF'], markers=True)
        polish_figure(fig_monthly, 320)

        fig_monthly_hi = px.line(merged_monthly, x='month', y='heat_index_c', title='Rata-Rata Bulanan Heat Index (°C)', color_discrete_sequence=['#FF0055'], markers=True)
        polish_figure(fig_monthly_hi, 320)

        corr_m = merged_monthly['heat_index_c'].corr(merged_monthly['jumlah_bulanan'])
        fig_corr_m = px.scatter(merged_monthly, x='heat_index_c', y='jumlah_bulanan', title=f'Korelasi Tingkat Bulanan (r = {corr_m:.2f})', color_discrete_sequence=['#B900FF'], trendline="ols")
        polish_figure(fig_corr_m, 320)

        # HEATMAP PERBAIKAN: Menggunakan skala warna 'Reds' agar perbedaan kontras terlihat jelas
        tw_full = twitter_data.copy()
        tw_full['year'] = tw_full['date'].dt.year
        tw_full['month_num'] = tw_full['date'].dt.month
        monthly_full = tw_full.groupby(['year', 'month_num']).size().reset_index(name='count')
        pivot = monthly_full.pivot_table(index='year', columns='month_num', values='count', fill_value=0)
        
        if not pivot.empty:
            pivot = pivot.reindex(columns=range(1,13), fill_value=0)
            x_labels = [calendar.month_abbr[m] for m in pivot.columns]
            fig_heat = px.imshow(pivot.values, x=x_labels, y=pivot.index.tolist(), color_continuous_scale='Reds', aspect='auto')
            fig_heat.update_layout(title="Matriks Kepadatan Volume Cuitan Historis (Tahun vs Bulan)")
            polish_figure(fig_heat, 320)

        # Layout Grid Grafik Bulanan
        cx1, cx2 = st.columns(2)
        with cx1: st.plotly_chart(fig_monthly, use_container_width=True)
        with cx2: st.plotly_chart(fig_monthly_hi, use_container_width=True)

        cx3, cx4 = st.columns(2)
        with cx3: st.plotly_chart(fig_corr_m, use_container_width=True)
        with cx4: st.plotly_chart(fig_heat, use_container_width=True)

        # Deskripsi Statistik Bulanan
        st.markdown("<br><h4 style='color:#00F0FF;'>📋 Ringkasan Statistik Deskriptif Bulanan</h4>", unsafe_allow_html=True)
        sb1, sb2 = st.columns(2)
        with sb1:
            st.markdown("**Statistik Heat Index Bulanan:**")
            st.write(f"- Rata-rata Nilai Bulanan: {merged_monthly['heat_index_c'].mean():.2f} °C")
            st.write(f"- Standar Deviasi Bulanan: {merged_monthly['heat_index_c'].std():.2f} °C")
        with sb2:
            st.markdown("**Statistik Volume Cuitan Bulanan:**")
            st.write(f"- Rata-rata Volume Bulanan: {merged_monthly['jumlah_bulanan'].mean():.1f} Tweet/bulan")
            st.write(f"- Total Akumulasi Terpilih: {merged_monthly['jumlah_bulanan'].sum():,} Tweet")

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
                    background: rgba(15, 23, 42, 0.6); 
                    border: 1px solid #1E293B; 
                    border-left: 4px solid #00F0FF; 
                    border-radius: 8px; padding: 15px; margin-bottom: 12px;
                ">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-family: monospace; font-size: 0.9rem;">
                        <span style="color: #00F0FF; font-weight: bold;">RANK #{rank} @{user_name}</span>
                        <span style="color: #64748B;">{date_str} | 🔥 Score: {interaction:,} (🔁 {int(tweet[rt_key]) if rt_key else 0} | ❤️ {int(tweet[lk_key]) if lk_key else 0})</span>
                    </div>
                    <div style="color: #E2E8F0; line-height: 1.5; font-style: italic;">"{tweet_text}"</div>
                </div>
                """,
                unsafe_allow_html=True
            )

# ==================== TAB 4: METODOLOGI & DATA ====================
with tab4:
    section_header("Dokumentasi Metodologi & Sumber Data", "Formulasi fisik matematika indeks termal dan verifikasi integritas struktur berkas berkas yang digunakan.")
    
    # PERBAIKAN LATEX: Notasi matematika dibersihkan agar rendering simbol presisi
    st.markdown("#### 🔬 Formulasi Fisis (Persamaan Kompleks Regresi Rothfusz)")
    st.latex(r"HI = c_1 + c_2T + c_3R + c_4TR + c_5T^2 + c_6R^2 + c_7T^2R + c_8TR^2 + c_9T^2R^2")
    
    st.markdown("#### 📐 Persamaan Pendekatan Sederhana (*Simple Equation*)")
    st.latex(r"HI_{\text{simple}} = 0.5 \times \left[T + 61.0 + ((T - 68.0) \times 1.2) + (R \times 0.094)\right]")
    
    st.markdown("""
    **Keterangan Variabel & Konstanta Konversi:**
    * $HI$ = *Heat Index* / Indeks Panas fisis ($^{\circ}\text{C}$).
    * $T$ = Temperatur udara permukaan hasil konversi ke unit Fahrenheit ($^{\circ}\text{F} = \frac{9}{5}T_{\text{C}} + 32$).
    * $R$ = Kelembapan Relatif / *Relative Humidity* ($RH$) dalam format persentase skala basis 100.
    * Matriks konstanta empiris fisis:
    """)
    
    st.code("""
    c1 = -42.379      c2 = 2.04901523   c3 = 10.14333127
    c4 = -0.22475541  c5 = -0.00683783  c6 = -0.05481717
    c7 = 0.00122874   c8 = 0.00085282   c9 = -0.00000199
    """, language="python")

    # PERBAIKAN DATA MENTAH: Menampilkan DataFrame gabungan harian yang bersih sesuai request
    st.markdown("<br>#### 🔍 Peninjauan Integrasi Dataset Tergabung", unsafe_allow_html=True)
    if not merged_daily.empty:
        with st.expander("Klik untuk Meninjau Matriks Gabungan Variabel Harian"):
            # Seleksi dan penataan ulang nama kolom sesuai permintaan
            display_df = merged_daily[['date', 'air_temperature', 'relative_humidity', 'heat_index_c', 'jumlah_tweet']].copy()
            display_df.columns = ['tanggal', 'air_temperature', 'relative_humidity', 'heat_index', 'jumlah cuitan harian']
            
            st.dataframe(display_df, use_container_width=True)
    else:
        st.warning("Gagal memuat matriks gabungan karena tidak ada data pada filter waktu terpilih.")