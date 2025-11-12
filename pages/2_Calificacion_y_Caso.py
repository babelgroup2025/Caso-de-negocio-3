# pages/2_Calificación_y_Caso.py
import streamlit as st
import re
from datetime import datetime

# --------------------------------------------------
# Config de página
# --------------------------------------------------
st.set_page_config(page_title="Calificación + Caso", page_icon="🧩", layout="wide")
st.title("2) Calificación + Caso (chat) + Competencia")

# --------------------------------------------------
# Constantes del caso (chat)
# --------------------------------------------------
THRESHOLD = 70

# Ponderaciones (suman 100)
WEIGHTS = {
    "objetivos": 10,
    "problema": 10,
    "solucion": 10,
    "target": 8,
    "funcionalidades": 10,
    "expectativas": 7,
    "experiencia": 5,
    "adjudicacion": 5,
    "criterios": 8,
    "lanzamiento": 7,
    "presupuesto": 10,
    "caso": 6,
    "nombre": 2,
    "notas": 2,
}

# Orden y textos EXACTOS
QUESTIONS = [
    ("objetivos",      "¿Cuáles son los **objetivos de negocio**?"),
    ("problema",       "¿Cuál es el **problema a resolver**?"),
    ("solucion",       "¿Cuál es la **solución esperada**?"),
    ("target",         "¿Quién va a utilizar la solución? — **TARGET**"),
    ("funcionalidades","¿Qué **funcionalidades** espera tener?"),
    ("expectativas",   "¿Qué **expectativas** tiene con esta solución?"),
    ("experiencia",    "¿Ha tenido **experiencia previa** similar a este proyecto?"),
    ("adjudicacion",   "¿Cuál es la **forma de adjudicación**?"),
    ("criterios",      "¿Cuáles son los **criterios de evaluación**?"),
    ("lanzamiento",    "¿Cuál sería la **fecha de lanzamiento**?"),
    ("presupuesto",    "¿Cuál es el **rango del presupuesto**?"),
    ("caso",           "**Caso de negocio:** (beneficios, ROI/ahorros/KPIs)"),
    ("nombre",         "**Nombre de proyecto:**"),
    ("notas",          "**Notas generales:**"),
]

# --------------------------------------------------
# Parsers / señales para el scoring del chat
# --------------------------------------------------
money_rx = re.compile(r"(?:USD|US\$|MXN|\$|EUR|€)\s?([\d.,]+)|([\d.,]+)\s?(?:USD|US\$|MXN|EUR|€)", re.I)
date_rx  = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")
month_words = ("enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre","q1","q2","q3","q4","semana","mes")
roles_rx = re.compile(r"\b(CTO|CFO|CEO|COO|CIO|CMO|Compras|Procurement|IT|Operaciones|Soporte|Ventas|Marketing|Finanzas|RH|Direcci[oó]n|Gerente|Jefe|L[ií]der)\b", re.I)
award_words = ("licitación","invitación","adjudicación directa","concurso","RFP","RFQ","marco","convenio")
criteria_words = ("precio","calidad","tiempo","soporte","SLA","experiencia","referencias","ROI","seguridad","cumplimiento","integración","capacidad","plazos")

def has_money(t): return bool(money_rx.search(t or ""))
def has_date(t): 
    t = t or ""
    return bool(date_rx.search(t)) or any(w in t.lower() for w in month_words)
def count_list_items(t): 
    t = (t or "").strip()
    return t.count(",") + t.count(";") + (1 if len(t)>0 else 0)
def mentions_roles_or_area(t): 
    t = t or ""
    return bool(roles_rx.search(t)) or any(w in t.lower() for w in ["usuarios","operadores","clientes","agentes","analistas","administradores"])
def mentions_any(t, words): 
    t = (t or "").lower()
    return any(w in t for w in words)
def has_kpis(t): 
    return bool(re.search(r"\bROI|NPS|CSAT|SLA|MTTR|conversi[oó]n|ingres|ahorro|cost|%|\bhoras\b|\bd[ií]as\b", t or "", re.I))

def partial_score(key, text):
    text = (text or "").strip()
    if not text: return 0
    w = WEIGHTS[key]
    words = len(text.split())

    if key in ("objetivos","problema","solucion","caso"):
        base = 1.0 if words >= 12 else 0.6
        bonus = 0.15 if has_kpis(text) else 0
        return round(w * min(1.0, base + bonus))
    if key == "target":
        return round(w * (1.0 if mentions_roles_or_area(text) else 0.5))
    if key == "funcionalidades":
        items = count_list_items(text)
        return round(w * (1.0 if items >= 4 else 0.7 if items >=2 else 0.4))
    if key == "expectativas":
        return round(w * (1.0 if has_kpis(text) else 0.6))
    if key == "experiencia":
        return round(w * (1.0 if any(x in text.lower() for x in ["sí","si","ya","anterior","previa","hemos"]) else 0.6))
    if key == "adjudicacion":
        return round(w * (1.0 if mentions_any(text, award_words) else 0.5))
    if key == "criterios":
        return round(w * (1.0 if mentions_any(text, criteria_words) and count_list_items(text)>=3 else 0.6))
    if key == "lanzamiento":
        return round(w * (1.0 if has_date(text) else 0.5))
    if key == "presupuesto":
        return round(w * (1.0 if has_money(text) else 0.5))
    if key in ("nombre","notas"):
        return round(w * (1.0 if len(text)>=3 else 0.3))
    return 0

