# pages/4_Desarrollo_y_Pruebas.py – Checklist + Chat + Generación/descarga de PDF
import os
import streamlit as st
from fpdf import FPDF
from openai import OpenAI

st.set_page_config(page_title="Fase 4 - Desarrollo y Pruebas", layout="wide")
st.title("🛠️ Fase 4: Desarrollo y Pruebas")

# Guardas de flujo
if not st.session_state.get("evaluacion_ok", False):
    st.warning("La oportunidad no alcanzó 70% en Evaluación. Ve a **Fase 1**.")
    st.stop()

# Estado compartido
st.session_state.setdefault("ready_for_pdf", False)
st.session_state.setdefault("dev_checklist", {
    "casos_uso": False,
    "pruebas": False,
    "riesgos": False,
    "aprobacion": False,
})
st.session_state.setdefault("dev_chat", [])
st.session_state.setdefault("devtest", {})  # devtest['notas']

FONT_PATH = "DejaVuSans.ttf"

def clean_text(text: str) -> str:
    if not text:
        return ""
    t = str(text).replace("\r", " ").replace("\x00", "")
    return t if t.strip() else " "

def pdf_header(pdf: FPDF, title: str):
    if os.path.exists("logo_babel.jpeg"):
        try:
            pdf.image("logo_babel.jpeg", x=10, y=8, w=28)
        except Exception:
            pass
    pdf.ln(10)
    pdf.set_font_size(18)
    pdf.cell(0, 10, clean_text(title), ln=1, align="C")
    pdf.set_font_size(11)
    pdf.cell(0, 7, clean_text("Reporte generado desde Fase 4 (Desarrollo y Pruebas)"), ln=1, align="C")
    pdf.ln(4)

def build_pdf() -> str:
    score = st.session_state.get("score_total", 0)
    eval_answers = st.session_state.get("eval_answers", {})
    diseno = st.session_state.get("diseno", {})
    proyectos = st.session_state.get("proyectos", [])
    notas = st.session_state.get("devtest", {}).get("notas", "")

    detalle_preguntas = [
        ("q1", "¿Tiene fecha planeada para iniciar proyecto?", 20),
        ("q2", "¿Cuenta con presupuesto?", 30),
        ("q3", "¿Es un proyecto para incrementar ventas o marketing?", 30),
        ("q4", "¿El proyecto resuelve un problema de prioridad 1, 2 o 3?", 5),
        ("q5", "¿Hablamos con tomador de decisión?", 5),
    ]

    pdf = FPDF()
    pdf.add_page()

    if os.path.exists(FONT_PATH):
        pdf.add_font("DejaVu", "", FONT_PATH, uni=True)
        pdf.set_font("DejaVu", "", 14)
    else:
        pdf.set_font("Arial", "", 14)

    pdf_header(pdf, "Caso de Negocio - Babel")

    pdf.set_font_size(12)
    pdf.multi_cell(190, 8, clean_text(f"Score de Evaluación (Fase 1): {score}%"), align="L")
    pdf.multi_cell(190, 8, clean_text(f"Proyectos en memoria: {len(proyectos)}"), align="L")
    pdf.multi_cell(190, 8, clean_text(f"Listo para PDF (Fase 4): {'Sí' if st.session_state.get('ready_for_pdf') else 'No'}"), align="L")
    pdf.ln(2)

    pdf.set_font_size(14)
    pdf.cell(0, 8, clean_text("Evaluación (detalle)"), ln=1)
    pdf.set_font_size(11)
    for k, texto, peso in detalle_preguntas:
        r = eval_answers.get(k, "No")
        pts = peso if r == "Sí" else 0
        pdf.multi_cell(190, 6, clean_text(f"• {texto} → {r} (peso {peso}, pts {pts})"), align="L")
    pdf.ln(2)

    if diseno:
        pdf.set_font_size(14)
        pdf.cell(0, 8, clean_text("Diseño de la solución (resumen)"), ln=1)
        pdf.set_font_size(11)
        for k, v in diseno.items():
            pdf.multi_cell(190, 6, clean_text(f"• {k}: {v}"), align="L")
        pdf.ln(2)

    if notas:
        pdf.set_font_size(14)
        pdf.cell(0, 8, clean_text("Notas de desarrollo/pruebas"), ln=1)
        pdf.set_font_size(11)
        pdf.multi_cell(190, 6, clean_text(notas), align="L")
        pdf.ln(2)

    chat = st.session_state.get("dev_chat", [])[-6:]
    if chat:
        pdf.set_font_size(14)
        pdf.cell(0, 8, clean_text("Anexo: Conversación (Fase 4)"), ln=1)
        pdf.set_font_size(11)
        for m in chat:
            role = "Cliente" if m["role"] == "user" else "Agente"
            pdf.multi_cell(190, 6, clean_text(f"{role}: {m['content']}"), align="L")
        pdf.ln(2)

    out = "caso_negocio_babel.pdf"
    pdf.output(out)
    return out

