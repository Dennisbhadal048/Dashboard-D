import streamlit as st

# 1. KONFIGURASI HALAMAN UTAMA
st.set_page_config(
    page_title="Cadet Climate Analytics Hub",
    page_icon="🌤️",
    layout="wide"
)

# Custom CSS yang AMAN: Hanya menargetkan kartu metrik & teks spesifik tanpa merusak SVG/Ikon Streamlit
st.markdown("""
    <style>
    /* 1. Latar Belakang Aplikasi Cerah */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #F8F9FA !important;
        color: #1A252F !important;
    }
    
    /* 2. Sidebar Berwarna Putih Bersih */
    [data-testid="stSidebar"], [data-testid="stSidebarNav"] {
        background-color: #1A252F !important;
        border-right: 1px solid #EAEAEA !important;
    }
    
    /* 3. Judul Utama Aplikasi (Target Spesifik) */
    .stApp h1, .stApp h2, .stApp h3 {
        color: #1A252F !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    }
    
    /* 4. PERBAIKAN METRIK: Menembak langsung kelas internal agar teks kontras dan terbaca */
    [data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        padding: 20px !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03) !important;
        border: 1px solid #E6E8EA !important;
    }
    [data-testid="stMetricLabel"] {
        color: #5A6A75 !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetricValue"] {
        color: #2C3E50 !important;
        font-weight: 700 !important;
    }
    
    /* 5. PERBAIKAN TAB MENU: Menggunakan warna kontras tanpa merusak tombol panah geser */
    button[data-baseweb="tab"] p {
        color: #5A6A75 !important;
        font-weight: 600 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] p {
        color: #E74C3C !important;
    }
    
    /* 6. Wadah Tabel Eksplorasi (Expander) */
    div[data-testid="stExpander"] {
        background-color: #FFFFFF !important;
        border-radius: 12px !important;
        border: 1px solid #E6E8EA !important;
    }
    </style>
""", unsafe_allow_html=True)

# 2. DEFINISI HALAMAN MULTI-FILE
halaman_proyek_1 = st.Page(
    "Page/proyek1.py", 
    title="Heat Index & Public Response", 
    icon="🌡️", 
    default=True
)

halaman_proyek_2 = st.Page(
    "Page/proyek2.py", 
    title="Analisis Pemodelan Baru", 
    icon="📊"
)

# 3. INISIALISASI NAVIGASI
pg = st.navigation({
    "🎯 NAVIGATION HUB": [halaman_proyek_1, halaman_proyek_2]
})

pg.run()