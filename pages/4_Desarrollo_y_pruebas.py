# pages/4_Desarrollo_y_Pruebas.py
# Fase 4: Checklist + Chat + Generación de PDF (con soporte de acentos via DejaVuSans.ttf)

import os
import streamlit as st
from fpdf import FPDF
from openai import OpenAI

st.set_page_config(page_title="Fase 4 - Desarrollo/Pruebas", layout="wide")
st.title("🛠️ Fase 4: Desarrollo y Pruebas")

# --- Guardas de flujo (necesita haber pasado Fase 1) ---
if not st.session_state.get("evaluacion_ok", False):
    st.warning("La oportunidad no alcanzó 70% en Evaluación. Ve a **Fase 1** primero.")
    st.stop()

# --- Estado base ---
st.session_state.setdefault("ready_for_pdf", False)
st.session_state.setdefault("dev_checklist", {
    "casos_uso": False,
    "pruebas": False,
    "riesgos": False,
    "aprobacion": False,
})
st.session_state.setdefault("dev_chat", [])      # historial de chat
st.session_state.setdefault("devtest", {})       # notas de pruebas opcionales

# ----------------- Utilidades PDF -----------------
FONT_PATH = "DejaVuSans.ttf"  # Debe existir en la raíz del repo (tú ya lo subiste)

def clean(t: str) -> str:
    if not t:
        return ""
    return str(t).replace("\r", "").replace("\x00", "").strip()

def build_pdf() -> str:
    """
    Construye el PDF con datos de todas las fases y lo guarda en disco.
    Retorna la ruta del archivo generado.
    """
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

    # Fuente unicode para acentos/ñ
    if os.path.exists(FONT_PATH):
        pdf.add_font("DejaVu", "", FONT_PATH, uni=True)
        pdf.set_font("DejaVu", "", 14)
    else:
        # Fallback (Arial no imprime bien acentos, pero evita crash si no está la TTF)
        pdf.set_font("Arial", "", 14)

    # Logo (si existe)
    if os.path.exists("logo_babel.jpeg"):
        try:
            pdf.image("logo_babel.jpeg", x=10, y=8, w=28)
        except Exception:
            pass
    pdf.ln(10)

    pdf.set_font_size(18)
    pdf.cell(0, 10, clean("Caso de Negocio - Babel"), ln=1, align="C")
    pdf.set_font_size(11)
    pdf.cell(0, 7, clean("Reporte generado desde Fase 4 (Desarrollo y Pruebas)"), ln=1, align="C")
    pdf.ln(5)

    # Resumen general
    pdf.set_font_size(12)
    pdf.multi_cell(0, 7, clean(f"Score de Evaluación (Fase 1): {score}%"))
    pdf.multi_cell(0, 7, clean(f"Proyectos en memoria: {len(proyectos)}"))
    pdf.multi_cell(0, 7, clean(f"Listo para PDF (Fase 4): {'Sí' if st.session_state.get('ready_for_pdf') else 'No'}"))
    pdf.ln(3)

    # Sección: detalle de evaluación
    pdf.set_font_size(14)
    pdf.cell(0, 8, clean("Evaluación (detalle)"), ln=1)
    pdf.set_font_size(11)
    for k, texto, peso in detalle_preguntas:
        r = eval_answers.get(k, "No")
        pts = peso if r == "Sí" else 0
        pdf.multi_cell(0, 6, clean(f"• {texto} → {r} (peso {peso}, pts {pts})"))
    pdf.ln(3)

    # Sección: Diseño (si existe)
    if diseno:
        pdf.set_font_size(14)
        pdf.cell(0, 8, clean("Diseño de la solución (resumen)"), ln=1)
        pdf.set_font_size(11)
        for k, v in diseno.items():
            pdf.multi_cell(0, 6, clean(f"• {k}: {v}"))
        pdf.ln(3)

    # Sección: Notas de pruebas (fase 4)
    if notas:
        pdf.set_font_size(14)
        pdf.cell(0, 8, clean("Notas de desarrollo/pruebas"), ln=1)
        pdf.set_font_size(11)
        pdf.multi_cell(0, 6, clean(notas))
        pdf.ln(3)

    # (Opcional) anexo con últimos mensajes del chat
    chat = st.session_state.get("dev_chat", [])[-6:]  # últimos 6 turnos
    if chat:
        pdf.set_font_size(14)
        pdf.cell(0, 8, clean("Anexo: Fragmento de conversación (Fase 4)"), ln=1)
        pdf.set_font_size(11)
        for m in chat:
            role = "Cliente" if m["role"] == "user" else "Agente"
            pdf.multi_cell(0, 6, clean(f"{role}: {m['content']}"))
        pdf.ln(3)

    output_path = "caso_negocio_babel.pdf"
    pdf.output(output_path)
    return output_path

