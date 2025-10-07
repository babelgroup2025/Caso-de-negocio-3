# pages/2_Calificacion.py
import re
from datetime import datetime
import streamlit as st

st.set_page_config(page_title="Calificación + Caso", page_icon="✅", layout="wide")

# ------------------ Estado global base ------------------
if "lead" not in st.session_state:
    st.session_state.lead = {
        "empresa": "", "contacto": "", "correo": "", "telefono": "", "descripcion": ""
    }

if "score" not in st.session_state:
    st.session_state.score = 0
if "calif_listo" not in st.session_state:
    st.session_state.calif_listo = False

# Caso de negocio (memoria del chat)
REQUIRED_FIELDS = [
    ("objetivos", "¿Cuáles son los objetivos de negocio?"),
    ("problema", "¿Cuál es el problema a resolver?"),
    ("solucion", "¿Cuál es la solución esperada?"),
    ("target", "¿Quién va a utilizar la solución? (TARGET)"),
    ("funcionalidades", "¿Qué funcionalidades espera tener?"),
    ("expectativas", "¿Qué expectativas tiene con esta solución?"),
    ("experiencia", "¿Ha tenido experiencia previa similar a este proyecto?"),
    ("adjudicacion", "¿Cuál es la forma de adjudicación?"),
    ("criterios", "¿Cuáles son los criterios de evaluación?"),
    ("lanzamiento", "¿Cuál sería la fecha de lanzamiento?"),
    ("presupuesto", "¿Cuál es el rango del presupuesto?"),
    ("nombre_proyecto", "¿Qué nombre le pondrías al proyecto?"),
    ("notas", "¿Alguna nota general o consideración adicional?")
]

if "caso" not in st.session_state:
    st.session_state.caso = {k: "" for k, _ in REQUIRED_FIELDS}
if "chat_msgs" not in st.session_state:
    st.session_state.chat_msgs = []
if "intel_urls" not in st.session_state:
    st.session_state.intel_urls = [
        "https://babelgroup.com",
        "https://www.accenture.com",
        "https://www.ibm.com/consulting"
    ]
if "caso_finalizado" not in st.session_state:
    st.session_state.caso_finalizado = False


# ------------------ Utilidades ------------------
def calc_score(resps: dict) -> int:
    pesos = {"q1": 20, "q2": 30, "q3": 30, "q4": 5, "q5": 5}
    puntos = sum(pesos[k] for k, v in resps.items() if v is True)
    return round(puntos / 90 * 100)

def badge(ok: bool) -> str:
    return "🟢 OK" if ok else "🟡 Pendiente"

def add_msg(role, text):
    st.session_state.chat_msgs.append((role, text))

def first_missing(caso_dict):
    for k, pregunta in REQUIRED_FIELDS:
        if not str(caso_dict.get(k, "")).strip():
            return k, pregunta
    return None, None

