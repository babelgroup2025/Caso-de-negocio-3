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
# Utilidades para PDF (sanitizar + cortar palabras largas)
# =========================
def soft_wrap(text: str, max_len: int = 40) -> str:
    """
    Corta cualquier 'palabra' sin espacios que exceda max_len (ej. URLs/tokens).
    Inserta saltos de línea para que FPDF pueda renderizar.
    """
    if not isinstance(text, str):
        text = str(text)
    out = []
    for tok in text.split(" "):
        if len(tok) > max_len:
            chunks = [tok[i:i + max_len] for i in range(0, len(tok), max_len)]
            out.append("\n".join(chunks))
        else:
            out.append(tok)
    return " ".join(out)

def clean_for_pdf(text: str) -> str:
    """
    Normaliza (quita comillas curvas, guiones largos), aplica soft-wrap y
    convierte a latin-1 con reemplazo para evitar errores de FPDF.
    """
    if not isinstance(text, str):
        text = str(text)
    text = (text
            .replace("–", "-").replace("—", "-").replace("•", "-")
            .replace("“", '"').replace("”", '"').replace("’", "'"))
    text = unicodedata.normalize("NFKD", text)
    text = soft_wrap(text, max_len=40)
    return text.encode("latin-1", "replace").decode("latin-1")

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
st.caption("Chat con IA + PDF + Calificación automática (5 preguntas: 20/30/30/5/5)")

# =========================
# Estado del chat
# =========================
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": "Hola, estoy aquí para ayudarte a construir tu caso de negocio. ¿Cómo se llama tu proyecto y de qué trata?"}
    ]

# Render del historial (omitimos el system)
for msg in st.session_state.messages[1:]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Entrada del usuario
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
    """Devuelve dict con todas las SECTIONS completadas (o vacío) usando JSON forzado."""
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
    """Pide a GPT Sí/No para las 5 preguntas (JSON forzado)."""
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
    # Normalización
    norm = {}
    for q in PREGUNTAS:
        v = (respuestas.get(q, "No") or "No").strip().lower()
        norm[q] = "Sí" if v in ["si", "sí", "yes", "true"] else "No"
    return norm

def score_fixed(respuestas):
    """Calcula puntaje/porcentaje/clasificación con pesos 20/30/30/5/5."""
    puntos = 0
    detalle = []
    for q, w in zip(PREGUNTAS, PESOS):
        got = respuestas.get(q, "No")
        pts = w if got == "Sí" else 0
        puntos += pts
        detalle.append((q, got, w, pts))
    porcentaje = puntos  # ya es %
    clasificacion = "VALIDA" if porcentaje >= 70 else "NO CALIFICADA"  # sin emojis para PDF
    return puntos, porcentaje, clasificacion, detalle

# Ejecutar calificación en pantalla
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
# PDF
# =========================
def build_pdf(data_dict, messages, puntos, porcentaje, clasificacion, detalle):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)  # evita desbordes
    pdf.add_page()

    # Cabecera
    try:
        pdf.image("logo_babel.jpeg", x=10, y=8, w=40)
    except Exception:
        pass
    pdf.set_font("Arial", size=12)
    pdf.ln(30)
    pdf.multi_cell(0, 10, clean_for_pdf("Caso de Negocio - Generado por Agente Babel\n"), align="L")

    # Secciones
    pdf.set_font("Arial", "B", 12)
    for section in SECTIONS:
        pdf.multi_cell(0, 8, clean_for_pdf(section))
        pdf.set_font("Arial", "", 12)
        content = data_dict.get(section, "") or "-"
        pdf.multi_cell(0, 8, clean_for_pdf(content))
        pdf.ln(2)
        pdf.set_font("Arial", "B", 12)

    # Calificación
    pdf.ln(4)
    pdf.set_font("Arial", "B", 12)
    pdf.multi_cell(0, 8, clean_for_pdf("Calificacion de la Oportunidad (5 preguntas)"))
    pdf.set_font("Arial", "", 12)
    resumen = f"Puntaje: {puntos} / 100\nPorcentaje: {porcentaje:.2f}%\nClasificacion: {clasificacion}\n"
    pdf.multi_cell(0, 8, clean_for_pdf(resumen))
    for q, got, w, pts in detalle:
        line = f"- {q} -> {got} (peso {w}%, pts {pts})"
        pdf.multi_cell(0, 8, clean_for_pdf(line))

    # Conversación (anexo)
    pdf.ln(4)
    pdf.set_font("Arial", "B", 12)
    pdf.multi_cell(0, 8, clean_for_pdf("Anexo: Conversacion"))
    pdf.set_font("Arial", "", 12)
    for msg in messages:
        if msg["role"] in ["user", "assistant"]:
            role = "Cliente" if msg["role"] == "user" else "Asistente"
            content = msg["content"]
            safe_content = clean_for_pdf(content)   # 👈 importante
            pdf.multi_cell(0, 8, f"{role}: {safe_content}", align="L")

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
