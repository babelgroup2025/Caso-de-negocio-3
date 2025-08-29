# app.py — Portada + Menú lateral amigable
import os
import streamlit as st

st.set_page_config(
    page_title="Caso de Negocio - Agente Babel",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----- MENÚ LATERAL (siempre visible) -----
st.sidebar.title("📌 Navegación")
st.sidebar.page_link("app.py", label="🏠 Inicio")
st.sidebar.page_link("pages/1_Evaluacion.py", label="📊 Evaluación")
st.sidebar.page_link("pages/2_Memoria.py", label="🗂 Memoria de Proyectos")
st.sidebar.page_link("pages/3_Diseno.py", label="🧩 Diseño de la Solución")
st.sidebar.page_link("pages/4_Desarrollo_y_Pruebas.py", label="🛠️ Desarrollo y Pruebas")
# Si ya creaste la página de PDF:
# st.sidebar.page_link("pages/5_PDF.py", label="📄 PDF Final")

st.sidebar.markdown("---")
if st.sidebar.button("♻️ Reiniciar sesión"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.sidebar.success("Sesión reiniciada. Ve a Evaluación.")
    st.experimental_rerun()

# ----- Estado base para que las otras páginas lo lean -----
st.session_state.setdefault("score_total", 0)
st.session_state.setdefault("proyectos", [])
st.session_state.setdefault("diseno", {})
st.session_state.setdefault("devtest", {})
st.session_state.setdefault("ready_for_pdf", False)
st.session_state.setdefault("propuesta_md", None)

# ----- Encabezado -----
col_logo, col_title = st.columns([1, 5])
with col_logo:
    if os.path.exists("logo_babel.jpeg"):
        st.image("logo_babel.jpeg", use_container_width=True)
with col_title:
    st.title("Agente Comercial Babel – Caso de Negocio")
    st.caption("Flujo: 1) Evaluación → 2) Memoria → 3) Diseño → 4) Desarrollo/Pruebas → (5) PDF")

st.divider()

# ----- Resumen rápido -----
col1, col2, col3 = st.columns(3)
col1.metric("Score (Evaluación)", f"{st.session_state['score_total']}%")
col2.metric("Proyectos en memoria", len(st.session_state["proyectos"]))
col3.metric("Listo para PDF", "Sí" if st.session_state["ready_for_pdf"] else "No")

st.info(
    "Usa el **menú lateral** para navegar entre las fases. "
    "Recuerda: para avanzar, la Evaluación debe ser **≥ 70%**."
)

with st.expander("📋 ¿Qué hace cada fase?"):
    st.markdown("""
- **Evaluación**: 5 preguntas ponderadas (20/30/30/5/5).  
- **Memoria**: guarda/consulta proyectos previos.  
- **Diseño**: objetivos, alcance, integraciones, arquitectura, KPIs, riesgos, roadmap.  
- **Desarrollo y Pruebas**: checklist técnico; marca **Listo para PDF**.  
- **PDF** (opcional): genera el documento final con todo lo capturado.
""")

st.caption("© Babel — Demo de Caso de Negocio con Streamlit")
