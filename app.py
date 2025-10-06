# app.py — Home & Navegación para el Agente Comercial Babel

import streamlit as st
from datetime import datetime

# ---------- Configuración de página ----------
st.set_page_config(
    page_title="Agente Comercial Babel • Caso de Negocio",
    page_icon="💼",
    layout="wide",
)

# ---------- Estado inicial (ids seguros) ----------
DEFAULT_STATE = {
    "lead": {},                              # empresa, contacto, correo, tel, descripción
    "memoria_proyectos": [],                 # lista de proyectos anteriores
    "score": None,                           # 0..100
    "calificado": False,                     # True si score >= 70
    "business_case": {},                     # dict con campos del caso de negocio
    "chat_hist": [],                         # historial del chat de caso de negocio
    "comp_urls": [],                         # URLs de Babel y competidores
    "listo_pdf": False,                      # bandera para habilitar PDF
    "pdf_bytes": None,                       # bytes del PDF final (si ya se generó)
    "ultima_actualizacion": None,            # timestamp
}

for k, v in DEFAULT_STATE.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Conveniencia
def kpi_value(v, suffix=""):
    if v is None:
        return "—"
    return f"{v}{suffix}"

# ---------- Sidebar de navegación ----------
st.sidebar.title("🧭 Navegación")
st.sidebar.page_link("app.py", label="🏠 Inicio")

# ⚠️ Importante: estos nombres deben existir exactamente en tu carpeta /pages
st.sidebar.page_link("pages/1_Lead_y_Memoria.py", label="1️⃣ Lead y Memoria")
st.sidebar.page_link("pages/2_Calificacion_y_Caso.py", label="2️⃣ Calificación + Caso")

st.sidebar.markdown("---")
st.sidebar.caption("© Babel • Agente Comercial IA • v2025.10")

# ---------- Encabezado ----------
col_logo, col_title = st.columns([1, 7])
with col_title:
    st.title("Agente Comercial Babel — Caso de Negocio")
    st.caption("Flujo: 1) Lead/Memoria → 2) Calificación + Caso")

# ---------- KPIs ----------
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Score (Calificación)", kpi_value(st.session_state["score"], "%"))
with col2:
    st.metric("Proyectos en memoria", len(st.session_state["memoria_proyectos"]))
with col3:
    st.metric("Listo para PDF", "Sí" if st.session_state["listo_pdf"] else "No")

# ---------- Tarjeta de estado general ----------
st.info(
    "Usa el menú lateral para navegar.\n\n"
    "1) **Lead y Memoria**: captura datos del cliente y registra proyectos previos.\n\n"
    "2) **Calificación + Caso**: califica (umbral ≥ 70%). Si se logra el umbral, "
    "se habilita el chat guiado para construir el Caso de Negocio y la comparación competitiva. "
    "Desde ahí podrás marcar *Listo para PDF*."
)

# ---------- Última actualización & acciones ----------
c1, c2 = st.columns([1, 1])
with c1:
    if st.session_state["ultima_actualizacion"]:
        st.caption(
            f"🕒 Última actualización: {st.session_state['ultima_actualizacion']}"
        )
with c2:
    if st.button("🔄 Reiniciar sesión", use_container_width=True):
        for k in list(st.session_state.keys()):
            if k in DEFAULT_STATE:
                st.session_state[k] = DEFAULT_STATE[k]
        st.session_state["ultima_actualizacion"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        st.success("Sesión reiniciada.")

# ---------- Ayuda ----------
with st.expander("❓ ¿Qué hace cada fase?"):
    st.markdown(
        """
**1) Lead y Memoria**
- Captura: *Empresa, Contacto, Correo, Teléfono, Descripción breve*.
- Registra proyectos previos (memoria) para personalizar recomendaciones.

**2) Calificación + Caso**
- Califica con ponderaciones **20/30/30/5/5** (umbral: **≥ 70%**).
- Si alcanza el umbral: habilita **Chat guiado** para completar el Caso de Negocio.
- Integra **Inteligencia competitiva** (Babel vs. competidores) para enriquecer la solución.
- Marca **Listo para PDF** para permitir la descarga del documento final en esa misma página.
        """
    )

# ---------- Footer ----------
st.markdown("---")
st.caption("Hecho con Streamlit • Mantén los nombres de archivo de /pages EXACTOS para evitar errores de navegación.")
