import streamlit as st

st.title("📊 Pengembangan Pemodelan Iklim Baru")
st.markdown("Halaman ini berjalan secara independen dari file `proyek2.py`.")

st.info("💡 Proyek ini sudah terpisah secara modular. Kamu bebas melakukan import library baru (seperti scikit-learn atau statsmodels) di sini.")

# Tempatkan kode eksperimen barumu di bawah ini...
st.subheader("Eksperimen Pemodelan Komparatif")
col_mock1, col_mock2 = st.columns(2)
with col_mock1:
    st.metric("Akurasi Evaluasi Model A", "89.4%", delta="Opsi Terbaik")
with col_mock2:
    st.metric("Akurasi Evaluasi Model B", "76.2%", delta="-13.2%", delta_color="inverse")