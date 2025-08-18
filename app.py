# app.py — Agente comercial Babel con RAG (Web+PDF) + Propuesta + Scoring + PDF Unicode + Memoria (SQLite)

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
from pypdf import PdfReader

# ===================== Config OpenAI =====================
api_key = st.secrets.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
if not api_key:
    st.error("Falta OPENAI_API_KEY (Settings → Secrets en Streamlit Cloud).")
    st.stop()
client = OpenAI(api_key=api_key)

# ===================== Texto helpers (UTF-8, sin multi_cell) =====================
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

# ===================== RAG multi-empresa (Web + PDF) =====================
EMBED_MODEL = "text-embedding-3-small"
CHUNK_SIZE = 900
CHUNK_OVERLAP = 150
TOP_K_PER_SOURCE = 3

def ensure_kb():
    if "kb_chunks" not in st.session_state:
        st.session_state.kb_chunks = []     # [str]
        st.session_state.kb_sources = []    # [empresa/etiqueta]
        st.session_state.kb_urls = []       # [url o pdf:nombre]
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

# ======== Ingesta de PDF (RAG) ========
def extract_text_from_pdf(uploaded_file) -> str:
    reader = PdfReader(uploaded_file)
    pages = []
    for p in reader.pages:
        txt = p.extract_text() or ""
        pages.append(txt)
    text = " ".join(pages)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def add_pdf_to_kb(company: str, uploaded_file):
    ensure_kb()
    raw = extract_text_from_pdf(uploaded_file)
    chunks = chunk_text(raw)
    vecs = embed_texts(chunks)
    label = company or "Documento"
    if st.session_state.kb_vecs is None:
        st.session_state.kb_vecs = vecs
    else:
        st.session_state.kb_vecs = np.vstack([st.session_state.kb_vecs, vecs])
    st.session_state.kb_chunks.extend(chunks)
    st.session_state.kb_sources.extend([label] * len(chunks))
    st.session_state.kb_urls.extend([f"pdf:{uploaded_file.name}"] * len(chunks))

# ===================== IA: resumen / scoring =====================
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

def score_to_dict(puntos, porcentaje, clasificacion, detalle):
    return {"puntos": puntos, "porcentaje": porcentaje,
            "clasificacion": clasificacion, "detalle": detalle}

# ===================== MEMORIA (SQLite) =====================
import sqlite3
from datetime import datetime

DB_PATH = "memoria.db"

def db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    with db_conn() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT,
            created_at TEXT,
            summary_json TEXT,
            score_json TEXT
        )""")
        con.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            project_id TEXT,
            role TEXT,
            content TEXT
        )""")
        con.execute("""
        CREATE TABLE IF NOT EXISTS kb (
            project_id TEXT,
            company TEXT,
            url TEXT,
            chunk TEXT
        )""")

def save_project(project_id: str, name: str, summary: dict, score: dict,
                 messages: list[dict], kb_chunks: list[str], kb_sources: list[str], kb_urls: list[str]):
    created = datetime.utcnow().isoformat()
    with db_conn() as con:
        con.execute("INSERT OR REPLACE INTO projects (id, name, created_at, summary_json, score_json) VALUES (?,?,?,?,?)",
                    (project_id, name, created, json.dumps(summary, ensure_ascii=False),
                     json.dumps(score, ensure_ascii=False)))
        con.execute("DELETE FROM messages WHERE project_id=?", (project_id,))
        con.execute("DELETE FROM kb WHERE project_id=?", (project_id,))
        con.executemany("INSERT INTO messages (project_id, role, content) VALUES (?,?,?)",
                        [(project_id, m["role"], m.get("content","")) for m in messages if m.get("content")])
        if kb_chunks:
            con.executemany("INSERT INTO kb (project_id, company, url, chunk) VALUES (?,?,?,?)",
                            [(project_id, kb_sources[i], kb_urls[i], kb_chunks[i]) for i in range(len(kb_chunks))])

def list_projects(search: str | None = None):
    with db_conn() as con:
        if search:
            cur = con.execute("SELECT id, name, created_at FROM projects WHERE name LIKE ? ORDER BY created_at DESC", (f"%{search}%",))
        else:
            cur = con.execute("SELECT id, name, created_at FROM projects ORDER BY created_at DESC")
        return cur.fetchall()

