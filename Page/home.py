import streamlit as st

def run_home():
    # Header Utama bergaya futuristik
    st.markdown(
        """
        <div style="text-align: center; padding: 40px 20px; background: radial-gradient(circle, rgba(0,240,255,0.1) 0%, rgba(11,15,25,0) 70%);">
            <h1 style="font-size: 3.5rem; color: #00F0FF; margin-bottom: 10px; text-shadow: 0 0 20px rgba(0,240,255,0.5);">
                CADET CLIMATE ANALYTICS HUB
            </h1>
            <p style="font-size: 1.2rem; color: #94A3B8; max-width: 800px; margin: 0 auto;">
                Sistem Terpadu untuk Analisis Data Atmosfer dan Respon Publik Wilayah Regional.
            </p>
        </div>
        <hr style="border: 1px solid #1E293B; margin-top: 20px; margin-bottom: 40px;">
        """,
        unsafe_allow_html=True
    )

    # Penjelasan Fitur Dashboard (Layout 2 Kolom)
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("### 🖥️ Tentang Sistem Ini")
        st.write("""
        Dashboard ini dikembangkan sebagai pusat integrasi data spasio-temporal meteorologis dengan algoritma ekstraksi data publik. 
        
        Tujuan utama dari Command Center ini adalah memfasilitasi komparasi antara parameter cuaca ekstrem (seperti indeks panas atau potensi curah hujan tinggi) dengan data validasi silang berupa respon sosiologis masyarakat secara *real-time* atau historis.
        """)

    with col2:
        st.markdown("### ⚙️ Modul Aktif")
        st.markdown("""
        <div style="background: rgba(30, 41, 59, 0.4); padding: 20px; border-radius: 10px; border-left: 3px solid #FF0055;">
            <h4 style="color: #F8FAFC; margin-bottom: 5px;">📡 Modul 1: Heat Index & Public Response</h4>
            <p style="color: #94A3B8; font-size: 0.95rem; margin-bottom: 0;">
                Menganalisis korelasi antara Indeks Panas (suhu dan kelembapan) harian dengan intensitas cuitan dan interaksi di media sosial X (Twitter). Menggunakan model korelasi Pearson dan *time-series tracking*.
            </p>
        </div>
        <div style="background: rgba(30, 41, 59, 0.4); padding: 20px; border-radius: 10px; border-left: 3px solid #FF0055;">
            <h4 style="color: #F8FAFC; margin-bottom: 5px;">⚙️ Modul 2: UNIVERSAL MET-CLIMATE DATA INGESTION</h4>
            <p style="color: #94A3B8; font-size: 0.95rem; margin-bottom: 0;">
                Memproses dan mengintegrasikan data cuaca dari berbagai sumber (satelit, stasiun meteorologi, model numerik) ke dalam format standar untuk analisis lanjutan.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.info("💡 **Petunjuk Penggunaan:** Silakan gunakan menu navigasi di sebelah kiri (Sidebar) untuk mengakses modul analitik yang tersedia.")

run_home()