# --------- Extracción simple de información (reglas) ---------
def extract_info_es(text: str) -> dict:
    """
    Heurísticas livianas para capturar campos del caso de negocio desde texto libre en español.
    No es IA generativa; es regex + palabras clave. Sirve para acelerar la captura.
    """
    t = text.lower().strip()
    out = {}

    # presupuesto (rangos, montos) ej: 1.5 M, $800k, 200 mil, 1 a 2 MUSD
    money_regex = r'(\$?\s?\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d+)?\s*(k|mil|m|mm|millones|usd|mxn)?)'
    m = re.search(money_regex, t)
    if m:
        out["presupuesto"] = m.group(0)

    # fecha de lanzamiento (mes/año, dd/mm/aaaa, “Q4”, “octubre 2025”, “en 3 meses”)
    f1 = re.search(r'(q[1-4]\s*\d{4}|ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic|\d{1,2}/\d{1,2}/\d{2,4}|20\d{2})', t)
    if f1:
        out["lanzamiento"] = f1.group(0)

    # objetivos / problema / solución: detecta por palabras gatillo si no hay valor previo
    if any(w in t for w in ["objetivo", "meta", "resultados de negocio", "okrs"]):
        out["objetivos"] = text
    if any(w in t for w in ["problema", "dolor", "pain", "barrera"]):
        out["problema"] = text
    if any(w in t for w in ["solución", "resolver", "propuesta", "implantar", "implementar"]):
        out["solucion"] = text

    # target
    if any(w in t for w in ["usuario", "usuarios", "target", "comercial", "marketing", "finanzas", "ventas", "operaciones"]):
        out["target"] = text

    # funcionalidades / expectativas
    if any(w in t for w in ["funcionalidad", "features", "módulo", "módulos"]):
        out["funcionalidades"] = text
    if "esper" in t or "éxito" in t or "kpi" in t:
        out["expectativas"] = text

    # experiencia previa
    if any(w in t for w in ["experiencia", "proyecto similar", "piloto", "poC", "poc", "antes hicimos"]):
        out["experiencia"] = text

    # adjudicación / criterios
    if any(w in t for w in ["adjudic", "licitación", "cotización", "3 cotizaciones", "rfi", "rfp"]):
        out["adjudicacion"] = text
    if any(w in t for w in ["criterio", "evaluación", "score", "puntos", "ponderación"]):
        out["criterios"] = text

    # nombre del proyecto
    if any(w in t for w in ["se llamará", "nombre del proyecto", "proyecto:", "codename"]):
        out["nombre_proyecto"] = text

    # notas (catch-all si usuario dice “nota”, “aclaración”)
    if any(w in t for w in ["nota", "aclaración", "consideración", "riesgo"]):
        out["notas"] = text

    return out

def render_resumen_live():
    empresa = st.session_state.lead.get("empresa") or "—"
    st.markdown("#### Resumen en vivo")
    st.markdown(f"**Empresa:** {empresa}")
    cols = st.columns(2)
    for i, (k, label) in enumerate(REQUIRED_FIELDS):
        val = st.session_state.caso.get(k, "")
        with cols[i % 2]:
            st.markdown(f"- **{label.replace('¿','').replace('?','')}**<br>{(val or '—')}", unsafe_allow_html=True)


# ------------------ UI: Métricas de cabecera ------------------
st.markdown("## 2) Calificación + Caso de negocio")
colA, colB, colC = st.columns([1, 1, 2])
with colA:
    st.metric("Score", f"{st.session_state.score}%")
with colB:
    st.metric("Calificación", badge(st.session_state.calif_listo))
with colC:
    st.metric("Lead", st.session_state.lead.get("empresa") or "—")

st.divider()

# ------------------ Pestañas ------------------
tab_calif, tab_chat, tab_intel = st.tabs(
    ["A) Calificación", "B) Caso (chat inteligente)", "C) Inteligencia competitiva"]
)

# ============ TAB A: CALIFICACIÓN ============
with tab_calif:
    st.caption("Ponderación: 20 / 30 / 30 / 5 / 5 • Requiere ≥ 70% para habilitar el chat")
    with st.form("frm_calif"):
        q1 = st.radio("¿Tiene fecha planeada para iniciar proyecto?", ["Sin responder", "Sí", "No"], index=0, horizontal=True)
        q2 = st.radio("¿Cuenta con presupuesto?", ["Sin responder", "Sí", "No"], index=0, horizontal=True)
        q3 = st.radio("¿Es un proyecto para incrementar ventas o marketing?", ["Sin responder", "Sí", "No"], index=0, horizontal=True)
        q4 = st.radio("¿El proyecto resuelve un problema de prioridad 1, 2 o 3 dentro de la empresa?", ["Sin responder", "Sí", "No"], index=0, horizontal=True)
        q5 = st.radio("¿Hablamos con tomador de decisión?", ["Sin responder", "Sí", "No"], index=0, horizontal=True)
        enviar = st.form_submit_button("Calcular calificación ✅", use_container_width=True)

    if enviar:
        resps = {
            "q1": (q1 == "Sí"),
            "q2": (q2 == "Sí"),
            "q3": (q3 == "Sí"),
            "q4": (q4 == "Sí"),
            "q5": (q5 == "Sí"),
        }
        st.session_state.score = calc_score(resps)
        st.session_state.calif_listo = st.session_state.score >= 70

    if st.session_state.calif_listo:
        st.success(f"Proyecto viable ({st.session_state.score}%). Abre la pestaña **B) Caso (chat inteligente)**.")
    else:
        st.info(f"Score actual: {st.session_state.score}%. Aún no alcanza 70%.")

