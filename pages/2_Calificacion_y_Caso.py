# pages/2_Calificación_y_Caso.py
import streamlit as st
import re
from datetime import datetime

# ------------------------------ Config ------------------------------
st.set_page_config(page_title="Calificación + Caso", page_icon="🧩", layout="wide")
st.title("2) Calificación + Caso (chat) + Competencia")

# ------------------------------ Cuestionario oficial ------------------------------
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

# ------------------------------ Parsers / señales ------------------------------
money_rx = re.compile(r"(?:USD|US\$|MXN|\$|EUR|€)\s?([\d.,]+)|([\d.,]+)\s?(?:USD|US\$|MXN|EUR|€)", re.I)
date_rx  = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")
month_words = ("enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre","q1","q2","q3","q4","semana","mes")
roles_rx = re.compile(r"\b(CTO|CFO|CEO|COO|CIO|CMO|Compras|Procurement|IT|Operaciones|Soporte|Ventas|Marketing|Finanzas|RH|Direcci[oó]n|Gerente|Jefe|L[ií]der)\b", re.I)
award_words = ("licitación","invitación","adjudicación directa","concurso","RFP","RFQ","marco","convenio")
criteria_words = ("precio","calidad","tiempo","soporte","SLA","experiencia","referencias","ROI","seguridad","cumplimiento","integración","capacidad","plazos")

def has_money(t: str) -> bool:
    return bool(money_rx.search(t or ""))

def has_date(t: str) -> bool:
    t = t or ""
    return bool(date_rx.search(t)) or any(w in t.lower() for w in month_words)

def count_list_items(t: str) -> int:
    t = (t or "").strip()
    return t.count(",") + t.count(";") + (1 if len(t) > 0 else 0)

def mentions_roles_or_area(t: str) -> bool:
    t = t or ""
    return bool(roles_rx.search(t)) or any(w in t.lower() for w in ["usuarios","operadores","clientes","agentes","analistas","administradores"])

def mentions_any(t: str, words) -> bool:
    t = (t or "").lower()
    return any(w in t for w in words)

def has_kpis(t: str) -> bool:
    return bool(re.search(r"\bROI|NPS|CSAT|SLA|MTTR|conversi[oó]n|ingres|ahorro|cost|%|\bhoras\b|\bd[ií]as\b", t or "", re.I))

# ------------------------------ Tabs ------------------------------
tabs = st.tabs(["A) Calificación", "B) Caso (chat inteligente)", "C) Competencia & PDF"])

# ============================== TAB A: Calificación ==============================
with tabs[0]:
    st.subheader("Calificación del lead (20/30/30/5/5)")
    st.write("Debes alcanzar un **70%** para habilitar el chat del caso.")

    c1, c2 = st.columns(2)
    fecha = c1.radio("¿Tiene fecha planeada para iniciar proyecto?", ["Sí", "No"], index=None, key="cal_fecha")
    marketing = c2.radio("¿Es un proyecto para incrementar ventas o marketing?", ["Sí", "No"], index=None, key="cal_mkt")
    presupuesto = c1.radio("¿Cuenta con presupuesto?", ["Sí", "No"], index=None, key="cal_pres")
    prioridad = c2.radio("¿El proyecto resuelve un problema de prioridad 1, 2 o 3?", ["Sí", "No"], index=None, key="cal_prio")
    decision = c1.radio("¿Hablamos con tomador de decisión?", ["Sí", "No"], index=None, key="cal_dec")

    if st.button("Calcular calificación", use_container_width=True):
        if None in (
            st.session_state.get("cal_fecha"),
            st.session_state.get("cal_mkt"),
            st.session_state.get("cal_pres"),
            st.session_state.get("cal_prio"),
            st.session_state.get("cal_dec"),
        ):
            st.warning("⚠️ Responde las 5 preguntas antes de calcular.")
        else:
            score = 0
            if fecha == "Sí": score += 20
            if marketing == "Sí": score += 30
            if presupuesto == "Sí": score += 30
            if prioridad == "Sí": score += 5
            if decision == "Sí": score += 5
            st.session_state.lead_score = score
            if score >= 70:
                st.success(f"Calificación: **90/100**" if score==90 else f"Calificación: **{score}/100**")
                st.info("Puedes pasar a la pestaña **B) Caso (chat)**.")
            else:
                st.warning(f"Calificación: **{score}/100** — Aún no alcanza el umbral de 70.")

    st.caption("Responde las 5 preguntas para calcular la calificación.")

