# app.py — Portada del Agente Comercial (multi-páginas)

import os
import streamlit as st

# ------------------ Configuración de página ------------------
st.set_page_config(
    page_title="Caso de Negocio - Agente Babel",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------ Encabezado / Branding ------------------
col_logo, col_title = st.columns([1, 5])
with col_logo:
    if os.path.exists("logo_babel.jpeg"):
        st.image("logo_babel.jpeg", use_container_width=True)
with col_title:
    st.title("Agente Comercial Babel – Caso de Negocio")
    st.caption("Evaluación → Memoria → Diseño → Desarrollo/Pruebas → PDF final")

st.divider()

# ------------------ Estado global (session_state) ------------------
# Llaves que usaremos en otras páginas
st.session_state.setdefault("score_total", 0)            # de 1_Evaluacion.py
st.session_state.setdefault("proyectos", [])             # de 2_Memoria.py
st.session_state.setdefault("diseno", {})                # de 3_Diseno.py
st.session_state.setdefault("devtest", {})               # de 4_Desarrollo_y_Pruebas.py
st.session_state.setdefault("ready_for_pdf", False)      # marcado en Fase 4
st.session_state.setdefault("propuesta_md", None)        # si generas propuesta IA

# API Key (opcional): solo mostramos si está cargada
api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
api_status = "✅ Cargada" if api_key else "—"

# ------------------ Resumen rápido en la portada ------------------
st.subheader("Resumen del estado")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Score (Evaluación)", f"{st.session_state['score_total']}%")
with col2:
    st.metric("Proyectos en memoria", len(st.session_state["proyectos"]))
with col3:
    ready = "Sí" if st.session_state["ready_for_pdf"] else "No"
    st.metric("Listo para PDF", ready)
with col4:
    st.metric("OpenAI API Key", api_status)

st.info(
    "Navega por las páginas desde el **menú lateral** (izquierda). "
    "El orden recomendado es: **1) Evaluación**, **2) Memoria**, **3) Diseño**, "
    "**4) Desarrollo y Pruebas**, y finalmente **5) PDF**."
)

# ------------------ Guía del flujo ------------------
with st.expander("📋 Qué hace cada fase"):
    st.markdown("""
**1) Evaluación**  
Califica la oportunidad con 5 preguntas (20/30/30/5/5). Si el puntaje ≥ **70%**, puedes avanzar.

**2) Memoria de Proyectos**  
Registra antecedentes para que el agente recuerde proyectos y resultados.

**3) Diseño de la Solución**  
Define objetivos, alcance, integraciones, arquitectura, KPIs, riesgos y roadmap.

**4) Desarrollo y Pruebas**  
Checklist técnico, entorno, pruebas y estado. Marca **Listo para PDF** cuando todo esté OK.

**5) PDF Final**  
Genera el documento con toda la información (usa la fuente *DejaVuSans.ttf* para acentos).
""")

# ------------------ Panel de inspección rápida ------------------
with st.expander("🔎 Ver datos guardados (debug útil)"):
    st.write("**Proyectos**:", st.session_state["proyectos"])
    st.write("**Diseño**:", st.session_state["diseno"])
    st.write("**Dev/Pruebas**:", st.session_state["devtest"])
    st.write("**Propuesta IA (markdown)**:", st.session_state["propuesta_md"])

# ------------------ Utilidades ------------------
col_reset, col_spacer, col_help = st.columns([1, 6, 1])
with col_reset:
    if st.button("♻️ Reiniciar sesión"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.success("Sesión reiniciada. Ve a la página de Evaluación para comenzar.")
        st.stop()

with col_help:
    st.page_link("pages/1_Evaluacion.py", label="Ir a Evaluación ➜", icon="➡️")

st.divider()
st.caption("© Babel — Demo de Caso de Negocio con Streamlit")
