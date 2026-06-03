import streamlit as st
import pandas as pd
import numpy as np
import xarray as xr
import os
import calendar
import tempfile

# --- TENTUKAN PATH DEFAULT UNTUK PENYIMPANAN OTOMATIS ---
OUTPUT_DIR = "Data/archive"

# --- HEADER HALAMAN (TEMA FUTURISTIK / DARK HUD) ---
st.markdown(
    """
    <div style="
        background: linear-gradient(135deg, rgba(16,24,39,0.85) 0%, rgba(30,41,59,0.65) 100%);
        border: 1px solid #1E293B; border-radius: 12px; padding: 25px; margin-bottom: 25px;
        box-shadow: 0 0 20px rgba(0,240,255,0.1); backdrop-filter: blur(10px);
    ">
        <div style="color: #00F0FF; font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 2px;">
            ● Data Engine Core v2.5 | Advanced Schema & Type Cast Matrix
        </div>
        <h2 style="color: #FFFFFF; margin: 8px 0; font-size: 2.2rem; font-weight: 600;">
            UNIVERSAL MET-CLIMATE DATA INGESTION
        </h2>
        <p style="color: #94A3B8; max-width: 800px; font-size: 1.0rem; margin: 0;">
            Modul pengolah data mentah lokal (CSV, XLSX, JSON, NetCDF, GRIB) dengan penanganan tanpa header, transformasi jenis data, rekonstruksi waktu, dan otomatisasi penyimpanan lokal disk.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# --- STEP 1: UNGHAH FILE LOCAL & KONFIGURASI PEMISAH ---
st.markdown("<h3 style='color: #00F0FF;'>📂 Step 1: Ingestion Berkas Lokal</h3>", unsafe_allow_html=True)

# Tambahkan format pendukung di sini
uploaded_file = st.file_uploader(
    "Unggah file data mentah (CSV, XLSX, XLS, TXT, JSON, NC, GRIB, GRB)", 
    type=["csv", "xlsx", "xls", "txt", "json", "nc", "grib", "grb"]
)

if uploaded_file is not None:
    file_name = uploaded_file.name
    st.info(f"Berkas masuk: `{file_name}`")
    
    # 1. Fitur Jalur Deteksi Pemisah & Penanganan Header Kustom (Anti-Error)
    separator = ","
    has_header = True
    
    if file_name.endswith(('.csv', '.txt')):
        st.markdown("**Konfigurasi Parsing Berkas Teks:**")
        hc1, hc2 = st.columns(2)
        with hc1:
            sep_mode = st.radio(
                "Pilih Delimiter Berkas:", 
                ["Koma ( , )", "Titik Koma ( ; )", "Tab ( \\t )", "Spasi Single", "Kustom"],
                horizontal=True
            )
            if sep_mode == "Koma ( , )": separator = ","
            elif sep_mode == "Titik Koma ( ; )": separator = ";"
            elif sep_mode == "Tab ( \\t )": separator = "\t"
            elif sep_mode == "Spasi Single": separator = " "
            else:
                separator = st.text_input("Masukkan karakter pemisah data secara manual:", value=",")
        with hc2:
            has_header = st.checkbox("Berkas memiliki baris header (Nama Kolom asli)", value=True)

# 2. Proses Komputasi Pembacaan Berkas Mentah (DIPERBAIKI)
    try:
        # Format Grid Meteorologi
        if file_name.endswith(('.nc', '.grib', '.grb')):
            suffix_file = os.path.splitext(file_name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix_file) as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name
            
            try:
                engine = 'netcdf4' if file_name.endswith('.nc') else 'cfgrib'
                ds = xr.open_dataset(tmp_file_path, engine=engine)
                df_raw = ds.to_dataframe().reset_index()
                ds.close()
            finally:
                if os.path.exists(tmp_file_path): os.remove(tmp_file_path)

        # Format Teks / CSV
        elif file_name.endswith(('.csv', '.txt')):
            if not has_header:
                df_raw = pd.read_csv(uploaded_file, sep=separator, header=None, engine='python')
                # ... (Logika penamaan header custom tetap sama) ...
            else:
                df_raw = pd.read_csv(uploaded_file, sep=separator, engine='python')
        
        # Format EXCEL (DIPERBAIKI UNTUK XLS DAN XLSX)
        elif file_name.endswith(('.xlsx', '.xls')):
            # engine 'xlrd' untuk .xls, 'openpyxl' untuk .xlsx
            engine = 'xlrd' if file_name.endswith('.xls') else 'openpyxl'
            df_raw = pd.read_excel(uploaded_file, engine=engine)
            
        # Format JSON
        elif file_name.endswith('.json'):
            df_raw = pd.read_json(uploaded_file)
       
        df_raw.columns = df_raw.columns.str.strip()
        st.success(f"Berhasil memuat berkas! Struktur data awal: {df_raw.shape[0]} baris × {df_raw.shape[1]} kolom.")
        
    except Exception as e:
        st.error(f"Gagal memetakan file. Pastikan setelan pemisah atau library dependensi sudah sesuai. Error: {e}")
        st.stop()

    # --- INISIALISASI MEMORI INTERNAL SESSION STATE (UNTUK PRESERVASI DATA MODIFIKASI) ---
    if 'current_file' not in st.session_state or st.session_state['current_file'] != file_name:
        st.session_state['current_file'] = file_name
        st.session_state['df_modified'] = df_raw.copy()

    # Ambil data dasar modifikasi dari memori internal aplikasi
    df_working = st.session_state['df_modified'].copy()

    # --- STEP 2: PRESENTASI DATA MENTAH (RAW INITIAL TABLE) ---
    st.markdown("---")
    st.markdown("<h3 style='color: #00F0FF;'>📋 Step 2: Kondisi Berkas Awal (Sebelum Diolah)</h3>", unsafe_allow_html=True)
    
    col_raw1, col_raw2 = st.columns([3, 1])
    with col_raw1:
        st.markdown("**Tabel Pratinjau Struktur Data Asli (10 Baris Pertama):**")
        st.dataframe(df_raw.head(10), use_container_width=True)
    with col_raw2:
        st.markdown("**Skema Tipe Kolom Asli:**")
        st.dataframe(pd.DataFrame(df_raw.dtypes, columns=["Tipe Berkas"]), use_container_width=True)

    # --- STEP 3: MODIFIKASI, FILTER & KONVERSI DATA PER KOLOM ---
    st.markdown("---")
    st.markdown("<h3 style='color: #00F0FF;'>🛠️ Step 3: Modifikasi & Transformasi Skema Jenis Data</h3>", unsafe_allow_html=True)
    
    col_clean1, col_clean2 = st.columns(2)
    
    with col_clean1:
        st.markdown("**Transformasi Struktur & Jenis Data Kolom:**")
        
        # Fitur Baru: Mengubah jenis data per kolom secara granular
        st.markdown("<span style='color:#00F0FF; font-weight:bold;'>⚙️ Fitur Konversi Jenis Tipe Data:</span>", unsafe_allow_html=True)
        cast_col = st.selectbox("Pilih Target Kolom:", list(df_working.columns))
        target_type = st.selectbox("Konversi Menjadi Jenis:", ["Integer (Angka Bulat / int64)", "Float / Double (Angka Desimal / float64)", "String (Teks / object)", "Datetime (Format Waktu)"])
        
        if st.button("⚡ Eksekusi Konversi Tipe Kolom", use_container_width=True):
            try:
                if target_type == "Integer (Angka Bulat / int64)":
                    st.session_state['df_modified'][cast_col] = pd.to_numeric(st.session_state['df_modified'][cast_col], errors='coerce').fillna(0).astype(np.int64)
                elif target_type == "Float / Double (Angka Desimal / float64)":
                    st.session_state['df_modified'][cast_col] = pd.to_numeric(st.session_state['df_modified'][cast_col], errors='coerce').astype(np.float64)
                elif target_type == "String (Teks / object)":
                    st.session_state['df_modified'][cast_col] = st.session_state['df_modified'][cast_col].astype(str)
                elif target_type == "Datetime (Format Waktu)":
                    st.session_state['df_modified'][cast_col] = pd.to_datetime(st.session_state['df_modified'][cast_col], errors='coerce')
                
                st.success(f"Kolom `{cast_col}` berhasil diubah ke tipe `{target_type}`.")
                st.rerun()
            except Exception as e:
                st.error(f"Gagal melakukan konversi tipe data pada kolom {cast_col}: {e}")

        st.markdown("---")
        # Fitur hapus kolom secara permanen dari memori internal
        columns_to_drop = st.multiselect("Pilih Kolom yang Ingin Dihapus/Dibuang:", list(df_working.columns))
        if st.button("🗑️ Hapus Kolom Terpilih dari Data", use_container_width=True):
            if columns_to_drop:
                st.session_state['df_modified'] = st.session_state['df_modified'].drop(columns=columns_to_drop)
                st.success("Kolom berhasil dieliminasi dari sistem.")
                st.rerun()

        if st.button("🔄 Reset Seluruh Hasil Modifikasi ke Kondisi Mentah", use_container_width=True):
            st.session_state['df_modified'] = df_raw.copy()
            st.success("Data berhasil dikembalikan ke kondisi awal berkas mentah.")
            st.rerun()

    with col_clean2:
        st.markdown("**Filtrasi Amplitudo Nilai & Kebocoran:**")
        
        if st.checkbox("Hapus Baris Duplikat"):
            df_working = df_working.drop_duplicates()

        missing_action = st.radio("Penanganan Baris Kosong (NaN/Null):", ["Biarkan Apa Adanya", "Hapus Seluruh Baris Kosong", "Isi Nilai Kosong dengan Angka 0"])
        if missing_action == "Hapus Seluruh Baris Kosong":
            df_working = df_working.dropna()
        elif missing_action == "Isi Nilai Kosong dengan Angka 0":
            df_working = df_working.fillna(0)

        st.markdown("---")
        filter_col = st.selectbox("Pilih Kolom Utama Basis Filter:", ["-- Tanpa Filter Kolom --"] + list(df_working.columns))
        if filter_col != "-- Tanpa Filter Kolom --":
            if df_working[filter_col].dtype in [np.float64, np.int64]:
                min_val = float(df_working[filter_col].min())
                max_val = float(df_working[filter_col].max())
                if min_val != max_val:
                    filter_range = st.slider(f"Pertahankan Nilai Kolom {filter_col} pada Rentang:", min_val, max_val, (min_val, max_val))
                    df_working = df_working[(df_working[filter_col] >= filter_range[0]) & (df_working[filter_col] <= filter_range[1])]
            else:
                unique_vals = df_working[filter_col].dropna().unique().tolist()
                selected_vals = st.multiselect(f"Pertahankan Karakter Spesifik pada {filter_col}:", unique_vals, default=unique_vals)
                df_working = df_working[df_working[filter_col].isin(selected_vals)]

    # --- STEP 4: REKAYASA AGREGASI TEMPORAL ---
    st.markdown("---")
    st.markdown("<h3 style='color: #00F0FF;'>🧠 Step 4: Rekonstruksi Skala Agregasi Waktu</h3>", unsafe_allow_html=True)
    
    time_col = st.selectbox("Pilih Kolom Indikator Waktu (Wajib bertipe datetime):", ["-- Pilih Kolom Waktu --"] + list(df_working.columns))
    
    if time_col != "-- Pilih Kolom Waktu --":
        # Konversi internal untuk agregasi (jika pengguna belum mengubah tipenya di step 3)
        parsed_time = pd.to_datetime(df_working[time_col], errors='coerce')
        
        if parsed_time.isna().all():
            st.error("Format kolom tidak dikenali sebagai penanda waktu. Silakan gunakan fitur konversi jenis tipe data di Step 3 terlebih dahulu.")
        else:
            st.success("Verifikasi struktur penanda kronologis waktu terintegrasi dengan baik.")
            df_working['parsed_time_core'] = parsed_time
            
            agg_period = st.selectbox(
                "Pilih Level Resolusi Agregasi Data:", 
                ["-- Pertahankan Format Waktu Asli --", "Jam (Hourly)", "Harian (Daily)", "Dasarian (10-Harian BMKG)", "Bulanan (Monthly)", "Tahunan (Yearly)"]
            )
            
            numeric_cols = df_working.select_dtypes(include=[np.number]).columns.tolist()
            if 'parsed_time_core' in numeric_cols: numeric_cols.remove('parsed_time_core')
            
            if agg_period != "-- Pertahankan Format Waktu Asli --" and len(numeric_cols) > 0:
                agg_func = st.radio("Metode Penggabungan Parameter Numerik:", ["Rata-rata (Mean)", "Jumlah Akumulasi (Sum)", "Nilai Ekstrem Maksimum (Max)"], horizontal=True)
                func_map = {"Rata-rata (Mean)": "mean", "Jumlah Akumulasi (Sum)": "sum", "Nilai Ekstrem Maksimum (Max)": "max"}
                
                if agg_period == "Jam (Hourly)":
                    df_working = df_working.groupby(df_working['parsed_time_core'].dt.strftime('%Y-%m-%d %H:00'))[numeric_cols].agg(func_map[agg_func]).reset_index()
                    df_working.rename(columns={'parsed_time_core': 'tanggal_jam'}, inplace=True)
                    
                elif agg_period == "Harian (Daily)":
                    df_working = df_working.groupby(df_working['parsed_time_core'].dt.date)[numeric_cols].agg(func_map[agg_func]).reset_index()
                    df_working.rename(columns={'parsed_time_core': 'tanggal'}, inplace=True)
                    
                elif agg_period == "Dasarian (10-Harian BMKG)":
                    def hitung_dasarian(dt):
                        if pd.isna(dt): return np.nan
                        return 1 if dt.day <= 10 else (2 if dt.day <= 20 else 3)
                        
                    df_working['tahun'] = df_working['parsed_time_core'].dt.year
                    df_working['bulan'] = df_working['parsed_time_core'].dt.month
                    df_working['dasarian'] = df_working['parsed_time_core'].apply(hitung_dasarian)
                    
                    df_working = df_working.groupby(['tahun', 'bulan', 'dasarian'])[numeric_cols].agg(func_map[agg_func]).reset_index()
                    
                elif agg_period == "Bulanan (Monthly)":
                    df_working['tahun'] = df_working['parsed_time_core'].dt.year
                    df_working['bulan'] = df_working['parsed_time_core'].dt.month
                    df_working = df_working.groupby(['tahun', 'bulan'])[numeric_cols].agg(func_map[agg_func]).reset_index()
                    
                elif agg_period == "Tahunan (Yearly)":
                    df_working['tahun'] = df_working['parsed_time_core'].dt.year
                    df_working = df_working.groupby(['tahun'])[numeric_cols].agg(func_map[agg_func]).reset_index()
            
            if 'parsed_time_core' in df_working.columns:
                df_working = df_working.drop(columns=['parsed_time_core'])

    # --- STEP 5: PRESENTASI HASIL AKHIR & AUTO-SAVE KE LOCAL LOCAL DISK ---
    st.markdown("---")
    st.markdown("<h3 style='color: #00F0FF;'>💾 Step 5: Tinjauan Akhir & Ekspor Penyimpanan</h3>", unsafe_allow_html=True)
    
    col_res1, col_res2 = st.columns([3, 1])
    with col_res1:
        st.markdown("**Tabel Data Setelah Di-otak-atik (Pratinjau Hasil Akhir Modifikasi):**")
        st.dataframe(df_working, use_container_width=True)
        st.caption(f"Dimensi Matriks Akhir: {df_working.shape[0]} Baris × {df_working.shape[1]} Kolom")
    with col_res2:
        st.markdown("**Skema Tipe Kolom Akhir:**")
        st.dataframe(pd.DataFrame(df_working.dtypes, columns=["Tipe Baru"]), use_container_width=True)
    
    # Penamaan file output otomatis berbasis nama file input
    base_name = os.path.splitext(file_name)[0]
    output_filename = f"mod_{base_name}.csv"
    full_output_path = os.path.join(OUTPUT_DIR, output_filename)
    
    if st.button("🚀 EXECUTE AUTO-SAVE TO INTERNAL DISK STORAGE", use_container_width=True):
        try:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            df_working.to_csv(full_output_path, index=False)
            st.success(f"💾 Sukses! Berkas modifikasi berhasil disimpan secara otomatis ke lokal komputer pada folder Data.")
            st.code(f"Path Berkas: {os.path.abspath(full_output_path)}", language="text")
        except Exception as e:
            st.error(f"Gagal melakukan auto-save ke direktori lokal disk. Pesan error: {e}")
else:
    st.info("Sistem standby. Silakan unggah berkas instrumen klimatologi atau data publik untuk memulai proses manajemen transformasi data.")