# ============================== TAB B: Chat del Caso ==============================
with tabs[1]:
    if st.session_state.get("lead_score", 0) < 70:
        st.warning("⚠️ Primero completa la **calificación** y alcanza al menos **70** para continuar.")
    else:
        st.success("✅ Lead calificado. Inicia el **chat**: iré construyendo el **Plan de Negocio** en la derecha.")

        # ---- Estado del chat ----
        if "case_chat_msgs" not in st.session_state:
            st.session_state.case_chat_msgs = []
        if "case_answers" not in st.session_state:
            st.session_state.case_answers = {k: "" for k, _ in QUESTIONS}
        if "case_current_key" not in st.session_state:
            st.session_state.case_current_key = QUESTIONS[0][0]
        if "ready_for_pdf" not in st.session_state:
            st.session_state.ready_for_pdf = False

        def next_unanswered_key():
            for k, _ in QUESTIONS:
                if not st.session_state.case_answers.get(k, "").strip():
                    return k
            return None

        def question_for(key):
            for k, q in QUESTIONS:
                if k == key:
                    return q
            return "¿Algo más?"

        # IA local: pulido ligero + rellenos prudentes
        def ai_refine(label, text):
            t = (text or "").strip()
            if not t:
                if label == "funcionalidades":
                    return "MVP con dashboard, gestión de usuarios/roles, alertas y exportación de reportes."
                if label == "criterios":
                    return "Precio total, calidad de entrega, tiempo de implementación, soporte/SLA y experiencia comprobable."
                if label == "lanzamiento":
                    return "Definir hito (mes/fecha o trimestre) y plan de piloto previo."
                if label == "presupuesto":
                    return "Rango estimado a definir con Finanzas y Compras."
                if label == "caso":
                    return "Se espera ROI positivo mediante ahorro operativo y mejora de KPIs de servicio."
                return "Pendiente por confirmar."
            t = t.replace("\n", " ").strip()
            if label in ("objetivos", "problema", "solucion", "expectativas", "caso") and not has_kpis(t):
                t += " (Incluir KPIs: ROI esperado, ahorro %, mejora de SLA/MTTR, conversión o NPS/CSAT)."
            if label == "funcionalidades" and (t.count(",") + t.count(";")) < 2:
                t += " (Detalle al menos 3–4 funcionalidades del MVP)."
            return t

        # Build del plan (sin depender de funciones externas)
        def build_plan(a: dict):
            objetivos = ai_refine("objetivos", a.get("objetivos", ""))
            problema  = ai_refine("problema", a.get("problema", ""))
            solucion  = ai_refine("solucion", a.get("solucion", ""))
            target    = ai_refine("target", a.get("target", ""))
            funcs     = ai_refine("funcionalidades", a.get("funcionalidades", ""))
            expectativas = ai_refine("expectativas", a.get("expectativas", ""))
            experiencia  = ai_refine("experiencia", a.get("experiencia", ""))
            adjudic      = ai_refine("adjudicacion", a.get("adjudicacion", ""))
            criterios    = ai_refine("criterios", a.get("criterios", ""))
            lanzamiento  = ai_refine("lanzamiento", a.get("lanzamiento", ""))
            presupuesto  = ai_refine("presupuesto", a.get("presupuesto", ""))
            caso         = ai_refine("caso", a.get("caso", ""))
            nombre       = (a.get("nombre", "") or "").strip() or "(pendiente)"
            notas        = (a.get("notas", "") or "").strip()

            faltantes = [k for k, _ in QUESTIONS if not (a.get(k, "") or "").strip()]
            checklist = ", ".join(faltantes) if faltantes else "Completo ✅"

            # Detección local de riesgos/objeciones en 'notas'
            risk_rx = re.compile(r"\b(riesgo|objeci[oó]n|costo|seguridad|legal|compliance|privacidad|cambio|adopci[oó]n|integraci[oó]n|soporte)\b", re.I)
            notas_tienen_riesgos = bool(risk_rx.search(notas or ""))

            # Siguiente paso sugerido (ligero)
            siguiente = (
                "Proponer **POC** de 2 semanas con alcance, métricas y responsables."
                if (has_kpis(expectativas) or has_kpis(caso)) else
                "Agendar **workshop** (90 min) para cerrar funcionalidades, KPIs y timeline."
            )

            md = f"""
# {nombre}

## 1. Resumen ejecutivo
**Objetivos de negocio:** {objetivos}

**Problema a resolver:** {problema}

**Solución esperada:** {solucion}

**TARGET / usuarios:** {target}

---

## 2. Alcance y MVP
**Funcionalidades (MVP):** {funcs}

**Expectativas de valor:** {expectativas}

**Caso de negocio (beneficios/KPIs):** {caso}

---

## 3. Plan de entrega
**Fecha de lanzamiento / hito:** {lanzamiento}

**Tipo de adjudicación:** {adjudic}

**Criterios de evaluación:** {criterios}

**Experiencia previa del cliente:** {experiencia}

---

## 4. Presupuesto
**Rango/Monto:** {presupuesto}

---

## 5. Riesgos y mitigación
**Riesgos/objeciones:** {notas if notas_tienen_riesgos else "Identificar riesgos técnicos/legales/operativos y plan de mitigación."}

---

## 6. Siguiente paso
{siguiente}

---

### Notas generales
{notas or "—"}

---

**Checklist:** {checklist}
"""
            return md, checklist

        # ---- Layout: Chat | Plan ----
        left, right = st.columns([0.56, 0.44])

        if not st.session_state.case_chat_msgs:
            st.session_state.case_chat_msgs.append(("assistant",
                "Usaremos el **cuestionario oficial**. A medida que respondas, iré armando el **Plan de Negocio** a la derecha."))
            st.session_state.case_chat_msgs.append(("assistant", question_for(st.session_state.case_current_key)))

        # Izquierda: chat
        with left:
            for role, content in st.session_state.case_chat_msgs:
                with st.chat_message(role):
                    st.markdown(content)

            user_text = st.chat_input("Escribe tu respuesta…")
            if user_text:
                cur = st.session_state.case_current_key
                st.session_state.case_chat_msgs.append(("user", user_text))
                prev = st.session_state.case_answers.get(cur, "")
                st.session_state.case_answers[cur] = (prev + " " + user_text).strip()

                # avanzar al siguiente pendiente
                nxt = next_unanswered_key()
                st.session_state.case_current_key = nxt

                if nxt:
                    st.session_state.case_chat_msgs.append(("assistant", f"Anotado. **Siguiente:** {question_for(nxt)}"))
                else:
                    st.session_state.case_chat_msgs.append(("assistant", "✅ **Plan completo.** Revisa la vista previa a la derecha."))
                st.rerun()

        # Derecha: plan en vivo + descarga
        with right:
            md, checklist = build_plan(st.session_state.case_answers)

            # Progreso (por campos completos)
            total_campos = len(QUESTIONS)
            completos = total_campos if checklist == "Completo ✅" else total_campos - checklist.count(",")
            prog = int((completos / total_campos) * 100)

            st.subheader("📋 Plan de Negocio (vivo)")
            st.progress(min(prog, 100), text=f"Progreso: {prog}%")

            with st.expander("📄 Vista previa (Markdown)", expanded=True):
                st.markdown(md)

            st.download_button(
                "⬇️ Descargar Plan (.md)",
                data=md.encode("utf-8"),
                file_name=f"Plan_de_Negocio_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                mime="text/markdown",
                use_container_width=True
            )

            # Habilitar PDF cuando esté completo
            st.session_state.ready_for_pdf = (checklist == "Completo ✅")

