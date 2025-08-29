import streamlit as st
from fpdf import FPDF
from io import BytesIO
import os
import re

st.title("📄 Fase 5: PDF Final")

# -------------------------
# Reglas para habilitar PDF
# -------------------------
score = st.session_state.get("score_total", 0)               # de 1_Evaluacion.py (>=70)
ready_for_pdf = st.session_state.get("ready_for_pdf", False) # de 4_Desarrollo_y_Pruebas.py
propuesta_md = st.session_state.get("propuesta_md")          # (opcional) de tu página de propuesta

st.write(f"**Score (Fase 1):** {score}%")
st.write(f"**Listo para PDF (Fase 4):** {'Sí' if ready_for_pdf else 'No'}")
st.write(f"**Propuesta IA:** {'Incluida' if propuesta_md else '—'}")

if score < 70:
    st.error("❌ La evaluación no alcanzó 70%. Vuelve a la Fase 1.")
if not ready_for_pdf:
    st.warning("⚠️ La Fase 4 aún no marca 'Listo para PDF'.")

disabled_btn = (score < 70) or (not ready_for_pdf)
st.divider()

# -------------------------
# Datos de fases (memoria)
# -------------------------
proyectos = st.session_state.get("proyectos", [])     # de 2_Memoria.py (lista de dicts)
diseno    = st.session_state.get("diseno", {})        # de 3_Diseno.py (dict)
devtest   = st.session_state.get("devtest", {})       # de 4_Desarrollo_y_Pruebas.py (dict)

# -------------------------
# Helpers para PDF
# -------------------------
def safe(text):
    if text is None:
        return ""
    return str(text)

def write_wrapped(pdf: FPDF, text: str, line_height=8, max_chars=90):
    """
    Ajuste rápido de texto (sin cortar palabras).
    """
    text = (text or "").replace("\r", " ").replace("\t", " ")
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            pdf.ln(2)
            continue
        words = paragraph.split(" ")
        line = []
        cur = 0
        for w in words:
            need = len(w) + (1 if cur > 0 else 0)
            if cur + need > max_chars:
                pdf.cell(0, line_height, " ".join(line), ln=1)
                line = [w]
                cur = len(w)
            else:
                line.append(w)
                cur += need
        if line:
            pdf.cell(0, line_height, " ".join(line), ln=1)

def strip_md(md: str) -> str:
    """
    Quita marcado Markdown básico para meterlo limpio en PDF.
    """
    if not md: return ""
    txt = md
    # Encabezados / listas / code fences / inline code / bold-italic
    txt = re.sub(r"^#{1,6}\s*", "", txt, flags=re.MULTILINE)
    txt = re.sub(r"[*_`>~-]{1,3}", "", txt)
    txt = re.sub(r"$begin:math:display$(.*?)$end:math:display$$begin:math:text$.*?$end:math:text$", r"\1", txt)  # enlaces [texto](url) -> texto
    return txt.strip()

