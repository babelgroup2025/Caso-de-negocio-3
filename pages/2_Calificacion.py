import streamlit as st
from fpdf import FPDF
from pathlib import Path

st.set_page_config(page_title="Calificación + Caso & PDF", page_icon="✅", layout="wide")
st.title("✅ 2) Calificación del Lead → Caso de Negocio + PDF")

# --------------------- Calificación (20/30/30/5/5) ---------------------
st.header("Calificación (20/30/30/5/5)")

with st.form("calif_form", clear_on_submit=False):
    st.caption("Responde las 5 preguntas. No hay selección por defecto.")

    q1 = st.radio("¿Tiene fecha planeada para iniciar proyecto?", ["Sí", "No"], index=None, horizontal=True, key="q1")
    q2 = st.radio("¿Cuenta con presupuesto?", ["Sí", "No"], index=None, horizontal=True, key="q2")
    q3 = st.radio("¿Es un proyecto para incrementar ventas o marketing?", ["Sí", "No"], index=None, horizontal=True, key="q3")
    q4 = st.radio("¿El proyecto resuelve un problema de prioridad 1, 2 o 3 dentro de la empresa?", ["Sí", "No"], index=None, horizontal=True, key="q4")
    q5 = st.radio("¿Hablamos con tomador de decisión?", ["Sí", "No"], index=None, horizontal=True, key="q5")

    enviado = st.form_submit_button("Calcular score")

if enviado:
    if None in (q1, q2, q3, q4, q5):
        st.warning("Por favor responde **todas** las preguntas.")
    else:
        peso = {"q1":20, "q2":30, "q3":30, "q4":5, "q5":5}
        valor = lambda ans: 1 if ans == "Sí" else 0
        puntos = (
            valor(q1)*peso["q1"] +
            valor(q2)*peso["q2"] +
            valor(q3)*peso["q3"] +
            valor(q4)*peso["q4"] +
            valor(q5)*peso["q5"]
        )
        st.session_state["score"] = puntos
        st.success(f"Calificación: **{puntos} / 100**")

score = int(st.session_state.get("score", 0))
st.metric("Score actual", f"{score}%")

# --------------------- Gate: si score >= 70, mostrar Caso + PDF ---------------------
if score < 70:
    st.info("Para continuar al **Caso de Negocio** necesitas **≥ 70%**. Ajusta tus respuestas y vuelve a calcular.")
    st.stop()

st.divider()
st.header("📄 Caso de Negocio")

# Estado por defecto del caso
if "caso_negocio" not in st.session_state:
    st.session_state["caso_negocio"] = {
        "nombre_proyecto": "",
        "presupuesto": "",
        "objetivos": "",
        "problema": "",
        "solucion_esperada": "",
        "target": "",
        "funcionalidades": "",
        "expectativas": "",
        "experiencia_previa": "",
        "adjudicacion": "",
        "criterios_eval": "",
        "fecha_lanzamiento": "",
        "notas": "",
        "propuesta_ia": st.session_state.get("propuesta_ia","")
    }
cn = st.session_state["caso_negocio"]
lead = st.session_state.get("lead", {})

with st.form("caso_form"):
    c1, c2 = st.columns(2)
    cn["nombre_proyecto"] = c1.text_input("Nombre de proyecto", cn["nombre_proyecto"])
    cn["presupuesto"] = c2.text_input("Rango de presupuesto", cn["presupuesto"])

    cn["objetivos"] = st.text_area("Objetivos de negocio", cn["objetivos"])
    cn["problema"] = st.text_area("Problema a resolver", cn["problema"])
    cn["solucion_esperada"] = st.text_area("Solución esperada", cn["solucion_esperada"])
    cn["target"] = st.text_area("TARGET (usuarios/roles)", cn["target"])
    cn["funcionalidades"] = st.text_area("Funcionalidades esperadas", cn["funcionalidades"])
    cn["expectativas"] = st.text_area("Expectativas", cn["expectativas"])
    cn["experiencia_previa"] = st.text_area("Experiencia previa", cn["experiencia_previa"])
    cn["adjudicacion"] = st.text_area("Forma de adjudicación", cn["adjudicacion"])
    cn["criterios_eval"] = st.text_area("Criterios de evaluación", cn["criterios_eval"])
    cn["fecha_lanzamiento"] = st.text_input("Fecha de lanzamiento", cn["fecha_lanzamiento"])
    cn["notas"] = st.text_area("Notas generales", cn["notas"])

    st.subheader("Propuesta IA (opcional)")
    cn["propuesta_ia"] = st.text_area("Resumen / propuesta generada por IA", cn["propuesta_ia"], height=140)

    listo = st.checkbox("Marcar como **Listo para PDF**", value=st.session_state.get("listo_pdf", False))
    guardado = st.form_submit_button("💾 Guardar caso")

