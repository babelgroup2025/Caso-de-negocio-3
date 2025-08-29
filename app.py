# app.py — Portada del Agente Comercial (Streamlit multipágina)
import os
import streamlit as st

# Configuración básica
st.set_page_config(
    page_title="Caso de Negocio - Agente Babel",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estado compartido para las páginas
st.session_state.setdefault("score_total", 0)          # de pages/1_Evaluacion.py
st.session_state.setdefault("proyectos", [])           # de pages/2_Memoria.py
st.session_state.setdefault("diseno", {})              # de pages/3_Diseno.py
st.session_state.setdefault("devtest", {})             # de pages/4_Desarrollo_y_Pruebas.py
st.session_state.setdefault("ready_for_pdf", False)    # se marca en Fase 4
st.session_state.setdefault("propuesta_md", None)      # propuesta IA opcional

# Encabezado
col_logo, col_title = st.columns([1, 5])
with col_logo:
    if os.path.exists("logo_babel.jpeg"):
        st.image("logo_babel.jpeg", use_container_width=True)
with col_title:
    st.title("Agente Comercial Babel – Caso de Negocio")
    st.caption("Flujo: 1) Evaluación → 2) Memoria → 3) Diseño → 4) Desarrollo/Pruebas → (5) PDF")

st.divider()

# Resumen rápido
c1, c2, c3 = st.columns(3)
c1.metric("Score (Evaluación)", f"{st.session_state['score_total']}%")
c2.metric("Proyectos en memoria", len(st.session_state["proyectos"]))
c3.metric("Listo para PDF", "Sí" if st.session_state["ready_for_pdf"] else "No")

st.info(
    "Usa el **menú lateral** (barra izquierda). Streamlit ya muestra "
    "automáticamente las páginas que tengas en la carpeta **pages/**:\n\n"
    "- 1_Evaluacion\n- 2_Memoria\n- 3_Diseno\n- 4_Desarrollo_y_Pruebas\n- (opcional) 5_PDF"
)

with st.expander("📋 ¿Qué hace cada fase?"):
    st.markdown("""
**Evaluación**: 5 preguntas ponderadas (20/30/30/5/5).  
**Memoria**: registrar y consultar proyectos previos.  
**Diseño**: objetivos, alcance, integraciones, arquitectura, KPIs, riesgos, roadmap.  
**Desarrollo y Pruebas**: checklist técnico; marcar **Listo para PDF**.  
**PDF**: genera el documento final (requiere `DejaVuSans.ttf` en la raíz).
""")

# Utilidad: reiniciar sesión
if st.button("♻️ Reiniciar sesión"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.success("Sesión reiniciada. Ve a **1_Evaluacion** desde el menú lateral.")
    st.rerun()

st.caption("© Babel — Demo de Caso de Negocio con Streamlit")
