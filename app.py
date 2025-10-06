import streamlit as st
from PIL import Image

# Configuración general
st.set_page_config(page_title="Agente Comercial Babel", layout="wide")

# Logo
logo = Image.open("logo_babel.jpeg")
st.sidebar.image(logo, use_container_width=True)

# Menú lateral con las dos páginas principales
st.sidebar.title("Navegación")
st.sidebar.page_link("pages/1_Lead_y_Memoria.py", label="📋 Lead y Memoria")
st.sidebar.page_link("pages/2_Calificacion_y_Caso.py", label="💡 Calificación + Caso de Negocio")

# Página principal
st.title("💼 Agente Comercial - Babel Group")
st.markdown("""
**Versión:** 2025.10  
**Propósito:** Facilitar la creación automática de casos de negocio con inteligencia competitiva.  
**Desarrollado por:** Babel Group 2025  
""")

st.info("Usa el menú lateral para comenzar con el registro de leads y avanzar en la calificación.")
