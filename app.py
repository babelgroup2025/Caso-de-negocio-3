# app.py — Navegación y estado global

import streamlit as st

st.set_page_config(page_title="Agente Comercial Babel", page_icon="🧭", layout="wide")

# ---------- Estado global ----------
defaults = {
    "memoria": [],            # lista de leads guardados
    "lead_activo": None,      # lead seleccionado
    "score": None,            # porcentaje de calificación (fase 2)
    "viable": False,          # si score >= 70
    "case_data": {},          # campos del caso de negocio (fase 3)
    "propuesta_ia": "",       # texto generado por IA
    "listo_pdf": False,       # bandera “listo para PDF” si la necesitas luego
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------- Cabecera ----------
st.title("Agente Comercial Babel – Caso de Negocio")
st.caption("Flujo: 1) Lead & Memoria → 2) Calificación → 3) Caso de negocio + Solución + PDF")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Score (Fase 2)", f"{st.session_state['score'] or 0}%")
with col2:
    st.metric("Leads en memoria", f"{len(st.session_state['memoria'])}")
with col3:
    st.metric("Listo para PDF", "Sí" if st.session_state.get("viable") else "No")

st.info("Usa el **menú lateral** para navegar por las 3 páginas.")

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Navegación")
    # Estos enlaces aparecen automáticamente si existen los archivos en /pages
    st.page_link("app.py", label="🏠 Inicio")
    st.page_link("pages/1_Lead_y_Memoria.py", label="1) Lead & Memoria")
    st.page_link("pages/2_Calificacion.py", label="2) Calificación")
    st.page_link("pages/3_Caso_y_Solucion.py", label="3) Caso + Solución + PDF")

    st.divider()
    if st.button("🔁 Reiniciar sesión"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# Contenido simple en home
with st.expander("¿Qué hace cada fase?"):
    st.markdown("""
**1) Lead & Memoria:** Captura/selecciona el lead (empresa, contacto, correo, teléfono, descripción) y guarda historial.  
**2) Calificación:** 5 preguntas ponderadas **20/30/30/5/5**. Si el **score ≥ 70%**, la oportunidad es **viable**.  
**3) Caso + Solución + PDF:** Completa/auto-genera el caso de negocio, compara con competidores y **descarga el PDF**.
""")
