import os
import json
import unicodedata
import streamlit as st
from fpdf import FPDF
from openai import OpenAI

# =========================
# API KEY (Streamlit Secrets o variable de entorno)
# =========================
api_key = st.secrets.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
if not api_key:
    st.error("Falta OPENAI_API_KEY (Settings → Secrets en Streamlit Cloud).")
    st.stop()
client = OpenAI(api_key=api_key)

# =========================
# Helpers de texto (UTF-8, sin latin-1)
# =========================
def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    # normaliza saltos y comillas/guiones “curvos”
    text = text.replace("\r", " ").replace("\n", " ")
    text = (text
            .replace("–", "-").replace("—", "-").replace("•", "-")
            .replace("“", '"').replace("”", '"').replace("’", "'"))
    # mantener acentos en UTF-8
    return unicodedata.normalize("NFKC", text)

def split_tokens_long(text: str, max_len: int = 40) -> str:
    """Trocea tokens largos (URLs/tokens sin espacios) para que quepan."""
    parts = []
    for tok in text.split(" "):
        if len(tok) > max_len:
            parts += [tok[i:i+max_len] for i in range(0, len(tok), max_len)]
        else:
            parts.append(tok)
    return " ".join(parts)

def make_lines_utf8(text: str, max_len: int = 40) -> list[str]:
    """Parte el texto en líneas <= max_len (por carácter, aproximado)."""
    text = split_tokens_long(normalize_text(text), max_len)
    words = text.split(" ")
    lines, cur, n = [], [], 0
    for w in words:
        need = len(w) + (1 if n > 0 else 0)
        if n + need > max_len:
            if cur:
                lines.append(" ".join(cur))
            cur, n = [w], len(w)
        else:
            cur.append(w); n += need
    if cur:
        lines.append(" ".join(cur))
    return lines

def write_lines(pdf: FPDF, text: str, lh: int = 8):
    """Escribe usando cell() línea por línea (sin multi_cell)."""
    for line in make_lines_utf8(text, max_len=40):
        pdf.cell(0, lh, line, ln=1)

# =========================
# Estructura del caso + scoring
# =========================
SECTIONS = [
    "Nombre del proyecto",
    "Objetivos de negocio",
    "Problema a resolver",
    "Solución esperada",
    "Usuario objetivo (target)",
    "Funcionalidades deseadas",
    "Expectativas",
    "Experiencia previa",
    "Forma de adjudicación",
    "Criterios de evaluación",
    "Fecha de lanzamiento estimada",
    "Presupuesto",
    "Notas generales",
]

PREGUNTAS = [
    "¿Tiene fecha planeada para iniciar proyecto?",
    "¿Cuenta con presupuesto?",
    "¿Es un proyecto para incrementar ventas o marketing?",
    "¿El proyecto resuelve un problema de prioridad 1, 2 o 3 dentro de tu empresa?",
    "¿Quién toma la decisión? ¿Hablamos con tomador de decisión?",
]
PESOS = [20, 30, 30, 5, 5]   # suma 100

SYSTEM_PROMPT = (
    "Eres un asistente comercial que levanta un caso de negocio mediante conversación. "
    "Haz preguntas naturales hasta cubrir todas las secciones requeridas."
)

# =========================
# UI
# =========================
st.image("logo_babel.jpeg", width=200)
st.title("Agente de Requerimientos - Babel")
st.caption("Chat con IA + PDF (con acentos) + Calificación automática (5 preguntas: 20/30/30/5/5)")

# =========================
# Estado del chat
# =========================
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": "Hola, estoy aquí para ayudarte a construir tu caso de negocio. ¿Cómo se llama tu proyecto y de qué trata?"}
    ]

for msg in st.session_state.messages[1:]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Escribe tu respuesta aquí..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        try:
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=st.session_state.messages,
                temperature=0.7,
                timeout=60
            )
            reply = resp.choices[0].message.content
            st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
        except Exception as e:
            st.error(f"Ocurrió un error al llamar a la API: {e}")

st.divider()
st.subheader("🧮 Calificación automática (≥ 70% = válida)")

# =========================
# Funciones IA (resumen y calificación)
# =========================
def extract_structured_summary(messages):
    try:
        sys = {"role": "system", "content": "Devuelve SOLO JSON con las claves exactas del caso de negocio."}
        user = {
            "role": "user",
            "content": (
                "Usa esta conversación para rellenar las siguientes claves. "
                "Devuelve SOLO JSON válido (sin texto extra). Claves: "
                + ", ".join(SECTIONS)
                + ". Conversación (role:content):\n"
                + "\n".join([f"{m['role']}:{m['content']}" for m in messages if m['role'] in ["user","assistant"]])
            )
        }
        comp = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[sys, user],
            temperature=0.0,
            timeout=60
        )
        data = json.loads(comp.choices[0].message.content)
        for k in SECTIONS:
            data.setdefault(k, "")
        return data
    except Exception as e:
        st.warning(f"No se pudo generar el resumen estructurado automáticamente. Detalle: {e}")
        return {k: "" for k in SECTIONS}

