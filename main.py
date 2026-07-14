import os
import streamlit as st

st.set_page_config(
    page_title="Portal Analisis Data Taruna",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --bmkg-blue: #00509E;
        --bmkg-dark: #003366;
        --bmkg-soft: #eef6fc;
        --text: #0f172a;
        --muted: #64748b;
    }
    .stApp {
        background: linear-gradient(180deg, #f8fbff 0%, #f4f8fc 100%) !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    }
    [data-testid="stMainBlockContainer"] {
        padding-top: 0.5rem;
        padding-bottom: 2rem;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%) !important;
        border-right: 1px solid #dbeafe !important;
        box-shadow: 2px 0 18px rgba(2, 6, 23, 0.04) !important;
    }
    [data-testid="stSidebarContent"] {
        padding-top: 0.75rem;
    }
    [data-testid="stSidebarNav"] a {
        border-radius: 10px;
        padding: 0.7rem 0.8rem;
        margin: 0.15rem 0;
        color: var(--text) !important;
        font-weight: 500;
    }
    [data-testid="stSidebarNav"] a:hover {
        background: #eff6ff !important;
        color: var(--bmkg-blue) !important;
    }
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background: linear-gradient(135deg, var(--bmkg-blue), var(--bmkg-dark)) !important;
        color: white !important;
        font-weight: 600;
    }
    .stButton > button {
        background: linear-gradient(135deg, var(--bmkg-blue), var(--bmkg-dark));
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.45rem 0.9rem;
        box-shadow: 0 4px 10px rgba(0, 80, 158, 0.18);
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #0a5db8, #002b4d);
        color: white;
    }
    h1, h2, h3 {
        color: var(--bmkg-blue) !important;
        font-weight: 700 !important;
    }
    p, span, label {
        color: var(--text) !important;
    }
    .app-footer {
        margin-top: 2rem;
        padding: 0.9rem 1rem;
        border-top: 1px solid #e2e8f0;
        color: var(--muted);
        font-size: 0.9rem;
        text-align: center;
    }
    .sidebar-brand-card {
        width: 100%;
        padding: 0.8rem 0.75rem 0.7rem;
        border-radius: 16px;
        background: linear-gradient(135deg, #f5faff 0%, #eef3ff 100%);
        border: 1px solid #dbeafe;
        box-shadow: 0 6px 16px rgba(2, 6, 23, 0.04);
    }
    .sidebar-logo-frame {
        width: 100%;
        max-width: 170px;
        margin: 0.2rem auto 0.6rem;
        padding: 0.45rem;
        border-radius: 14px;
        background: #ffffff;
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 110px;
    }
    .sidebar-logo-frame img {
        max-width: 100%;
        max-height: 100px;
        object-fit: contain;
    }
    .sidebar-brand-title {
        font-size: 0.76rem;
        font-weight: 800;
        letter-spacing: 0.18em;
        color: #00509E;
        text-transform: uppercase;
        margin-bottom: 0.2rem;
        text-align: center;
    }
    .sidebar-brand-subtitle {
        font-size: 0.82rem;
        color: #475569;
        text-align: center;
        line-height: 1.4;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown(
        """
        <div style="display:flex; flex-direction:column; align-items:center; padding: 0.15rem 0 0.6rem;">
            <div class="sidebar-brand-card">
                <div class="sidebar-brand-title">STMKG</div>
        """,
        unsafe_allow_html=True,
    )

    logo_path = os.path.join(os.getcwd(), "Logo_STMKG.png")
    if os.path.exists(logo_path):
        st.markdown(
            f"""
            <div class="sidebar-logo-frame">
                <img src="data:image/png;base64,{__import__('base64').b64encode(open(logo_path, 'rb').read()).decode()}" alt="Logo STMKG" />
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="sidebar-logo-frame">
                <div style="width: 100%; height: 86px; display:flex; align-items:center; justify-content:center; border: 2px dashed #cbd5e1; border-radius: 12px; background: #f8fafc; color: #64748b; font-weight: 600;">
                    Logo STMKG
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
            <div class="sidebar-brand-subtitle">Sistem Terpadu Analisis Data</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

halaman_home = st.Page("Page/home.py", title="Beranda Utama", icon="🏠", default=True)
halaman_proyek_1 = st.Page("Page/proyek1.py", title="Analisis Heat Index", icon="🌡️")
halaman_proyek_2 = st.Page("Page/proyek2.py", title="Konversi & Ingesti Data", icon="🔄")
halaman_proyek_3 = st.Page("Page/proyek3.py", title="Studio Peta Otomatis", icon="🗺️")
halaman_proyek_4 = st.Page("Page/proyek4.py", title="Spasial Interpolator", icon="🛰️")

pg = st.navigation({
    "Navigasi Utama": [halaman_home],
    "Modul Analisis Taruna": [halaman_proyek_1, halaman_proyek_2, halaman_proyek_3, halaman_proyek_4],
})

pg.run()

st.markdown(
    """
    <div class="app-footer">
        <strong>Portal Analisis Data Taruna</strong> · Designed for clean operational dashboard experience · BMKG-style visual system
    </div>
    """,
    unsafe_allow_html=True,
)