if listo:
    st.session_state["listo_pdf"] = True
else:
    st.session_state["listo_pdf"] = False

st.divider()
st.subheader("🧾 Generar PDF")

if not st.session_state.get("listo_pdf", False):
    st.info("Activa **'Listo para PDF'** para habilitar la descarga.")
    st.stop()

# --------------------- PDF helpers ---------------------
ROOT = Path(__file__).resolve().parents[1]
FONT_PATH = ROOT / "DejaVuSans.ttf"
LOGO_PATH = ROOT / "logo_babel.jpeg"

def add_unicode_font(pdf: FPDF):
    try:
        if FONT_PATH.exists():
            pdf.add_font("DejaVu", "", str(FONT_PATH), uni=True)
            pdf.set_font("DejaVu", "", 12)
            return True
    except Exception:
        pass
    pdf.set_font("Arial", "", 12)
    return False

def header(pdf: FPDF):
    if LOGO_PATH.exists():
        pdf.image(str(LOGO_PATH), x=10, y=10, w=30)
    pdf.set_xy(10, 10)
    pdf.set_font_size(16)
    pdf.cell(0, 10, "Caso de Negocio - Babel", ln=1, align="R")
    pdf.ln(8)

def section(pdf: FPDF, titulo: str, texto: str):
    pdf.set_font_size(13); pdf.set_text_color(20,20,20)
    pdf.cell(0, 8, titulo, ln=1)
    pdf.set_font_size(11); pdf.set_text_color(0,0,0)
    pdf.multi_cell(w=0, h=6, txt=(texto or "").replace("\t","    ").replace("\r",""), align="J")
    pdf.ln(2)

def build_pdf() -> bytes:
    pdf = FPDF(format="Letter", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    add_unicode_font(pdf)
    header(pdf)

    pdf.set_font_size(12)
    pdf.multi_cell(0, 6,
        f"Empresa: {lead.get('empresa','')}\n"
        f"Contacto: {lead.get('contacto','')}  |  Email: {lead.get('email','')}  |  Tel: {lead.get('telefono','')}")
    pdf.ln(2)
    pdf.multi_cell(0, 6, f"Descripción breve: {lead.get('descripcion','')}")
    pdf.ln(4)
    pdf.cell(0, 6, f"Score (Calificación): {int(st.session_state.get('score',0))}%", ln=1)
    pdf.ln(2)

    section(pdf, "Nombre de proyecto", cn["nombre_proyecto"])
    section(pdf, "Presupuesto", cn["presupuesto"])
    section(pdf, "Objetivos de negocio", cn["objetivos"])
    section(pdf, "Problema a resolver", cn["problema"])
    section(pdf, "Solución esperada", cn["solucion_esperada"])
    section(pdf, "TARGET (usuarios/roles)", cn["target"])
    section(pdf, "Funcionalidades esperadas", cn["funcionalidades"])
    section(pdf, "Expectativas", cn["expectativas"])
    section(pdf, "Experiencia previa", cn["experiencia_previa"])
    section(pdf, "Forma de adjudicación", cn["adjudicacion"])
    section(pdf, "Criterios de evaluación", cn["criterios_eval"])
    section(pdf, "Fecha de lanzamiento", cn["fecha_lanzamiento"])
    section(pdf, "Notas generales", cn["notas"])
    if cn.get("propuesta_ia"):
        section(pdf, "Propuesta IA", cn["propuesta_ia"])

    return bytes(pdf.output(dest="S").encode("latin1", "replace"))

if st.button("⬇️ Generar y descargar PDF"):
    try:
        pdf_bytes = build_pdf()
        st.download_button(
            "Descargar 'caso_negocio_babel.pdf'",
            data=pdf_bytes,
            file_name="caso_negocio_babel.pdf",
            mime="application/pdf",
        )
        st.success("PDF generado.")
    except Exception as e:
        st.error(f"Error al generar el PDF: {e}")