# ============ TAB B: CHAT INTELIGENTE ============
with tab_chat:
    if not st.session_state.calif_listo:
        st.warning("Primero alcanza ≥ 70% en **A) Calificación** para habilitar el chat.")
    else:
        st.subheader("Caso de negocio — chat inteligente")
        st.caption("Responde en lenguaje natural. El asistente reconocerá información y solo preguntará lo que falte.")

        # Mensaje inicial
        if not st.session_state.chat_msgs:
            saludo = (
                f"Hola 👋 Soy tu asistente. Vamos a construir el caso de negocio para **{st.session_state.lead.get('empresa') or 'tu empresa'}**.\n\n"
                "Cuéntame primero **los objetivos de negocio** y **el problema a resolver**. "
                "Puedes escribir todo junto; iré extrayendo lo importante."
            )
            add_msg("assistant", saludo)

        # Render de historial
        for role, text in st.session_state.chat_msgs:
            with st.chat_message(role):
                st.write(text)

        # Entrada del usuario
        user = st.chat_input("Escribe tu mensaje…")
        if user:
            add_msg("user", user)

            # 1) extraer datos automáticos de lo que escribió
            updates = extract_info_es(user)
            # Solo rellenamos campos vacíos para no pisar ediciones previas
            for k, v in updates.items():
                if k in st.session_state.caso and not st.session_state.caso[k]:
                    st.session_state.caso[k] = v

            # 2) decidir qué preguntar después
            faltante_key, faltante_preg = first_missing(st.session_state.caso)
            if faltante_key:
                # feedback: lo que entendí
                entendidos = [label for (k, label) in REQUIRED_FIELDS if updates.get(k)]
                pref = ""
                if entendidos:
                    pref = "Anotado: " + "; ".join([l.replace("¿", "").replace("?", "") for l in entendidos]) + ". "
                respuesta = pref + faltante_preg
            else:
                respuesta = (
                    "Perfecto, ya tengo todo el caso capturado. "
                    "Puedes revisar el **resumen en vivo** abajo y presionar **Finalizar caso** cuando esté listo."
                )

            add_msg("assistant", respuesta)

        # Resumen en vivo y botones
        st.divider()
        render_resumen_live()

        c1, c2, c3 = st.columns([1,1,2])
        with c1:
            if st.button("Limpiar chat", use_container_width=True):
                st.session_state.chat_msgs = []
        with c2:
            if all(st.session_state.caso[k] for k, _ in REQUIRED_FIELDS):
                if st.button("Finalizar caso ✅", type="primary", use_container_width=True):
                    st.session_state.caso_finalizado = True
                    add_msg("assistant", "Caso finalizado. Puedes generar el PDF en tu módulo o continuar con Inteligencia competitiva.")
            else:
                st.disabled = True
                st.button("Finalizar caso ✅", disabled=True, use_container_width=True)

# ============ TAB C: INTELIGENCIA COMPETITIVA ============
with tab_intel:
    st.subheader("Inteligencia competitiva (RAG listo)")
    st.caption("Pega 1 URL por línea (Babel y competidores). Esto luego consultará tu índice RAG.")
    urls = st.text_area("URLs", "\n".join(st.session_state.intel_urls), height=120)
    st.session_state.intel_urls = [u.strip() for u in urls.splitlines() if u.strip()]

    col1, col2 = st.columns([1,1])
    with col1:
        st.write("**Sitios**")
        st.write(", ".join([u.split("//")[-1].split("/")[0] for u in st.session_state.intel_urls]))
    with col2:
        st.write("**Sugerencias (simulado)**")
        st.write(
            "• Babel: modernización, datos/IA, automatización, time-to-value.\n"
            "• Accenture: transformación digital end-to-end, consultoría.\n"
            "• IBM Consulting: datos e integración empresarial."
        )
    st.info("Cuando actives tu RAG, esta pestaña generará la comparativa automática contra las URLs indexadas.")