def load_project(project_id: str):
    with db_conn() as con:
        proj = con.execute("SELECT id, name, created_at, summary_json, score_json FROM projects WHERE id=?", (project_id,)).fetchone()
        if not proj:
            return None
        summary = json.loads(proj[3]) if proj[3] else {}
        score = json.loads(proj[4]) if proj[4] else {}
        msgs = con.execute("SELECT role, content FROM messages WHERE project_id=?", (project_id,)).fetchall()
        messages = [{"role": r, "content": c} for (r,c) in msgs]
        kb_rows = con.execute("SELECT company, url, chunk FROM kb WHERE project_id=?", (project_id,)).fetchall()
        kb_sources = [r[0] for r in kb_rows]
        kb_urls    = [r[1] for r in kb_rows]
        kb_chunks  = [r[2] for r in kb_rows]
        return {"summary": summary, "score": score, "messages": messages,
                "kb_sources": kb_sources, "kb_urls": kb_urls, "kb_chunks": kb_chunks}

def delete_project(project_id: str):
    with db_conn() as con:
        con.execute("DELETE FROM projects WHERE id=?", (project_id,))
        con.execute("DELETE FROM messages WHERE project_id=?", (project_id,))
        con.execute("DELETE FROM kb WHERE project_id=?", (project_id,))

# ===================== UI principal =====================
st.image("logo_babel.jpeg", width=200)
st.title("Agente de Requerimientos - Babel")
st.caption("Chat con IA + RAG (Web + PDF) + Propuesta + Calificación + PDF con acentos + Memoria")

# ---- Memoria: init + panel
init_db()
st.subheader("🧠 Memoria de proyectos")

col_m1, col_m2 = st.columns([2,1])
with col_m1:
    project_name = st.text_input("Nombre del proyecto a guardar/actualizar", value="")
with col_m2:
    project_id = st.text_input("ID (opcional; si se deja vacío, se usa el nombre)", value="")

def current_score_and_summary():
    data = extract_structured_summary(st.session_state.messages)
    try:
        respuestas = infer_answers_fixed(st.session_state.messages)
        puntos, porcentaje, clasificacion, detalle = score_fixed(respuestas)
    except Exception:
        puntos, porcentaje, clasificacion, detalle = 0, 0, "NO CALIFICADA", []
    score = score_to_dict(puntos, porcentaje, clasificacion, detalle)
    return data, score

if st.button("💾 Guardar/Actualizar proyecto en memoria"):
    if not project_name and not project_id:
        st.warning("Indica al menos un nombre de proyecto.")
    else:
        pid = (project_id or project_name).strip()
        data, score = current_score_and_summary()
        ensure_kb()
        save_project(
            project_id=pid,
            name=project_name or pid,
            summary=data,
            score=score,
            messages=[m for m in st.session_state.get("messages", []) if m["role"] in ["user","assistant"]],
            kb_chunks=st.session_state.kb_chunks,
            kb_sources=st.session_state.kb_sources,
            kb_urls=st.session_state.kb_urls
        )
        st.success(f"Proyecto '{project_name or pid}' guardado en memoria.")

st.markdown("#### 📁 Proyectos guardados")
q = st.text_input("Buscar por nombre (vacío = todos)")
rows = list_projects(q if q else None)
if rows:
    for (pid, name, created) in rows[:50]:
        cols = st.columns([4,3,3,3,3])
        cols[0].write(f"**{name}**")
        cols[1].caption(pid)
        cols[2].caption(created)
        load_btn = cols[3].button("Cargar", key=f"load_{pid}")
        del_btn  = cols[4].button("Eliminar", key=f"del_{pid}")
        if load_btn:
            loaded = load_project(pid)
            if not loaded:
                st.error("No se pudo cargar el proyecto.")
            else:
                # restaurar mensajes (mantén el system prompt)
                st.session_state.messages = [{"role":"system","content": SYSTEM_PROMPT}]
                for m in loaded["messages"]:
                    st.session_state.messages.append(m)
                # restaurar KB
                ensure_kb()
                st.session_state.kb_chunks = loaded["kb_chunks"]
                st.session_state.kb_sources = loaded["kb_sources"]
                st.session_state.kb_urls = loaded["kb_urls"]
                # re-crear embeddings
                st.session_state.kb_vecs = None
                if st.session_state.kb_chunks:
                    st.info("Regenerando embeddings del proyecto cargado…")
                    st.session_state.kb_vecs = embed_texts(st.session_state.kb_chunks)
                st.success(f"Proyecto '{name}' cargado. Continúa la conversación o genera PDF.")
        if del_btn:
            delete_project(pid)
            st.warning(f"Proyecto '{name}' eliminado. Recarga la página para ver la lista actualizada.")
else:
    st.caption("No hay proyectos guardados aún.")

# ---- Indexación de páginas (Web)
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
                st.caption(f"Chunks almacenados: {len(st.session_state.kb_chunks)} | Empresas/etiquetas: {', '.join(list_companies_in_kb())}")
        except Exception as e:
            st.error(f"No pude indexar: {e}")