def infer_answers_fixed(messages):
    prompt = (
        "Con base en la conversación siguiente, responde con 'Sí' o 'No' "
        "a cada una de estas preguntas EXACTAS. Devuelve SOLO JSON válido, "
        "con las claves siendo las preguntas tal cual.\n\n"
        "CONVERSACIÓN:\n" +
        "\n".join([f"{m['role']}: {m['content']}" for m in messages if m['role'] in ["user","assistant"]]) +
        "\n\nPREGUNTAS:\n" +
        "\n".join([f"- {q}" for q in PREGUNTAS])
    )
    comp = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "Eres un asistente que devuelve SOLO JSON válido con 'Sí' o 'No'."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0,
        timeout=60
    )
    respuestas = json.loads(comp.choices[0].message.content)
    norm = {}
    for q in PREGUNTAS:
        v = (respuestas.get(q, "No") or "No").strip().lower()
        norm[q] = "Sí" if v in ["si", "sí", "yes", "true"] else "No"
    return norm

def score_fixed(respuestas):
    puntos = 0
    detalle = []
    for q, w in zip(PREGUNTAS, PESOS):
        got = respuestas.get(q, "No")
        pts = w if got == "Sí" else 0
        puntos += pts
        detalle.append((q, got, w, pts))
    porcentaje = puntos
    clasificacion = "VALIDA" if porcentaje >= 70 else "NO CALIFICADA"
    return puntos, porcentaje, clasificacion, detalle

try:
    respuestas = infer_answers_fixed(st.session_state.messages)
    puntos, porcentaje, clasificacion, detalle = score_fixed(respuestas)
    c1, c2, c3 = st.columns(3)
    c1.metric("Puntaje", f"{puntos} / 100")
    c2.metric("Porcentaje", f"{porcentaje:.2f}%")
    c3.metric("Clasificación", clasificacion)
    st.write("**Detalle de respuestas:**")
    for q, got, w, pts in detalle:
        st.write(f"- {q} -> **{got}** (peso {w}%, pts {pts})")
except Exception:
    st.info("Responde algunas preguntas para poder calcular la calificación.")

# =========================
# PDF (con fuente Unicode, sin multi_cell)
# =========================
def build_pdf(data_dict, messages, puntos, porcentaje, clasificacion, detalle):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # 👉 Fuente Unicode (sube DejaVuSans.ttf al repo)
    # Usamos la misma TTF para todo (sin estilo B para evitar depender de DejaVuSans-Bold.ttf)
    pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
    pdf.set_font("DejaVu", "", 12)

    # Cabecera
    try:
        pdf.image("logo_babel.jpeg", x=10, y=8, w=40)
    except Exception:
        pass
    pdf.ln(30)
    write_lines(pdf, "Caso de Negocio - Generado por Agente Babel")

    # Secciones
    pdf.set_font("DejaVu", "", 13)
    for section in SECTIONS:
        write_lines(pdf, section)
        pdf.set_font("DejaVu", "", 12)
        content = data_dict.get(section, "") or "-"
        write_lines(pdf, content)
        pdf.ln(2)
        pdf.set_font("DejaVu", "", 13)

    # Calificación
    pdf.ln(4)
    pdf.set_font("DejaVu", "", 13)
    write_lines(pdf, "Calificación de la Oportunidad (5 preguntas)")
    pdf.set_font("DejaVu", "", 12)
    write_lines(pdf, f"Puntaje: {puntos} / 100")
    write_lines(pdf, f"Porcentaje: {porcentaje:.2f}%")
    write_lines(pdf, f"Clasificación: {clasificacion}")
    for q, got, w, pts in detalle:
        write_lines(pdf, f"- {q} -> {got} (peso {w}%, pts {pts})")

    # Conversación (anexo)
    pdf.ln(4)
    pdf.set_font("DejaVu", "", 13)
    write_lines(pdf, "Anexo: Conversación")
    pdf.set_font("DejaVu", "", 12)
    for msg in messages:
        if msg["role"] in ["user", "assistant"]:
            role = "Cliente" if msg["role"] == "user" else "Asistente"
            content = msg.get("content", "")
            write_lines(pdf, f"{role}: {content}")

    return pdf

# Botón para generar PDF
if st.button("📄 Generar PDF"):
    data = extract_structured_summary(st.session_state.messages)
    try:
        respuestas = infer_answers_fixed(st.session_state.messages)
        puntos, porcentaje, clasificacion, detalle = score_fixed(respuestas)
    except Exception:
        puntos, porcentaje, clasificacion, detalle = 0, 0, "NO CALIFICADA", []
    pdf = build_pdf(data, st.session_state.messages, puntos, porcentaje, clasificacion, detalle)
    output_file = "caso_negocio_babel.pdf"
    pdf.output(output_file)
    with open(output_file, "rb") as f:
        st.download_button("⬇️ Descargar PDF", f, file_name=output_file)
