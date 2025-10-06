import streamlit as st

st.set_page_config(
    page_title="Agente Comercial - Babel",
    layout="wide",
    page_icon="💼"
)

st.sidebar.image("logo_babel.jpeg", use_column_width=True)
st.sidebar.title("Navegación")

st.sidebar.page_link("pages/1_Lead_y_Memoria.py", label="1️⃣ Lead y Memoria")
st.sidebar.page_link("pages/2_Calificacion_y_Caso.py", label="2️⃣ Calificación + Caso de Negocio")