def compute_score(answers):
    total = 0
    for k, _ in QUESTIONS:
        total += partial_score(k, answers.get(k,""))
    return int(total)

# --------------------------------------------------
# Tabs
# --------------------------------------------------
tabs = st.tabs(["A) Calificación", "B) Caso (chat inteligente)", "C) Competencia & PDF"])

# ------------------------- TAB A: Calificación -------------------------
with tabs[0]:
    st.subheader("Calificación del lead (20/30/30/5/5)")
    st.write("Debes alcanzar un **70%** para habilitar el chat del caso.")

    # Radios de calificación rápida (Sí/No)
    c1, c2 = st.columns(2)
    fecha = c1.radio("¿Tiene fecha planeada para iniciar proyecto?", ["Sí", "No"], key="cal_fecha")
    marketing = c2.radio("¿Es un proyecto para incrementar ventas o marketing?", ["Sí", "No"], key="cal_mkt")
    presupuesto = c1.radio("¿Cuenta con presupuesto?", ["Sí", "No"], key="cal_pres")
    prioridad = c2.radio("¿El proyecto resuelve un problema de prioridad 1, 2 o 3?", ["Sí", "No"], key="cal_prio")
    decision = c1.radio("¿Hablamos con tomador de decisión?", ["Sí", "No"], key="cal_dec")

    if st.button("Calcular calificación", use_container_width=True):
        score = 0
        if fecha == "Sí": score += 20
        if marketing == "Sí": score += 30
        if presupuesto == "Sí": score += 30
        if prioridad == "Sí": score += 5
        if decision == "Sí": score += 5
        st.session_state.lead_score = score
        if score >= 70:
            st.success(f"Calificación: **{score}/100** ✅ — Puedes pasar a la pestaña **B) Caso (chat)**.")
        else:
            st.warning(f"Calificación: **{score}/100** ⚠️ — Aún no alcanza el umbral de 70.")

    st.caption("Responde las 5 preguntas para calcular la calificación.")

