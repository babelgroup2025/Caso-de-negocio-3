# app.py — Agente comercial Babel con RAG multi-empresa + PDF + Scoring

import os
import re
import json
import unicodedata
import numpy as np
import requests
import streamlit as st
from bs4 import BeautifulSoup
from fpdf import FPDF
from openai import OpenAI

# ===================== Config OpenAI =====================
api_key = st.secrets.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
if not api_key:
    st.error("Falta OPENAI_API_KEY (Settings → Secrets en Streamlit Cloud).")
    st.stop()
client = OpenAI(api_key=api_key)

# ===================== Texto helpers (UTF-8) =====================
def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    text = text.replace("\r", " ").replace("\n", " ")
    text = (text
            .replace("–", "-").replace("—", "-").replace("•", "-")
            .replace("“", '"').replace("”", '"').replace("’", "'"))
    return unicodedata.normalize("NFKC", text)

def split_tokens_long(text: str, max_len: int = 42) -> str:
    parts = []
    for tok in text.split(" "):
        if len(tok) > max_len:
            parts += [tok[i:i+max_len] for i in range(0, len(tok), max_len)]
        else:
            parts.append(tok)
    return " ".join(parts)

def make_lines_utf8(text: str, max_len: int = 42) -> list[str]:
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
    for line in make_lines_utf8(text, max_len=42):
        pdf.cell(0, lh, line, ln=1)

