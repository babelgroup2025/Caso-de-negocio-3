# app.py — Portada del Agente Comercial (Streamlit multipágina)
import os
import streamlit as st

# ---- Configuración de página ----
st.set_page_config(
    page_title="Caso de Negocio - Agente Babel",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- Estado inicial (para que las demás páginas lo usen) ----
st.session_state.setdefault("score_total", 0)          # de 1_Evaluacion.py
st.session_state.setdefault("proyectos", [])           # de 2_Memoria.py
st.session_state.setdefault("diseno", {})              # de 3_Diseno.py
st.session_state.setdefault("devtest", {})             # de 4_Desarrollo_y_Pruebas.py
st.session_state.setdefault("ready_for_pdf", False)    # marcado en Fase 4
st.session_state.setdefault("propuesta_md", None)      # si generas propuesta IA

# ---- Encabezado / Branding ----
col_logo, col_title = st.columns([1, 5])
with col_logo:
    if os.path.exists("logo_babel.jpeg"):
        st.image("logo_babel.jpeg", use_container_width=True)
with col_title:
    st.title("Agente Comercial Babel – Caso de Negocio")
    st.caption("Flujo: 1) Evaluación → 2) Memoria → 3) Diseño → 4) Desarrollo/Pruebas → 5) PDF")

st.divider()

# ---- Resumen rápido ----
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Score (Evaluación)", f"{st.session_state['score_total']}%")
with col2:
    st.metric("Proyectos en memoria", len(st.session_state["proyectos"]))
with col3:
    st.metric("Listo para PDF", "Sí" if st.session_state["ready_for_pdf"] else "No")

st.info(
    "Usa el **menú lateral** para navegar por las páginas: "
    "**1_Evaluacion**, **2_Memoria**, **3_Diseno**, **4_Desarrollo_y_Pruebas** y **5_PDF**."
)

# ---- Ayuda / Guía ----
with st.expander("📋 ¿Qué hace cada fase?"):
    st.markdown("""
**1) Evaluación** – Calcula el puntaje (≥ 70% para avanzar).  
**2) Memoria** – Registra/consulta proyectos previos.  
**3) Diseño** – Objetivos, alcance, integraciones, arquitectura, KPIs, riesgos, roadmap.  
**4) Desarrollo y Pruebas** – Checklist técnico y estado; marca **Listo para PDF**.  
**5) PDF** – Genera el documento final con acentos (requiere `DejaVuSans.ttf` en la raíz).
""")

# ---- Utilidad: reiniciar sesión ----
if st.button("♻️ Reiniciar sesión"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.success("Sesión reiniciada. Ve a la página **1_Evaluacion** en el menú lateral.")
    st.stop()

st.caption("© Babel — Demo de Caso de Negocio con Streamlit")
