import streamlit as st

st.set_page_config(page_title="Lead & Memoria", page_icon="🗂️", layout="wide")
st.title("🗂️ 1) Lead & Memoria")

lead = st.session_state.get("lead", {})

with st.form("lead_form"):
    st.subheader("Datos del lead")
    c1, c2 = st.columns(2)
    lead["empresa"] = c1.text_input("Empresa", lead.get("empresa", ""))
    lead["contacto"] = c2.text_input("Nombre completo", lead.get("contacto", ""))
    c3, c4 = st.columns(2)
    lead["email"] = c3.text_input("Correo", lead.get("email", ""))
    lead["telefono"] = c4.text_input("Teléfono", lead.get("telefono", ""))
    lead["descripcion"] = st.text_area("Descripción breve", lead.get("descripcion", ""))

    guardado = st.form_submit_button("💾 Guardar lead")
    if guardado:
        st.session_state["lead"] = lead
        st.success("Lead guardado.")

st.divider()
st.subheader("📒 Memoria de proyectos")
with st.expander("Agregar proyecto a memoria"):
    with st.form("add_proj"):
        p_nombre = st.text_input("Nombre / Cliente / Proyecto")
        p_notas = st.text_area("Notas / aprendizaje")
        add = st.form_submit_button("Agregar a memoria")
        if add and p_nombre.strip():
            st.session_state["proyectos_memoria"].append({"nombre": p_nombre.strip(), "notas": p_notas.strip()})
            st.success("Proyecto agregado.")

mem = st.session_state.get("proyectos_memoria", [])
if not mem:
    st.info("Aún no hay proyectos en memoria.")
else:
    for i, p in enumerate(mem, start=1):
        st.markdown(f"**{i}. {p['nombre']}**  \n{p['notas'] or '_Sin notas_'}")
