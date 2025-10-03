import streamlit as st
from urllib.parse import urlparse

st.header("🧪 Fase 2 · Calificación + Caso (Chat) + Competitividad")

# ------ Validación de lead activo ------
if "active_lead_idx" not in st.session_state or st.session_state.get("active_lead_idx") is None:
    st.warning("Primero selecciona un **Lead activo** en la Fase 1.")
    st.stop()

lead = st.session_state["leads"][st.session_state["active_lead_idx"]]
st.caption(f"Lead activo: **{lead['empresa']}** · {lead['nombre']}")

# ------ A) CALIFICACIÓN ------
st.subheader("A) Calificación del Lead — Ponderación 20/30/30/10/10")

q1 = st.radio("¿Tiene fecha planeada para iniciar proyecto?", ["Sí", "No"], index=None, horizontal=True)
q2 = st.radio("¿Cuenta con presupuesto?", ["Sí", "No"], index=None, horizontal=True)
q3 = st.radio("¿Es un proyecto para incrementar ventas o marketing?", ["Sí", "No"], index=None, horizontal=True)
q4 = st.radio("¿El proyecto resuelve un problema de prioridad 1, 2 o 3?", ["Sí", "No"], index=None, horizontal=True)
q5 = st.radio("¿Hablamos con tomador de decisión?", ["Sí", "No"], index=None, horizontal=True)

score = 0
if q1 == "Sí": score += 20
if q2 == "Sí": score += 30
if q3 == "Sí": score += 30
if q4 == "Sí": score += 10
if q5 == "Sí": score += 10

st.session_state["score"] = score
st.progress(score/100.0)
st.metric("Puntaje", f"{score} / 100")

st.session_state["ready_for_case"] = score >= 70

# ------ B) CASO DE NEGOCIO · Chat Guiado ------
st.subheader("B) Caso de Negocio (Chat guiado)")

# Campos estructurados que el chat debe llenar
DEFAULT_FIELDS = {
    "objetivos": "",
    "problema": "",
    "solucion_esperada": "",
    "target": "",
    "funcionalidades": "",
    "expectativas": "",
    "experiencia_previa": "",
    "forma_adjudicacion": "",
    "criterios_evaluacion": "",
    "fecha_lanzamiento": "",
    "rango_presupuesto": "",
    "nombre_proyecto": "",
    "notas": "",
}

# Init memoria de chat y campos
if "bn_fields" not in st.session_state:
    st.session_state["bn_fields"] = DEFAULT_FIELDS.copy()
if "chat_log" not in st.session_state:
    st.session_state["chat_log"] = []

# Ayuda para el usuario
with st.expander("Ver campos del Caso de Negocio / editar manualmente (opcional)"):
    for k, label in [
        ("objetivos", "Objetivos de negocio"),
        ("problema", "Problema a resolver"),
        ("solucion_esperada", "Solución esperada"),
        ("target", "Usuarios/target"),
        ("funcionalidades", "Funcionalidades"),
        ("expectativas", "Expectativas"),
        ("experiencia_previa", "Experiencia previa similar"),
        ("forma_adjudicacion", "Forma de adjudicación"),
        ("criterios_evaluacion", "Criterios de evaluación"),
        ("fecha_lanzamiento", "Fecha de lanzamiento"),
        ("rango_presupuesto", "Rango de presupuesto"),
        ("nombre_proyecto", "Nombre del proyecto"),
        ("notas", "Notas generales"),
    ]:
        st.session_state["bn_fields"][k] = st.text_area(label, st.session_state["bn_fields"][k], key=f"edit_{k}")

# Chat sólo si score >= 70
if st.session_state["ready_for_case"]:
    st.info("💬 Chatea con el agente. Irá pidiendo lo que falte para completar el caso.")
    user_msg = st.chat_input("Escribe tu mensaje…")
    if user_msg:
        st.session_state["chat_log"].append(("usuario", user_msg))

        # --- Lógica simple de “asistente” (sin dependencias externas). 
        #     Puedes conectar OpenAI aquí si quieres: genera una respuesta y actualiza bn_fields.
        response = "Gracias. ¿Puedes detallar los **objetivos de negocio** y el **problema a resolver**?"
        # Ejemplo: si el usuario menciona 'objetivo' o 'problema', auto-llenar algo:
        low = user_msg.lower()
        if "objetiv" in low:
            st.session_state["bn_fields"]["objetivos"] = user_msg
            response = "Anotado el objetivo. ¿Cuál sería la **solución esperada** y el **target** principal?"
        elif "problema" in low:
            st.session_state["bn_fields"]["problema"] = user_msg
            response = "Registré el problema. ¿Qué **funcionalidades** mínimas necesitas?"
        elif "solución" in low or "solucion" in low:
            st.session_state["bn_fields"]["solucion_esperada"] = user_msg
            response = "Ok. ¿Quién usará esto (target) y qué **expectativas** de resultados tienen?"
        elif "presupuesto" in low:
            st.session_state["bn_fields"]["rango_presupuesto"] = user_msg
            response = "Gracias. ¿Cuál es la **fecha de lanzamiento** tentativamente?"
        # añade más reglas si quieres…

        st.session_state["chat_log"].append(("agente", response))

    # Render chat
    for role, txt in st.session_state["chat_log"]:
        if role == "usuario":
            st.chat_message("user").markdown(txt)
        else:
            st.chat_message("assistant").markdown(txt)
else:
    st.warning("⚠️ Aún no alcanzas 70 puntos. Completa la calificación para desbloquear el chat.")

# ------ C) INTELIGENCIA COMPETITIVA ------
st.subheader("C) Inteligencia Competitiva")

st.caption("Pega URLs de Babel y competidores (una por línea). Este módulo está listo para conectarse a un RAG.")
urls_raw = st.text_area("URLs:", value="https://babelgroup.com\nhttps://www.accenture.com\nhttps://www.ibm.com/consulting")
urls = [u.strip() for u in urls_raw.splitlines() if u.strip()]

def domain(u: str) -> str:
    try:
        return urlparse(u).netloc.replace("www.", "")
    except:
        return u

cols = st.columns(3)
with cols[0]:
    st.markdown("**Sitios**")
    st.write("\n".join([f"• {domain(u)}" for u in urls]) or "—")
with cols[1]:
    st.markdown("**Soluciones (resumen simulado)**")
    st.write("• Babel: modernización, data/AI, automatización\n• Accenture: transformación digital end-to-end\n• IBM Consulting: IA generativa, integración empresarial")
with cols[2]:
    st.markdown("**Oportunidades para diferenciar**")
    st.write("• Propuesta enfocada en time-to-value\n• Caso de negocio cuantificado\n• Entregables rápidos (MVP) con IA aplicada")

st.info("Para activar RAG real: conéctalo a un índice (web/PDF) y reemplaza la sección superior por consultas al índice.")