left, right = st.columns([1, 2], gap="large")

with left:
    st.subheader("Checklist de preparación")
    st.caption("Marca los puntos. Cuando todo esté listo, podrás generar el PDF aquí mismo.")

    dc = st.session_state["dev_checklist"]
    dc["casos_uso"]  = st.checkbox("✅ Casos de uso definidos", value=dc["casos_uso"])
    dc["pruebas"]    = st.checkbox("✅ Criterios de prueba definidos", value=dc["pruebas"])
    dc["riesgos"]    = st.checkbox("✅ Riesgos y mitigaciones", value=dc["riesgos"])
    dc["aprobacion"] = st.checkbox("✅ Aprobación interna", value=dc["aprobacion"])

    all_ok = all(dc.values())
    st.markdown("---")
    st.success("✅ Checklist completo.") if all_ok else st.info("Completa el checklist para habilitar el PDF.")

    if st.button("📄 Marcar **Listo para PDF**"):
        if all_ok:
            st.session_state["ready_for_pdf"] = True
            st.success("¡Listo para PDF marcado!")
            st.rerun()
        else:
            st.warning("Aún faltan puntos del checklist.")

    st.metric("Listo para PDF", "Sí" if st.session_state["ready_for_pdf"] else "No")
    st.markdown("---")

    if not st.session_state["ready_for_pdf"]:
        st.button("⬇️ Generar PDF (habilitado al marcar 'Listo para PDF')", disabled=True)
    else:
        if st.button("⬇️ Generar PDF (desde Fase 4)"):
            if not os.path.exists(FONT_PATH):
                st.error("No se encontró **DejaVuSans.ttf** en la raíz del repo.")
            else:
                try:
                    path = build_pdf()
                    with open(path, "rb") as f:
                        st.download_button("Descargar archivo PDF", f, file_name="caso_negocio_babel.pdf",
                                           mime="application/pdf")
                    st.success("PDF generado correctamente.")
                except Exception as e:
                    st.error(f"Error al generar el PDF: {e}")

with right:
    st.subheader("💬 Chat con el agente")

    api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
    if not api_key:
        st.info("Agrega tu **OPENAI_API_KEY** en Settings → Secrets para usar el chat.")
    else:
        client = OpenAI(api_key=api_key)

        score = st.session_state.get("score_total", 0)
        eval_answers = st.session_state.get("eval_answers", {})
        diseno = st.session_state.get("diseno", {})
        proyectos = st.session_state.get("proyectos", [])

        system_prompt = f"""
Eres un asistente técnico de Babel. Ayudas a cerrar la Fase 4 (desarrollo/pruebas).
Contexto:
- Score evaluación: {score}%
- Respuestas evaluación: {eval_answers}
- Diseño: {diseno}
- Proyectos en memoria: {len(proyectos)}
Responde con listas claras y criterios de aceptación cuando pidan pruebas.
"""

        with st.container(height=420, border=True):
            if not st.session_state["dev_chat"]:
                st.markdown("> 👇 Escribe tu primera pregunta en el cuadro de abajo.")
            for m in st.session_state["dev_chat"]:
                with st.chat_message("user" if m["role"] == "user" else "assistant"):
                    st.write(m["content"])

        user_msg = st.chat_input("Pregunta al agente…")
        if user_msg:
            st.session_state["dev_chat"].append({"role": "user", "content": user_msg})
            messages = [{"role": "system", "content": system_prompt}] + st.session_state["dev_chat"]
            try:
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=0.3,
                )
                answer = resp.choices[0].message.content.strip()
            except Exception as e:
                answer = f"Hubo un error llamando a la API: {e}"
            st.session_state["dev_chat"].append({"role": "assistant", "content": answer})
            st.rerun()

        cols = st.columns(2)
        if cols[0].button("🧹 Limpiar chat"):
            st.session_state["dev_chat"] = []
            st.rerun()

        with st.expander("📎 Guardar notas de pruebas (opcional)"):
            notas = st.text_area("Notas/criterios de prueba", height=140)
            if st.button("Guardar notas"):
                st.session_state["devtest"]["notas"] = notas
                st.success("Notas guardadas; se incluirán en el PDF.")
