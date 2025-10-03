import streamlit as st

st.set_page_config(page_title="Agente Comercial Babel", page_icon="🤖", layout="wide")

# ---- Estado inicial ----
defaults = {
    "lead": {"empresa": "", "contacto": "", "email": "", "telefono": "", "descripcion": ""},
    "proyectos_memoria": [],
    "score": 0,            # 0-100
    "listo_pdf": False,    # bandera desde página 2
    "propuesta_ia": ""
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---- Sidebar (navegación) ----
with st.sidebar:
    st.header("Navegación")
    st.page_link("app.py", label="🏠 Inicio")
    st.page_link("pages/1_Lead_y_Memoria.py", label="1) Lead & Memoria")
    st.page_link("pages/2_Calificacion_y_Caso.py", label="2) Calificación + Caso & PDF")
    st.divider()
    if st.button("🔄 Reiniciar sesión"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.experimental_rerun()

st.title("Agente Comercial Babel – Caso de Negocio")

c1, c2, c3 = st.columns(3)
c1.metric("Score (Pág. 2)", f"{int(st.session_state['score'])}%")
c2.metric("Proyectos en memoria", len(st.session_state["proyectos_memoria"]))
c3.metric("Listo para PDF", "Sí" if st.session_state["listo_pdf"] else "No")

st.info(
    "Flujo: **1) Lead & Memoria → 2) Calificación** (si ≥ 70%) **→ Caso de negocio + Descarga de PDF**.\n"
    "Usa el menú lateral para navegar."
)