# ---- Ingesta de PDF (RFP / briefs)
st.subheader("📄 Ingesta de PDF como referencia")
pdf_company = st.text_input("Etiqueta del PDF (ej. Babel, Cliente X, Accenture)", key="pdf_company")
uploaded_pdf = st.file_uploader("Sube un PDF (RFP, brief, documento técnico)", type=["pdf"])
if uploaded_pdf is not None and st.button("Indexar PDF"):
    try:
        add_pdf_to_kb(pdf_company.strip() or "Documento", uploaded_pdf)
        st.success(f"PDF '{uploaded_pdf.name}' indexado con etiqueta: {pdf_company or 'Documento'}")
        st.caption(f"Chunks almacenados: {len(st.session_state.kb_chunks)}")
    except Exception as e:
        st.error(e)

if list_companies_in_kb():
    st.info("Empresas/etiquetas indexadas: " + ", ".join(list_companies_in_kb()))

# ---- Estado del chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": "Hola, estoy aquí para ayudarte a construir tu caso de negocio. ¿Cómo se llama tu proyecto y de qué trata?"}
    ]

for msg in st.session_state.messages[1:]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---- Chat (aprovecha RAG si hay contexto)
if prompt := st.chat_input("Escribe tu mensaje (puedes pedir comparaciones o propuestas)…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    grouped_ctx = retrieve_grouped(prompt, top_k_per_source=TOP_K_PER_SOURCE)
    context_text = make_comparison_instruction(grouped_ctx)
    aug_system = {
        "role": "system",
        "content": (
            "Usa el CONTEXTO (Web+PDF) para fundamentar tu respuesta. "
            "Si falta información para alguna empresa/etiqueta, dilo. Evita inventar datos.\n\n"
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

# ---- Propuesta de solución (desde el contexto)
st.subheader("🧩 Propuesta de solución (contexto Web+PDF)")
propuesta_alcance = st.text_area(
    "Enfócate en (opcional): objetivos, restricciones, industria, tecnologías, etc.",
    placeholder="Ej.: agente de ventas multicanal, integración CRM, SLA 99.9%, data residency MX…"
)
if st.button("Generar propuesta"):
    consulta = propuesta_alcance or "propuesta de solución basada en el contexto indexado"
    grouped_ctx = retrieve_grouped(consulta, top_k_per_source=TOP_K_PER_SOURCE)
    context_text = make_comparison_instruction(grouped_ctx)
    prompt_prop = (
        "Eres un consultor de soluciones de Babel. Usa EXCLUSIVAMENTE el contexto provisto "
        "(PDFs y páginas indexadas) para proponer una solución. Si algo no está en el contexto, "
        "menciónalo como supuesto explícito.\n\n"
        "Formato de salida:\n"
        "1) Resumen ejecutivo (3–5 bullets)\n"
        "2) Alcance (qué se hará y qué NO se hará)\n"
        "3) Arquitectura/Componentes (alto nivel, diagrama textual)\n"
        "4) Integraciones (APIs, fuentes de datos, CRM, ERP, etc.)\n"
        "5) Plan de implementación (fases, tiempos estimados)\n"
        "6) Equipo y roles\n"
        "7) Riesgos y mitigaciones\n"
        "8) Supuestos y dependencias\n"
        "9) Entregables\n"
        "10) Próximos pasos\n\n"
        f"Contexto:\n{context_text}\n\n"
        f"Enfoque del usuario: {propuesta_alcance or 'no especificado'}"
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Devuelve una propuesta clara y profesional, basada en el contexto. No inventes datos."},
                {"role": "user", "content": prompt_prop}
            ],
            temperature=0.4,
            timeout=90
        )
        propuesta_md = resp.choices[0].message.content
        st.session_state.last_proposal = propuesta_md
        st.markdown(propuesta_md)
        st.success("Propuesta generada.")
    except Exception as e:
        st.error(f"No pude generar la propuesta: {e}")

st.divider()
st.subheader("🧮 Calificación automática (≥ 70% = válida)")
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

    # Fuente Unicode (DejaVuSans.ttf en la raíz del repo)
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

    # Propuesta de solución (si existe)
    proposal = st.session_state.get("last_proposal")
    if proposal:
        pdf.ln(4)
        pdf.set_font("DejaVu", "", 13)
        write_lines(pdf, "Propuesta de solución (generada desde el contexto)")
        pdf.set_font("DejaVu", "", 12)
        texto = re.sub(r"[#*_>`~-]+", "", proposal)  # limpieza simple de markdown
        for para in texto.split("\n"):
            if para.strip():
                write_lines(pdf, para.strip())

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
