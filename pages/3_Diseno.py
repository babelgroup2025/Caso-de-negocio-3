import streamlit as st

st.title("🧩 Fase 3: Diseño de la Solución")

st.write("""
En esta fase definimos **qué** se va a construir y **cómo** se va a integrar.
Completa las secciones para dejar trazabilidad del diseño.
""")

# --- Reglas: si vienes usando la Fase 1 (Evaluación), puedes forzar el candado aquí ---
score = st.session_state.get("score_total", None)  # si guardaste el score en 1_Evaluacion.py
if score is not None and score < 70:
    st.warning("⚠️ La oportunidad no alcanzó 70% en Evaluación. Revisa la Fase 1 antes de continuar.")
# (No bloqueamos edición para que puedas documentar; si quieres bloquear, deshabilita los inputs con disabled=True)

# --- Plantilla de diseño ---
with st.form("form_diseno"):
    objetivos = st.text_area("🎯 Objetivos específicos de la solución", height=120,
        placeholder="Ej.: Reducir el tiempo de captura de requerimientos un 40%; estandarizar propuestas; etc.")
    usuarios = st.text_area("👥 Usuarios/roles y casos de uso", height=120,
        placeholder="Ej.: Comercial, Preventa, Gerente; casos de uso principales…")
    alcance = st.text_area("📦 Alcance funcional (MVP / Fase 1)", height=140,
        placeholder="- Captura guiada de requerimientos\n- Calificación automática (BANT/Custom)\n- Generación de caso de negocio\n- RAG con web y PDFs…")
    integraciones = st.text_area("🔌 Integraciones (CRM, correos, repositorios, APIs)", height=120,
        placeholder="Salesforce/HubSpot, correo, SharePoint/Drive, etc.")
    restricciones = st.text_area("🧱 Restricciones y supuestos", height=110,
        placeholder="Seguridad, cumplimiento, datos, tiempos, presupuesto, stack disponible…")
    arquitectura = st.text_area("🏗️ Arquitectura/Componentes (alto nivel)", height=150,
        placeholder="- Frontend: Streamlit\n- Orquestación: Python\n- LLM: OpenAI (gpt-4o)\n- Embeddings: text-embedding-3-small\n- Vectorizado: (opcional) FAISS/pgvector\n- Almacenamiento: (opcional) SQLite/PostgreSQL\n- Ingesta: Web/PDF\n- PDF: fpdf2\n- Despliegue: Streamlit Cloud/Render")
    kpis = st.text_area("📈 KPIs de éxito", height=100,
        placeholder="Tiempo de levantamiento, tasa de conversión, precisión del resumen, uso por el equipo, etc.")
    riesgos = st.text_area("⚠️ Riesgos y mitigaciones", height=120,
        placeholder="- Riesgo: calidad de fuentes → Mitigación: curado y evaluación\n- Riesgo: costos de LLM → Mitigación: cache y prompts optimizados")
    roadmap = st.text_area("🗺️ Roadmap / Entregables por hitos", height=140,
        placeholder="Hito 1: MVP con evaluación y PDF\nHito 2: Indexación RAG + propuesta\nHito 3: Memoria persistente y multi-agente\n…")

    submitted = st.form_submit_button("Guardar Diseño")

if submitted:
    st.session_state["diseno"] = {
        "objetivos": objetivos,
        "usuarios": usuarios,
        "alcance": alcance,
        "integraciones": integraciones,
        "restricciones": restricciones,
        "arquitectura": arquitectura,
        "kpis": kpis,
        "riesgos": riesgos,
        "roadmap": roadmap,
    }
    st.success("✅ Diseño guardado en memoria de la sesión.")

st.divider()
st.subheader("🔎 Vista previa del diseño guardado")
diseno = st.session_state.get("diseno")
if diseno:
    for k, v in diseno.items():
        st.markdown(f"**{k.capitalize()}**")
        st.write(v or "—")
        st.write("---")
else:
    st.info("Aún no has guardado información de diseño.")
