import streamlit as st

st.title("🛠️ Fase 4: Desarrollo y Pruebas")

# ⚠️ Candado por score (si lo guardaste en la Fase 1)
score = st.session_state.get("score_total", None)
if score is not None and score < 70:
    st.warning("⚠️ La oportunidad no alcanzó 70% en Evaluación. Revisa la Fase 1 antes de continuar.")
    # Si quieres bloquear edición, descomenta la siguiente línea:
    # st.stop()

st.write("""
Completa esta fase para dejar traza del plan de construcción y la validación.
Al guardar, quedará disponible una marca para preparar el PDF final.
""")

with st.form("form_dev_test"):
    st.subheader("📋 Plan de desarrollo")
    plan_desarrollo = st.text_area(
        "Descripción general (iteraciones, ramas, criterios de done)",
        height=120,
        placeholder="Sprint 1: núcleo de evaluación y memoria; Sprint 2: RAG + propuesta; Sprint 3: pulido y despliegue…"
    )

    st.subheader("🧱 Entorno y dependencias")
    entorno = st.text_area(
        "Entorno/stack",
        height=100,
        placeholder="Python 3.11+, Streamlit Cloud/Render, OpenAI API, fpdf2, bs4, numpy, pypdf…"
    )
    dependencias_ok = st.checkbox("Requirements instalados y verificados")

    st.subheader("✅ Checklist de tareas")
    t_eval     = st.checkbox("Evaluación (score 5 preguntas) funcionando")
    t_memoria  = st.checkbox("Memoria de proyectos (session_state/DB) funcionando")
    t_rag      = st.checkbox("Indexación RAG (web/PDF) funcionando")
    t_chat     = st.checkbox("Chat con contexto (RAG) funcionando")
    t_pdf      = st.checkbox("Generación de PDF con acentos (DejaVuSans.ttf)")

    st.subheader("🧪 Plan de pruebas")
    pruebas_unit = st.text_area("Pruebas unitarias (qué y cómo)", height=100,
        placeholder="Normalización de texto, cálculo de score, paginado PDF, extracción de contexto…")
    pruebas_int  = st.text_area("Pruebas de integración (qué y cómo)", height=100,
        placeholder="Flujo completo: Evaluación ≥70% → Propuesta → PDF. Manejo de errores y timeouts.")
    criterios_ok = st.checkbox("Criterios de aceptación cumplidos")

    st.subheader("📈 Resultados de pruebas")
    resultado = st.selectbox("Estatus", ["Pendiente","En progreso","Aprobado","Con observaciones"])
    riesgos   = st.text_area("Riesgos técnicos y mitigaciones", height=90,
        placeholder="Límites de la API, costos, fuentes con ruido, encoding de PDF, escalabilidad…")
    despliegue = st.text_area("Plan de despliegue / rollback", height=90,
        placeholder="Streamlit Cloud/Render, variables de entorno (OPENAI_API_KEY), rollback por commit/tag…")

    submitted = st.form_submit_button("💾 Guardar Fase 4")

if submitted:
    st.session_state["devtest"] = {
        "plan_desarrollo": plan_desarrollo,
        "entorno": entorno,
        "dependencias_ok": dependencias_ok,
        "tareas": {
            "evaluacion": t_eval, "memoria": t_memoria, "rag": t_rag,
            "chat": t_chat, "pdf": t_pdf
        },
        "pruebas": {
            "unitarias": pruebas_unit,
            "integracion": pruebas_int,
            "criterios_ok": criterios_ok,
            "resultado": resultado
        },
        "riesgos": riesgos,
        "despliegue": despliegue
    }

    # Marca para habilitar PDF si todo está OK
    listo_para_pdf = all([
        dependencias_ok, t_eval, t_memoria, t_rag, t_chat, t_pdf,
        criterios_ok, (resultado in ["Aprobado"])
    ])
    st.session_state["ready_for_pdf"] = bool(listo_para_pdf)
    if listo_para_pdf:
        st.success("✅ Fase 4 completa. Listo para generar el PDF final en la página de PDF.")
    else:
        st.info("Información guardada. Aún faltan criterios para marcar 'Listo para PDF'.")

st.divider()
st.subheader("🔎 Resumen guardado")
devtest = st.session_state.get("devtest")
if devtest:
    st.write("**Plan de desarrollo:**"); st.write(devtest["plan_desarrollo"] or "—")
    st.write("**Entorno:**"); st.write(devtest["entorno"] or "—")
    st.write("**Dependencias OK:**", "Sí" if devtest["dependencias_ok"] else "No")
    st.write("**Tareas:**", devtest["tareas"])
    st.write("**Pruebas:**", devtest["pruebas"])
    st.write("**Riesgos:**"); st.write(devtest["riesgos"] or "—")
    st.write("**Despliegue:**"); st.write(devtest["despliegue"] or "—")
    st.write("---")
    st.metric("Listo para PDF", "Sí" if st.session_state.get("ready_for_pdf") else "No")
else:
    st.info("Aún no has guardado información de esta fase.")