def make_pdf_bytes():
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Fuente Unicode (acentos/ñ): requiere DejaVuSans.ttf en la raíz
    try:
        pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        pdf.set_font("DejaVu", "", 12)
    except Exception:
        pdf.set_font("Arial", "", 12)

    # Logo si existe
    if os.path.exists("logo_babel.jpeg"):
        try:
            pdf.image("logo_babel.jpeg", x=10, y=8, w=40)
        except Exception:
            pass

    pdf.ln(28)
    pdf.set_font_size(14)
    write_wrapped(pdf, "Caso de Negocio - Agente Comercial")

    # ---- Resumen de evaluación ----
    pdf.ln(4)
    pdf.set_font_size(13)
    write_wrapped(pdf, "1) Evaluación de Oportunidad")
    pdf.set_font_size(12)
    write_wrapped(pdf, f"- Calificación total: {score}%")
    write_wrapped(pdf, f"- Estatus: {'VALIDA' if score >= 70 else 'NO CALIFICADA'}")

    # ---- Memoria de proyectos ----
    pdf.ln(4)
    pdf.set_font_size(13)
    write_wrapped(pdf, "2) Memoria de proyectos")
    pdf.set_font_size(12)
    if proyectos:
        for i, p in enumerate(proyectos, 1):
            nombre = safe(p.get("nombre", f"Proyecto {i}"))
            desc   = safe(p.get("descripcion", ""))
            res    = safe(p.get("resultado", ""))
            write_wrapped(pdf, f"- {i}. {nombre}")
            if desc: write_wrapped(pdf, f"  • Descripción: {desc}")
            if res:  write_wrapped(pdf, f"  • Resultado: {res}")
    else:
        write_wrapped(pdf, "— Sin proyectos cargados.")

    # ---- Diseño de solución ----
    pdf.ln(4)
    pdf.set_font_size(13)
    write_wrapped(pdf, "3) Diseño de la Solución")
    pdf.set_font_size(12)
    if diseno:
        bloques = [
            ("Objetivos específicos", diseno.get("objetivos")),
            ("Usuarios/roles y casos de uso", diseno.get("usuarios")),
            ("Alcance funcional (MVP / Fase 1)", diseno.get("alcance")),
            ("Integraciones", diseno.get("integraciones")),
            ("Restricciones y supuestos", diseno.get("restricciones")),
            ("Arquitectura/Componentes", diseno.get("arquitectura")),
            ("KPIs de éxito", diseno.get("kpis")),
            ("Riesgos y mitigaciones", diseno.get("riesgos")),
            ("Roadmap / Entregables por hitos", diseno.get("roadmap")),
        ]
        for titulo, contenido in bloques:
            pdf.set_font_size(12)
            write_wrapped(pdf, f"- {titulo}:")
            write_wrapped(pdf, f"  {safe(contenido) or '—'}")
    else:
        write_wrapped(pdf, "— Aún no hay información de diseño (ver Fase 3).")

    # ---- Desarrollo y pruebas ----
    pdf.ln(4)
    pdf.set_font_size(13)
    write_wrapped(pdf, "4) Desarrollo y Pruebas")
    pdf.set_font_size(12)
    if devtest:
        write_wrapped(pdf, f"- Plan de desarrollo: {safe(devtest.get('plan_desarrollo')) or '—'}")
        write_wrapped(pdf, f"- Entorno/stack: {safe(devtest.get('entorno')) or '—'}")
        tareas = devtest.get("tareas", {})
        write_wrapped(pdf, "- Checklist de tareas:")
        for k, v in tareas.items():
            write_wrapped(pdf, f"   • {k}: {'OK' if v else 'Pendiente'}")
        pruebas = devtest.get("pruebas", {})
        write_wrapped(pdf, f"- Pruebas unitarias: {safe(pruebas.get('unitarias')) or '—'}")
        write_wrapped(pdf, f"- Pruebas de integración: {safe(pruebas.get('integracion')) or '—'}")
        write_wrapped(pdf, f"- Criterios de aceptación: {'OK' if pruebas.get('criterios_ok') else 'Pendiente'}")
        write_wrapped(pdf, f"- Resultado: {safe(pruebas.get('resultado')) or '—'}")
        write_wrapped(pdf, f"- Riesgos y mitigaciones: {safe(devtest.get('riesgos')) or '—'}")
        write_wrapped(pdf, f"- Plan de despliegue / rollback: {safe(devtest.get('despliegue')) or '—'}")
    else:
        write_wrapped(pdf, "— Aún no hay información de la Fase 4.")

    # ---- Propuesta generada por IA (si existe) ----
    if propuesta_md:
        pdf.ln(4)
        pdf.set_font_size(13)
        write_wrapped(pdf, "5) Propuesta de solución (IA)")
        pdf.set_font_size(12)
        propuesta_txt = strip_md(propuesta_md)
        for para in propuesta_txt.split("\n"):
            if para.strip():
                write_wrapped(pdf, para.strip())

    # Exportar a bytes (para download_button)
    bio = BytesIO()
    pdf_bytes = pdf.output(dest="S").encode("latin-1")  # fpdf2 retorna str → convertir a bytes
    bio.write(pdf_bytes)
    bio.seek(0)
    return bio

# -------------------------
# Botón de descarga
# -------------------------
if st.button("🖨️ Generar PDF", disabled=disabled_btn):
    pdf_file = make_pdf_bytes()
    st.download_button(
        "⬇️ Descargar Caso de Negocio (PDF)",
        data=pdf_file,
        file_name="Caso_de_Negocio.pdf",
        mime="application/pdf",
    )
