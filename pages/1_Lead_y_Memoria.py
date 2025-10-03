import streamlit as st

st.header("📌 Fase 1 · Lead & Memoria")

# Estado inicial
if "leads" not in st.session_state: st.session_state["leads"] = []
if "active_lead_idx" not in st.session_state: st.session_state["active_lead_idx"] = None

st.markdown("Completa los datos del lead y guárdalos. Podrás seleccionarlo como activo para calificarlo en la Fase 2.")

with st.form("lead_form", clear_on_submit=False):
    col1, col2 = st.columns(2)
    with col1:
        empresa = st.text_input("Empresa")
        nombre  = st.text_input("Nombre completo")
        correo  = st.text_input("Correo")
    with col2:
        telefono = st.text_input("Teléfono")
        desc     = st.text_area("Descripción breve", height=110)

    submitted = st.form_submit_button("Guardar / Actualizar lead")
    if submitted:
        lead = {"empresa": empresa, "nombre": nombre, "correo": correo,
                "telefono": telefono, "descripcion": desc}
        st.session_state["leads"].append(lead)
        st.success("✅ Lead guardado en memoria.")

# Listado de leads
st.markdown("### Leads guardados")
if not st.session_state["leads"]:
    st.info("Aún no hay leads guardados.")
else:
    opts = [f'[{i+1}] {l["empresa"]} · {l["nombre"]}' for i,l in enumerate(st.session_state["leads"])]
    choice = st.selectbox("Selecciona lead activo", options=list(range(len(opts))), format_func=lambda x: opts[x])
    st.session_state["active_lead_idx"] = int(choice)
    lead = st.session_state["leads"][choice]
    st.markdown(f"""
**Empresa:** {lead['empresa']}  
**Contacto:** {lead['nombre']} · {lead['correo']} · {lead['telefono']}  
**Descripción:** {lead['descripcion']}
""")
    st.success("Este lead quedará **activo** para la Fase 2.")