# ===================== Caso de negocio + Scoring =====================
SECTIONS = [
    "Nombre del proyecto","Objetivos de negocio","Problema a resolver","Solución esperada",
    "Usuario objetivo (target)","Funcionalidades deseadas","Expectativas","Experiencia previa",
    "Forma de adjudicación","Criterios de evaluación","Fecha de lanzamiento estimada",
    "Presupuesto","Notas generales",
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

# ===================== RAG multi-empresa (Babel + competidores) =====================
EMBED_MODEL = "text-embedding-3-small"
CHUNK_SIZE = 900
CHUNK_OVERLAP = 150
TOP_K_PER_SOURCE = 3

def ensure_kb():
    if "kb_chunks" not in st.session_state:
        st.session_state.kb_chunks = []     # [str]
        st.session_state.kb_sources = []    # [empresa]
        st.session_state.kb_urls = []       # [url]
        st.session_state.kb_vecs = None     # np.array (N,D)

def fetch_url_text(url: str) -> str:
    r = requests.get(url, timeout=25, headers={"User-Agent":"Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script","style","noscript","header","footer","nav","aside"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text

def chunk_text(text: str, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks, i = [], 0
    while i < len(text):
        chunks.append(text[i:i+size])
        i += max(1, size - overlap)
    return chunks

def embed_texts(texts):
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    vecs = [np.array(e.embedding, dtype=np.float32) for e in resp.data]
    return np.vstack(vecs)

def add_page(company: str, url: str):
    ensure_kb()
    raw = fetch_url_text(url)
    chunks = chunk_text(raw)
    vecs = embed_texts(chunks)
    if st.session_state.kb_vecs is None:
        st.session_state.kb_vecs = vecs
    else:
        st.session_state.kb_vecs = np.vstack([st.session_state.kb_vecs, vecs])
    st.session_state.kb_chunks.extend(chunks)
    st.session_state.kb_sources.extend([company]*len(chunks))
    st.session_state.kb_urls.extend([url]*len(chunks))

def list_companies_in_kb():
    ensure_kb()
    return sorted(set(st.session_state.kb_sources))

def retrieve_grouped(query: str, top_k_per_source: int = TOP_K_PER_SOURCE):
    ensure_kb()
    if st.session_state.kb_vecs is None or len(st.session_state.kb_chunks) == 0:
        return {}
    qv = embed_texts([query])[0]
    A = st.session_state.kb_vecs
    sims = A @ qv / (np.linalg.norm(A, axis=1) * (np.linalg.norm(qv) + 1e-9) + 1e-9)
    grouped = {}
    for idx, sim in enumerate(sims):
        company = st.session_state.kb_sources[idx]
        grouped.setdefault(company, []).append((sim, idx))
    out = {}
    for company, arr in grouped.items():
        arr.sort(key=lambda x: -x[0])
        top = arr[:top_k_per_source]
        out[company] = [st.session_state.kb_chunks[i] for (_, i) in top]
    return out

def make_comparison_instruction(grouped_ctx: dict, prefer_companies: list[str] | None = None):
    if not grouped_ctx:
        return "NO HAY CONTEXTO INDEXADO."
    lines = ["=== CONTEXTO COMPARATIVO POR EMPRESA ==="]
    for company in sorted(grouped_ctx.keys()):
        if prefer_companies and company not in prefer_companies:
            continue
        lines.append(f"\n## {company}\n")
        for chunk in grouped_ctx[company]:
            lines.append(f"- {chunk}")
    lines.append("\n=== FIN DEL CONTEXTO ===")
    return "\n".join(lines)

def make_comparison_prompt(user_query: str, companies: list[str]):
    comp_list = ", ".join(companies)
    return (
        "Eres un analista que responde PRIORITARIAMENTE usando el contexto provisto.\n"
        "Objetivo: comparar empresas y su propuesta en relación con la consulta del usuario.\n\n"
        f"Empresas a comparar: {comp_list}\n"
        "Formato de salida requerido:\n"
        "1) Resumen ejecutivo (3–5 bullets)\n"
        "2) Babel: ¿qué hace? ¿cuál es su solución/propuesta relevante?\n"
        "3) Competidores (uno por uno): ¿qué hacen? ¿cuál es su solución/propuesta?\n"
        "4) Diferenciales claros de Babel vs cada competidor (bullets)\n"
        "5) Riesgos/consideraciones\n"
        "6) Recomendación (clara y accionable)\n\n"
        f"Consulta del usuario: {user_query}\n"
        "Si el contexto no incluye información para una empresa, indícalo explícitamente."
    )

# ===================== UI principal =====================
st.image("logo_babel.jpeg", width=200)
st.title("Agente de Requerimientos - Babel")
st.caption("Chat con IA + RAG multi-empresa (Babel y competidores) + Calificación + PDF con acentos")

# ---- Indexación de páginas
st.subheader("📚 Indexar páginas de Babel y competidores")
with st.form("form_index"):
    company = st.text_input("Empresa (ej. Babel, Accenture, Deloitte, etc.)").strip()
    url_in = st.text_input("URL a indexar (página de servicios/soluciones, etc.)").strip()
    submitted = st.form_submit_button("Indexar URL")
    if submitted:
        try:
            if not company or not url_in:
                st.warning("Indica empresa y URL.")
            else:
                add_page(company, url_in)
                st.success(f"Indexado OK: {company} → {url_in}")
                st.caption(f"Chunks almacenados: {len(st.session_state.kb_chunks)} | Empresas: {', '.join(list_companies_in_kb())}")
        except Exception as e:
            st.error(f"No pude indexar: {e}")

if list_companies_in_kb():
    st.info("Empresas indexadas: " + ", ".join(list_companies_in_kb()))

# ---- Estado del chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": "Hola, estoy aquí para ayudarte a construir tu caso de negocio. ¿Cómo se llama tu proyecto y de qué trata?"}
    ]

for msg in st.session_state.messages[1:]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---- Entrada chat con RAG comparativo auto
if prompt := st.chat_input("Escribe tu mensaje o una consulta comparativa..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # RAG por empresa
    grouped_ctx = retrieve_grouped(prompt, top_k_per_source=TOP_K_PER_SOURCE)
    context_text = make_comparison_instruction(grouped_ctx)
    aug_system = {
        "role": "system",
        "content": (
            "Usa el CONTEXTO COMPARATIVO POR EMPRESA para fundamentar tu respuesta. "
            "Si falta información para alguna empresa, dilo. Evita inventar datos.\n\n"
            + context_text
        ),
    }
    rag_messages = [st.session_state.messages[0], aug_system] + st.session_state.messages[1:]

    with st.chat_message("assistant"):
        try:
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=rag_messages,
                temperature=0.5,
                timeout=60
            )
            reply = resp.choices[0].message.content
            st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
        except Exception as e:
            st.error(f"Ocurrió un error al llamar a la API: {e}")

st.divider()

# ---- Comparación dirigida
st.subheader("🔍 Comparación dirigida")
empresas_disp = list_companies_in_kb()
if empresas_disp:
    sel = st.multiselect("Selecciona empresas a comparar", options=empresas_disp, default=min(2, len(empresas_disp)) and empresas_disp[:2])
    user_query_comp = st.text_input("Consulta para la comparación (ej. agentes de IA para ventas)")
    if st.button("Generar comparación"):
        grouped_ctx = retrieve_grouped(user_query_comp or "comparar empresas", top_k_per_source=TOP_K_PER_SOURCE)
        context_text = make_comparison_instruction(grouped_ctx, prefer_companies=sel)
        comp_prompt = make_comparison_prompt(user_query_comp or "comparar empresas", sel)
        try:
            comp_resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": context_text},
                          {"role": "user", "content": comp_prompt}],
                temperature=0.4,
                timeout=60
            )
            comp_reply = comp_resp.choices[0].message.content
            st.markdown(comp_reply)
            st.session_state.messages.append({"role": "assistant", "content": comp_reply})
        except Exception as e:
            st.error(f"Error generando comparación: {e}")
else:
    st.caption("Primero indexa al menos una URL por empresa para habilitar la comparación.")

st.divider()
st.subheader("🧮 Calificación automática (≥ 70% = válida)")

# ===================== IA: resumen estructurado + scoring =====================
def extract_structured_summary(messages):
    try:
        sys = {"role": "system", "content": "Devuelve SOLO JSON con las claves exactas del caso de negocio."}
        user = {"role": "user", "content":
            "Usa esta conversación para rellenar las siguientes claves. Devuelve SOLO JSON válido (sin texto extra). "
            f"Claves: {', '.join(SECTIONS)}. Conversación (role:content):\n" +
            "\n".join([f"{m['role']}:{m['content']}" for m in messages if m['role'] in ['user','assistant']])
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
        "a cada una de estas preguntas EXACTAS. Devuelve SOLO JSON válido.\n\n"
        "CONVERSACIÓN:\n" +
        "\n".join([f"{m['role']}: {m['content']}" for m in messages if m['role'] in ['user','assistant']]) +
        "\n\nPREGUNTAS:\n" + "\n".join([f"- {q}" for q in PREGUNTAS])
    )
    comp = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "Devuelve SOLO JSON válido con 'Sí' o 'No'."},
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