# ------------------------- TAB B: Chat del Caso -------------------------
with tabs[1]:
    # Bloqueo si no alcanza la calificación mínima
    if st.session_state.get("lead_score", 0) < 70:
        st.warning("⚠️ Primero completa la **calificación** y alcanza al menos **70** para continuar.")
    else:
        st.success("✅ Lead calificado. Puedes iniciar el **chat del caso de negocio**.")

        # ---------- Estado del chat (prefijo 'case_' para evitar colisiones) ----------
        if "case_chat_msgs" not in st.session_state:
            st.session_state.case_chat_msgs = []
        if "case_answers" not in st.session_state:
            st.session_state.case_answers = {k: "" for k, _ in QUESTIONS}
        if "case_current_key" not in st.session_state:
            st.session_state.case_current_key = QUESTIONS[0][0]
        if "score" not in st.session_state:
            st.session_state.score = 0
        if "ready_for_pdf" not in st.session_state:
            st.session_state.ready_for_pdf = False

        def next_unanswered_key():
            for k, _ in QUESTIONS:
                if not st.session_state.case_answers.get(k,"").strip():
                    return k
            return None

        def question_for(key):
            for k, q in QUESTIONS:
                if k == key: return q
            return "¿Algo más?"

        # Mensajes iniciales
        if not st.session_state.case_chat_msgs:
            st.session_state.case_chat_msgs.append(("assistant",
                "Usaremos el **cuestionario oficial**. Responde en tus palabras; iré calculando el **score** y te diré cómo fortalecer cada punto. "
                f"Umbral: **{THRESHOLD}**."))
            st.session_state.case_chat_msgs.append(("assistant", question_for(st.session_state.case_current_key)))

        # Render del historial
        for role, content in st.session_state.case_chat_msgs:
            with st.chat_message(role):
                st.markdown(content)

        # Entrada del usuario
        user_text = st.chat_input("Escribe tu respuesta…")
        if user_text:
            cur = st.session_state.case_current_key
            st.session_state.case_chat_msgs.append(("user", user_text))

            # concatena por si amplía la respuesta
            prev = st.session_state.case_answers.get(cur,"")
            st.session_state.case_answers[cur] = (prev + " " + user_text).strip()

            # Recalcular score del caso
            st.session_state.score = compute_score(st.session_state.case_answers)
            st.session_state.ready_for_pdf = st.session_state.score >= THRESHOLD

            # Tips contextuales
            tips = ""
            ans = st.session_state.case_answers[cur]
            if cur == "presupuesto" and not has_money(ans):
                tips = " *Tip:* menciona un **monto o rango** y moneda (ej. MXN 1.2–1.5M)."
            if cur == "lanzamiento" and not has_date(ans):
                tips = " *Tip:* aporta **mes/fecha** o un **hito** (ej. 'Q1 2026', '15/03/2026')."
            if cur == "funcionalidades" and count_list_items(ans) < 3:
                tips = " *Tip:* enumera funcionalidades separadas por **coma** (mín. 3–4)."
            if cur == "criterios" and not mentions_any(ans, criteria_words):
                tips = " *Tip:* incluye criterios como **precio, calidad, tiempo, soporte, SLA**."
            if cur == "target" and not mentions_roles_or_area(ans):
                tips = " *Tip:* menciona **área/rol** de los usuarios (p.ej., Operaciones, Soporte)."
            if cur in ("objetivos","problema","solucion","caso") and not has_kpis(ans):
                tips = " *Tip:* agrega **KPIs/impacto** (ROI, ahorro %, SLA, conversión…)."

            # Avanzar si ya es suficiente
            advance = partial_score(cur, ans) >= int(WEIGHTS[cur]*0.8) or len(ans.split()) > 25
            nxt = next_unanswered_key() if advance else cur
            st.session_state.case_current_key = nxt

            feedback = f"**Score actual:** {st.session_state.score}/100."
            if st.session_state.ready_for_pdf:
                feedback += " ✅ ¡Superaste el umbral! (Listo para PDF)."
            else:
                faltan = [k for k,_ in QUESTIONS if not st.session_state.case_answers.get(k,'').strip()]
                if faltan: feedback += f" Pendientes: `{', '.join(faltan)}`."

            if nxt:
                st.session_state.case_chat_msgs.append(("assistant", f"Anotado. {feedback}\n{tips}\n\n**Siguiente:** {question_for(nxt)}"))
            else:
                a = st.session_state.case_answers
                resumen = (
                    f"### Resumen — Caso de Negocio\n"
                    f"- **Nombre de proyecto:** {a['nombre']}\n"
                    f"- **Objetivos:** {a['objetivos']}\n"
                    f"- **Problema:** {a['problema']}\n"
                    f"- **Solución esperada:** {a['solucion']}\n"
                    f"- **TARGET:** {a['target']}\n"
                    f"- **Funcionalidades:** {a['funcionalidades']}\n"
                    f"- **Expectativas:** {a['expectativas']}\n"
                    f"- **Experiencia previa:** {a['experiencia']}\n"
                    f"- **Forma de adjudicación:** {a['adjudicacion']}\n"
                    f"- **Criterios de evaluación:** {a['criterios']}\n"
                    f"- **Fecha de lanzamiento:** {a['lanzamiento']}\n"
                    f"- **Rango de presupuesto:** {a['presupuesto']}\n"
                    f"- **Caso de negocio:** {a['caso']}\n"
                    f"- **Notas generales:** {a['notas']}\n\n"
                    f"**Score final:** {st.session_state.score}/100 — "
                    + ("✅ Cumple umbral (Listo para PDF)." if st.session_state.ready_for_pdf else "⚠️ Aún bajo el umbral.")
                )
                st.session_state.case_chat_msgs.append(("assistant", resumen))

            st.rerun()

# ------------------------- TAB C: Competencia & PDF -------------------------
with tabs[2]:
    st.subheader("Competencia & PDF")
    if not st.session_state.get("ready_for_pdf"):
        st.info("Completa el **Caso (chat)** y alcanza el umbral para habilitar la exportación a PDF.")
    else:
        st.success("✅ Caso completo. **Listo para PDF**.")
        st.write("Aquí puedes agregar tu comparación competitiva y (si deseas) un botón para **generar PDF** con el resumen anterior.")

# ------------------------- Sidebar: estado y reset -------------------------
with st.sidebar:
    st.subheader("Estado")
    st.metric("Calificación (lead)", st.session_state.get("lead_score", 0))
    st.metric("Score del Caso", st.session_state.get("score", 0))
    st.metric("Listo para PDF", "Sí" if st.session_state.get("ready_for_pdf", False) else "No")

    if st.button("Reiniciar sesión", use_container_width=True):
        for k in ("lead_score", "case_chat_msgs", "case_answers", "case_current_key", "score", "ready_for_pdf"):
            if k in st.session_state:
                del st.session_state[k]
        st.experimental_rerun()
