
import os
import json
import unicodedata
import streamlit as st
from fpdf import FPDF
from openai import OpenAI

# --- API Key: Streamlit Cloud uses st.secrets; fallback to env for others ---
api_key = st.secrets.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
if not api_key:
    st.error("Falta OPENAI_API_KEY en secrets (Streamlit Cloud) o Environment (Railway).")
    st.stop()
client = OpenAI(api_key=api_key)

# --- UI ---
st.image("logo_babel.jpeg", width=200)
st.title("Agente de Requerimientos - Babel")
st.caption("Chat con IA + PDF estructurado + Calificación automática (5 preguntas: 20/30/30/5/5).")

def sanitize_for_pdf(s: str) -> str:
    if not isinstance(s, str):
        s = str(s)
    s = s.replace("–", "-").replace("—", "-").replace("•", "-")
    s = s.replace("“", '"').replace("”", '"').replace("’", "'")
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("latin-1", "ignore").decode("latin-1")
    return s

SECTIONS = [
    "Nombre del proyecto","Objetivos de negocio","Problema a resolver","Solución esperada",
    "Usuario objetivo (target)","Funcionalidades deseadas","Expectativas","Experiencia previa",
    "Forma de adjudicación","Criterios de evaluación","Fecha de lanzamiento estimada",
    "Presupuesto","Notas generales"
]

PREGUNTAS = [
    "¿Tiene fecha planeada para iniciar proyecto?",
    "¿Cuenta con presupuesto?",
    "¿Es un proyecto para incrementar ventas o marketing?",
    "¿El proyecto resuelve un problema de prioridad 1, 2 o 3 dentro de tu empresa?",
    "¿Quién toma la decisión? ¿Hablamos con tomador de decisión?"
]
PESOS = [20, 30, 30, 5, 5]

SYSTEM_PROMPT = (
    "Eres un asistente comercial que levanta un caso de negocio mediante conversación. "
    "Haz preguntas naturales hasta cubrir todas las secciones requeridas."
)

# Estado del chat
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
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=st.session_state.messages,
                temperature=0.7,
                timeout=60  # evita timeouts largos
            )
            reply = response.choices[0].message.content
            st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
        except Exception as e:
            st.error(f"Ocurrió un error al llamar a la API: {e}")

st.divider()
st.subheader("🧮 Calificación automática (≥ 70% = válida)")

def extract_structured_summary(messages):
    try:
        sys = {"role": "system", "content": "Devuelve SOLO JSON con las claves exactas de las secciones del caso de negocio."}
        user = {"role": "user", "content":
            "Usa esta conversación para rellenar las siguientes claves. Devuelve SOLO JSON válido, sin texto adicional. "
            + ", ".join(SECTIONS)
            + ". Conversación (role:content):\n"
            + "\n".join([f"{m['role']}:{m['content']}" for m in messages if m['role'] in ['user','assistant']])
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
        "Con base en la conversación siguiente, responde con 'Sí' o 'No' a cada una de estas preguntas EXACTAS. "
        "Devuelve SOLO JSON válido con las claves siendo las preguntas tal cual.\n\n"
        "CONVERSACIÓN:\n" +
        "\n".join([f"{m['role']}: {m['content']}" for m in messages if m['role'] in ['user','assistant']]) +
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
        norm[q] = "Sí" if v in ["si","sí","yes","true"] else "No"
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
    clasificacion = "VÁLIDA" if porcentaje >= 70 else "NO CALIFICADA"
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
        st.write(f"- {q} → **{got}** (peso {w}%, pts {pts})")
except Exception:
    st.info("Responde algunas preguntas para poder calcular la calificación.")

def build_pdf(data_dict, messages, puntos, porcentaje, clasificacion, detalle):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    try:
        pdf.image("logo_babel.jpeg", x=10, y=8, w=40)
    except Exception:
        pass
    pdf.ln(30)
    pdf.multi_cell(0, 10, sanitize_for_pdf("Caso de Negocio - Generado por Agente Babel\n\n"), align="L")

    pdf.set_font("Arial", "B", 12)
    for section in SECTIONS:
        pdf.multi_cell(0, 8, sanitize_for_pdf(section))
        pdf.set_font("Arial", "", 12)
        content = sanitize_for_pdf(data_dict.get(section, "")) or "-"
        pdf.multi_cell(0, 8, content)
        pdf.ln(2)
        pdf.set_font("Arial", "B", 12)

    pdf.ln(4)
    pdf.set_font("Arial", "B", 12)
    pdf.multi_cell(0, 8, sanitize_for_pdf("Calificación de la Oportunidad (5 preguntas)"))
    pdf.set_font("Arial", "", 12)
    resumen = f"Puntaje: {puntos} / 100\nPorcentaje: {porcentaje:.2f}%\nClasificación: {clasificacion}\n"
    pdf.multi_cell(0, 8, sanitize_for_pdf(resumen))
    for q, got, w, pts in detalle:
        line = f"- {q} → {got} (peso {w}%, pts {pts})"
        pdf.multi_cell(0, 8, sanitize_for_pdf(line))

    pdf.ln(4)
    pdf.set_font("Arial", "B", 12)
    pdf.multi_cell(0, 8, sanitize_for_pdf("Anexo: Conversación"))
    pdf.set_font("Arial", "", 12)
    for msg in messages:
        if msg["role"] in ["user", "assistant"]:
            role = "Cliente" if msg["role"] == "user" else "Asistente"
            content = sanitize_for_pdf(msg["content"])
            pdf.multi_cell(0, 8, f"{role}: {content}")
    return pdf

if st.button("📄 Generar PDF"):
    data = extract_structured_summary(st.session_state.messages)
    try:
        respuestas = infer_answers_fixed(st.session_state.messages)
        puntos, porcentaje, clasificacion, detalle = score_fixed(respuestas)
    except Exception:
        puntos, porcentaje, clasificacion, detalle = 0, 0, "NO CALIFICADA ⚠️", []
    pdf = build_pdf(data, st.session_state.messages, puntos, porcentaje, clasificacion, detalle)
    output_file = "caso_negocio_babel.pdf"
    pdf.output(output_file)
    with open(output_file, "rb") as f:
        st.download_button("⬇️ Descargar PDF", f, file_name=output_file)
