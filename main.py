import streamlit as st

# 1. KONFIGURASI HALAMAN UTAMA
st.set_page_config(
    page_title="CCAH | Command Center",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. CUSTOM CSS (TEMA FUTURISTIK / DARK GLASSMORPHISM)
st.markdown("""
    <style>
    /* Latar Belakang Utama Gelap (Midnight Blue / Cyberpunk Vibe) */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #0B0F19 !important;
        color: #E2E8F0 !important;
    }
    
    /* Sidebar bergaya panel kontrol */
    [data-testid="stSidebar"], [data-testid="stSidebarNav"] {
        background-color: rgba(16, 22, 34, 0.95) !important;
        border-right: 1px solid #1E293B !important;
        backdrop-filter: blur(10px);
    }
    
    /* Teks dan Heading Utama */
    h1, h2, h3 {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
        color: #00F0FF !important; /* Aksen Neon Cyan */
        text-shadow: 0px 0px 8px rgba(0, 240, 255, 0.3);
    }
    p, span, div {
        color: #94A3B8;
    }

    /* KARTU METRIK bergaya Hologram/HUD */
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%) !important;
        padding: 20px !important;
        border-radius: 12px !important;
        border: 1px solid #1E293B !important;
        border-left: 3px solid #00F0FF !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37) !important;
        backdrop-filter: blur(8px);
        transition: all 0.3s ease;
    }
    [data-testid="stMetric"]:hover {
        border-left: 3px solid #FF0055 !important;
        box-shadow: 0 8px 32px 0 rgba(255, 0, 85, 0.2) !important;
    }
    [data-testid="stMetricLabel"] {
        color: #64748B !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    [data-testid="stMetricValue"] {
        color: #F8FAFC !important;
        font-weight: 700 !important;
        font-family: 'Courier New', Courier, monospace !important;
    }

    /* TAB MENU Futuristik */
    button[data-baseweb="tab"] {
        background-color: transparent !important;
    }
    button[data-baseweb="tab"] p {
        color: #64748B !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] p {
        color: #00F0FF !important;
        text-shadow: 0px 0px 10px rgba(0, 240, 255, 0.4);
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        border-bottom: 2px solid #00F0FF !important;
    }

    /* Expander / Tabel */
    div[data-testid="stExpander"] {
        background-color: rgba(15, 23, 42, 0.6) !important;
        border-radius: 10px !important;
        border: 1px solid #1E293B !important;
    }
    </style>
""", unsafe_allow_html=True)

# 3. DEFINISI HALAMAN MULTI-FILE STREAMLIT
halaman_home = st.Page(
    "Page/home.py", 
    title="Dashboard Overview", 
    icon="🏠", 
    default=True
)

halaman_proyek_1 = st.Page(
    "Page/proyek1.py", 
    title="Heat Index & Public Response", 
    icon="📡"
)

halaman_proyek_2 = st.Page(
    "Page/proyek2.py", 
    title="UNIVERSAL MET-CLIMATE DATA INGESTION", 
    icon="⚙️"
)

halaman_proyek_3 = st.Page(
    "Page/proyek3.py", 
    title="(PENGEMBANGAN!!!) Spatial Map Interpolator", 
    icon="🗺️"
)

halaman_proyek_4 = st.Page(
    "Page/proyek4.py",
    title="Spatial Map Interpolator",
    icon="🌧️"
)

# 4. INISIALISASI NAVIGASI
pg = st.navigation({
    "MAIN HUB": [halaman_home],
    "DATA MODULES": [halaman_proyek_1, halaman_proyek_2, halaman_proyek_4]
})

pg.run()