# ----------------- UI -----------------
left, right = st.columns([1, 2], gap="large")

# --------- Columna izquierda: checklist y “Listo para PDF” ----------
with left:
    st.subheader("Checklist de preparación")
    st.caption("Marca los puntos cuando estén listos. Luego podrás generar el PDF aquí mismo.")

    st.session_state["dev_checklist"]["casos_uso"] = st.checkbox("✅ Casos de uso definidos", value=st.session_state["dev_checklist"]["casos_uso"])
    st.session_state["dev_checklist"]["pruebas"]  = st.checkbox("✅ Criterios de prueba definidos", value=st.session_state["dev_checklist"]["pruebas"])
    st.session_state["dev_checklist"]["riesgos"]  = st.checkbox("✅ Riesgos y mitigaciones", value=st.session_state["dev_checklist"]["riesgos"])
    st.session_state["dev_checklist"]["aprobacion"] = st.checkbox("✅ Aprobación interna", value=st.session_state["dev_checklist"]["aprobacion"])

    all_ok = all(st.session_state["dev_checklist"].values())

    st.markdown("---")
    if all_ok:
        st.success("✅ Checklist completo.")
    else:
        st.info("Completa el checklist para poder marcar **Listo para PDF** y generar el documento.")

    # Botón: marcar listo
    if st.button("📄 Marcar **Listo para PDF**"):
        if all_ok:
            st.session_state["ready_for_pdf"] = True
            st.success("¡Perfecto! Marcado como **Listo para PDF**.")
            st.rerun()  # refresca para que se vea el estado actualizado
        else:
            st.warning("Faltan puntos del checklist.")

    st.metric("Listo para PDF", "✅ Sí" if st.session_state["ready_for_pdf"] else "❌ No")
    st.markdown("---")

    # Botón: Generar PDF aquí mismo (solo si está listo)
    disabled_pdf = not st.session_state["ready_for_pdf"]
    if disabled_pdf:
        st.button("⬇️ Generar PDF (habilitado al marcar 'Listo para PDF')", disabled=True)
    else:
        if st.button("⬇️ Generar PDF (desde Fase 4)"):
            # Validación de fuente unicode
            if not os.path.exists(FONT_PATH):
                st.error(f"No se encontró **{FONT_PATH}** en la raíz del repo. Súbela para que salgan bien los acentos.")
            else:
                try:
                    pdf_path = build_pdf()
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            label="Descargar archivo PDF",
                            data=f,
                            file_name="caso_negocio_babel.pdf",
                            mime="application/pdf"
                        )
                    st.success("PDF generado correctamente.")
                except Exception as e:
                    st.error(f"Error al generar el PDF: {e}")

# --------- Columna derecha: chat del agente ----------
with right:
    st.subheader("💬 Chat con el agente (soporte técnico/funcional)")

    # Preparar cliente OpenAI
    api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
    if not api_key:
        st.info("Agrega tu **OPENAI_API_KEY** en *Settings → Secrets* para usar el chat.")
    else:
        client = OpenAI(api_key=api_key)

        # Contexto del proyecto
        score = st.session_state.get("score_total", 0)
        eval_answers = st.session_state.get("eval_answers", {})
        diseno = st.session_state.get("diseno", {})
        proyectos = st.session_state.get("proyectos", [])

        system_prompt = f"""
Eres un asistente técnico de Babel. Ayudas a cerrar la Fase 4 (desarrollo/pruebas) del caso de negocio.
Contexto:
- Score de evaluación: {score}%
- Respuestas evaluación: {eval_answers}
- Diseño: {diseno}
- Proyectos en memoria: {len(proyectos)}
Da respuestas concretas con listas; si piden pruebas, entrega casos de prueba y criterios de aceptación.
"""

        # Historial
        with st.container(height=420, border=True):
            if not st.session_state["dev_chat"]:
                st.markdown("> 👇 Escribe tu primera pregunta en el cuadro de abajo.")
            for m in st.session_state["dev_chat"]:
                if m["role"] == "user":
                    with st.chat_message("user"):
                        st.write(m["content"])
                else:
                    with st.chat_message("assistant"):
                        st.write(m["content"])

        # Entrada
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

        with st.expander("📎 Guardar notas de pruebas en el estado (opcional)"):
            notas = st.text_area("Pega aquí notas/criterios de prueba a conservar", height=140)
            if st.button("Guardar notas en estado"):
                st.session_state["devtest"]["notas"] = notas
                st.success("Notas guardadas; se incluyen en el PDF.")
