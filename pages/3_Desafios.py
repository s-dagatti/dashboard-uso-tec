import streamlit as st

st.set_page_config(
    page_title="Desafíos JD",
    page_icon="mtg.png",
    layout="wide"
)

st.title("Desafíos John Deere FY27")
st.caption("Accesos directos a gestión de desafíos")


# =====================================================
# ACCESO DIRECTO A CRACK DEL CAMPO
# =====================================================

URL_CRACK_DEL_CAMPO = (
    "https://desafios-jd.streamlit.app/"
)

st.link_button(
    "🚜 Ir al tablero Crack del Campo | Tractores",
    URL_CRACK_DEL_CAMPO,
)