# ============================== TAB C: Competencia & PDF ==============================
# ============================== TAB C: Competencia & PDF ==============================
# ============================== TAB C: Competencia & PDF ==============================
# ============================== TAB C: Competencia & PDF ==============================
with tabs[2]:
    st.subheader("Competencia & PDF")

    if not st.session_state.get("ready_for_pdf"):
        st.info("Completa el **Caso (chat)** al 100% para habilitar la exportación a PDF.")
    else:
        st.success("✅ Plan de Negocio completo. **Listo para exportar en PDF**.")

        # Traer el markdown generado en el Tab B; si no está, volver a construirlo
        plan_md = st.session_state.get("plan_md")
        if not plan_md:
            plan_md, _ = build_plan(st.session_state.case_answers)

        # ---- Generar PDF usando reportlab ----
        from io import BytesIO
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Image
        from reportlab.lib.styles import getSampleStyleSheet

        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=letter,
            leftMargin=50, rightMargin=50, topMargin=80, bottomMargin=50
        )

        styles = getSampleStyleSheet()
        story = []

        # Logo (opcional)
        try:
            story.append(Image("logo_babel.jpeg", width=120, height=60))
            story.append(Spacer(1, 18))
        except Exception:
            st.caption("No se encontró 'logo_babel.jpeg' (opcional).")

        # Título
        story.append(Paragraph("<b>Plan de Negocio – Babel</b>", styles["Title"]))
        story.append(Spacer(1, 12))

        # Pasar el contenido línea por línea (markdown simplificado)
        for line in plan_md.split("\n"):
            t = line.strip()
            if not t:
                story.append(Spacer(1, 6))
                continue
            t = t.lstrip("# ").strip()  # quitar hashes de encabezado
            story.append(Paragraph(t, styles["Normal"]))
            story.append(Spacer(1, 6))

        # Crear PDF en memoria
        doc.build(story)
        pdf_data = pdf_buffer.getvalue()

        # ✅ Botón SOLO PDF
        st.download_button(
            "⬇️ Descargar Plan de Negocio (PDF)",
            data=pdf_data,
            file_name="Plan_de_Negocio_Babel.pdf",
            mime="application/pdf",            # si tu navegador sigue abriéndolo raro, usa "application/octet-stream"
            use_container_width=True
        )