def score_fixed(resps):
    puntos = 0
    detalle = []
    for q, w in zip(PREGUNTAS, PESOS):
        got = resps.get(q, "No")
        pts = w if got == "Sí" else 0
        puntos += pts
        detalle.append((q, got, w, pts))
    porcentaje = puntos
    clasificacion = "VALIDA" if porcentaje >= 70 else "NO CALIFICADA"
    return puntos, porcentaje, clasificacion, detalle

# Mostrar scoring
try:
    respuestas = infer_answers_fixed(st.session_state.messages)
    puntos, porcentaje, clasificacion, detalle = score_fixed(respuestas)
    c1, c2, c3 = st.columns(3)
    c1.metric("Puntaje", f"{puntos} / 100")
    c2.metric("Porcentaje", f"{porcentaje:.2f}%")
    c3.metric("Clasificación", clasificacion)
    st.write("**Detalle:**")
    for q, got, w, pts in detalle:
        st.write(f"- {q} → **{got}** (peso {w}%, pts {pts})")
except Exception:
    st.info("Responde algunas preguntas para poder calcular la calificación.")

# ===================== PDF (Unicode, sin multi_cell) =====================
def build_pdf(data_dict, messages, puntos, porcentaje, clasificacion, detalle):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Fuente Unicode (asegúrate de tener DejaVuSans.ttf en la raíz del repo)
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
        write_lines(pdf, f"- {q} → {got} (peso {w}%, pts {pts})")

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

# ---- Botón PDF
st.divider()
if st.button("📄 Generar PDF"):
    data = extract_structured_summary(st.session_state.messages)
    try:
        respuestas = infer_answers_fixed(st.session_state.messages)
        puntos, porcentaje, clasificacion, detalle = score_fixed(respuestas)
    except Exception:
        puntos, porcentaje, clasificacion, detalle = 0, 0, "NO CALIFICADA", []
    pdf = build_pdf(data, st.session_state.messages, puntos, porcentaje, clasificacion, detalle)
    fname = "caso_negocio_babel.pdf"
    pdf.output(fname)
    with open(fname, "rb") as f:
        st.download_button("⬇️ Descargar PDF", f, file_name=fname, mime="application/pdf")
