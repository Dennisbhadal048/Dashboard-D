import streamlit as st


def run_home():
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #00509E 0%, #003366 100%); padding: 30px 34px; border-radius: 18px; color: white; box-shadow: 0 12px 28px rgba(0, 48, 102, 0.2); margin-bottom: 20px; position: relative; overflow: hidden;">
            <div style="position:absolute; inset:0; background: radial-gradient(circle at top right, rgba(255,255,255,0.22), transparent 36%); pointer-events:none;"></div>
            <div style="position:relative; z-index:1;">
                <div style="display:inline-block; padding: 6px 10px; border-radius: 999px; background: rgba(255,255,255,0.16); font-size: 0.77rem; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase; margin-bottom: 10px;">Dashboard Operasional</div>
                <h1 style="color: #ffffff !important; margin: 0 0 8px 0; font-size: 2.2rem; line-height: 1.2;">PORTAL ANALISIS DATA TARUNA</h1>
                <p style="margin: 0; font-size: 1.02rem; opacity: 0.96; max-width: 880px;">Sistem terpadu untuk pemrosesan, visualisasi, dan analisis meteorologi serta klimatologi secara cepat, rapi, dan siap dipakai untuk kebutuhan operasional.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([1.1, 0.9], gap="large")

    with col1:
        st.markdown("### 🎯 Tujuan Sistem")
        st.markdown(
            """
            <div style="background: #f0f7ff; border: 1px solid #dbeafe; border-left: 4px solid #0284c7; padding: 16px; border-radius: 10px; color: #0f3b63; line-height: 1.6;">
            <strong>Platform</strong> ini dirancang untuk membantu Taruna melakukan ekstraksi, pemrosesan, dan visualisasi data spasial maupun <em>time-series</em> dengan alur kerja yang sederhana namun tetap menghasilkan output visual yang siap dipakai untuk kebutuhan operasional dan publikasi.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown("### ⚙️ Modul Tersedia")
        st.markdown(
            """
            <div style="background: #fff7ed; border: 1px solid #ffedd5; border-left: 4px solid #f59e0b; padding: 12px 14px; border-radius: 10px; margin-bottom: 10px; color: #7c2d12;">
            <strong>🌡️ Modul 1:</strong> Analisis Heat Index dan respons publik berbasis data sosial.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div style="background: #fef2f2; border: 1px solid #fecaca; border-left: 4px solid #ef4444; padding: 12px 14px; border-radius: 10px; margin-bottom: 10px; color: #7f1d1d;">
            <strong>🔄 Modul 2:</strong> Konversi data universal, termasuk ekstraksi metadata GeoTIFF.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div style="background: #ecfdf5; border: 1px solid #d1fae5; border-left: 4px solid #10b981; padding: 12px 14px; border-radius: 10px; color: #065f46;">
            <strong>🗺️ Modul 3:</strong> Studio peta otomatis berbasis Cartopy untuk visualisasi spasial cepat.
            </div>
            """,
            unsafe_allow_html=True,
        )


run_home()