import streamlit as st

st.title("📚 Memoria de Proyectos")

st.write("Aquí puedes registrar o consultar proyectos previos para que el agente los recuerde.")

# Inicializamos la memoria si no existe
if "proyectos" not in st.session_state:
    st.session_state["proyectos"] = []

# Formulario para registrar proyectos
with st.form("nuevo_proyecto"):
    nombre = st.text_input("📌 Nombre del proyecto")
    descripcion = st.text_area("📝 Descripción del proyecto")
    resultado = st.text_area("✅ Resultado / estado actual")

    submitted = st.form_submit_button("Guardar en Memoria")

    if submitted:
        if nombre and descripcion:
            st.session_state["proyectos"].append({
                "nombre": nombre,
                "descripcion": descripcion,
                "resultado": resultado
            })
            st.success(f"Proyecto **{nombre}** guardado en la memoria.")
        else:
            st.error("⚠️ Debes llenar al menos el nombre y la descripción.")

# Mostrar proyectos previos guardados
st.write("### 📂 Proyectos en memoria:")

if st.session_state["proyectos"]:
    for i, p in enumerate(st.session_state["proyectos"], 1):
        st.markdown(f"**{i}. {p['nombre']}**")
        st.write(f"- Descripción: {p['descripcion']}")
        st.write(f"- Resultado: {p['resultado']}")
        st.write("---")
else:
    st.info("Aún no hay proyectos guardados en memoria.")
