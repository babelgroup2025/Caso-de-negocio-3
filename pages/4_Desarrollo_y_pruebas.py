import os
import io
import json
import re
from datetime import datetime

import streamlit as st
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF

# ---------------------------
# Helpers de estado / defaults
# ---------------------------
def get_ss(key, default):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]

get_ss("score", 0)                         # viene de Evaluación
get_ss("listo_pdf", False)                 # bandera de esta fase
get_ss("memoria_proyectos", [])            # lista de dicts
get_ss("diseno", {})                       # fase 3, campos libres
get_ss("caso_negocio", {})                 # preguntas del caso
get_ss("chat_hist", [])                    # [{'role':'user'|'assistant','content': '...'}]
get_ss("rag_index", {"docs": []})          # índice simple

# ---------------------------------
# Normalización para evitar errores
# ---------------------------------
def clean_for_pdf(txt: str) -> str:
    if txt is None:
        return ""
    # quitar caracteres de control / reemplazos raros
    txt = txt.replace("\u200b", " ").replace("\u2028", " ").replace("\u2029", " ")
    txt = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", txt)
    # evitar líneas vacías con espacios no rompibles
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt

# ----------------------------
# Construcción del PDF final
# ----------------------------
def build_pdf():
    pdf = FPDF(format="Letter", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Fuente con acentos
    font_path = os.path.join(os.getcwd(), "DejaVuSans.ttf")
    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.set_font("DejaVu", "", 14)

    # Encabezado con logo (opcional)
    logo_path = os.path.join(os.getcwd(), "logo_babel.jpeg")
    if os.path.exists(logo_path):
        try:
            pdf.image(logo_path, x=10, y=10, w=28)
        except Exception:
            pass
    pdf.cell(0, 10, "", ln=1)  # separador

    pdf.set_font("DejaVu", "", 18)
    pdf.cell(0, 10, "Caso de Negocio – Agente Comercial Babel", ln=1)
    pdf.set_font("DejaVu", "", 10)
    pdf.cell(0, 6, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=1)
    pdf.ln(2)

    # Resumen de score
    pdf.set_font("DejaVu", "", 12)
    pdf.cell(0, 8, f"Score (Fase 1): {st.session_state['score']}%", ln=1)

    # Diseño (Fase 3)
    pdf.set_font("DejaVu", "", 14)
    pdf.cell(0, 8, "Diseño (Fase 3)", ln=1)
    pdf.set_font("DejaVu", "", 11)
    dis = st.session_state.get("diseno", {})
    for k, v in dis.items():
        section = clean_for_pdf(f"{k}: {v}")
        if not section:
            continue
        pdf.multi_cell(0, 6, section)
        pdf.ln(1)

    # Caso de negocio
    pdf.set_font("DejaVu", "", 14)
    pdf.cell(0, 8, "Caso de Negocio (Chat)", ln=1)
    pdf.set_font("DejaVu", "", 11)
    caso = st.session_state.get("caso_negocio", {})
    if caso:
        for k, v in caso.items():
            k2 = clean_for_pdf(str(k))
            v2 = clean_for_pdf(str(v))
            if not v2:
                continue
            pdf.multi_cell(0, 6, f"{k2}: {v2}")
            pdf.ln(0.5)

    # Comparativa / RAG
    pdf.set_font("DejaVu", "", 14)
    pdf.cell(0, 8, "Comparativa competitiva (RAG)", ln=1)
    pdf.set_font("DejaVu", "", 11)
    rag = st.session_state.get("rag_index", {"docs": []})
    if rag.get("docs"):
        fuentes = sorted(set(d.get("url", "") for d in rag["docs"] if d.get("url")))
        pdf.multi_cell(0, 6, clean_for_pdf("Fuentes indexadas: " + ", ".join(fuentes)))
    else:
        pdf.multi_cell(0, 6, "Sin fuentes indexadas.")

    # Conversación (anexo)
    pdf.add_page()
    pdf.set_font("DejaVu", "", 14)
    pdf.cell(0, 8, "Anexo: Conversación", ln=1)
    pdf.set_font("DejaVu", "", 11)
    for m in st.session_state["chat_hist"]:
        role = "Cliente" if m.get("role") == "user" else "Asistente"
        content = clean_for_pdf(m.get("content", ""))
        if not content:
            continue
        pdf.multi_cell(0, 6, f"{role}: {content}")
        pdf.ln(0.5)

    # Exportar a bytes para download_button
    bio = io.BytesIO()
    pdf.output(bio)  # fpdf2 soporta buffer in-memory
    bio.seek(0)
    return bio

# -----------------
# RAG muy sencillo
# -----------------
def crawl_page(url: str) -> list[dict]:
    """Descarga y trocea texto simple de una URL en pequeños fragmentos."""
    try:
        html = requests.get(url, timeout=15).text
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        chunks = []
        step = 600
        for i in range(0, len(text), step):
            chunks.append({"url": url, "chunk": text[i:i+step]})
        return chunks[:40]  # cap
    except Exception as e:
        st.warning(f"No se pudo indexar {url}: {e}")
        return []

def ensure_rag_store():
    if "rag_index" not in st.session_state:
        st.session_state["rag_index"] = {"docs": []}

def add_urls_to_index(urls: list[str]):
    ensure_rag_store()
    for u in urls:
        u = u.strip()
        if not u:
            continue
        docs = crawl_page(u)
        st.session_state["rag_index"]["docs"].extend(docs)
    st.success("Fuentes indexadas / actualizadas.")

def simple_search(query: str, k: int = 5):
    ensure_rag_store()
    q = query.lower()
    scored = []
    for d in st.session_state["rag_index"]["docs"]:
        c = d["chunk"].lower()
        score = c.count(q) if len(q) > 2 else 0
        scored.append((score, d))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for s, d in scored[:k] if s > 0]

# -----------------
# Chat (sin API)
# -----------------
def chat_reply_local(user_msg: str, contexto: str = "") -> str:
    """
    Respuesta 'mock' simple sin API, para que funcione aunque no haya clave.
    Si tienes OPENAI_API_KEY y quieres usar modelo, sustituye por llamada real.
    """
    base = (
        "Gracias. He leído tu mensaje y el contexto.\n\n"
        "Resumen rápido: "
    )
    resumen = (user_msg[:180] + "…") if len(user_msg) > 180 else user_msg
    tips = "\n\nPróximos pasos sugeridos: definir KPIs, riesgos y entregables clave."
    return base + resumen + tips

# --------------
# Interfaz UI
# --------------
st.set_page_config(page_title="Fase 4 – Desarrollo y Pruebas", page_icon="🧪", layout="wide")
st.title("Fase 4: Desarrollo y Pruebas")

colA, colB, colC = st.columns(3)
colA.metric("Score (Fase 1)", f"{st.session_state['score']}%")
colB.metric("Listo para PDF", "Sí" if st.session_state["listo_pdf"] else "No")
colC.metric("Fuentes RAG", len(st.session_state.get("rag_index", {}).get("docs", [])))

st.write("---")

# ----- Bloque RAG
with st.expander("📚 RAG competitivo (indexa webs una sola vez y reutiliza)"):
    st.caption("Ejemplos: https://www.babelgroup.com/ | https://www.accenture.com/ | https://www.ibm.com/")
    urls_text = st.text_area("Pega 1 o varias URLs (separadas por salto de línea)", height=100)
    col1, col2 = st.columns(2)
    if col1.button("Indexar / Actualizar RAG"):
        urls = [u.strip() for u in urls_text.splitlines() if u.strip()]
        add_urls_to_index(urls)

    query = st.text_input("Consulta de comparación (ej. 'servicios de IA generativa')")
    if col2.button("Buscar en RAG"):
        if not query.strip():
            st.warning("Escribe una consulta.")
        else:
            results = simple_search(query, k=6)
            if results:
                st.success(f"{len(results)} fragmentos relevantes")
                for r in results:
                    with st.container(border=True):
                        st.caption(r["url"])
                        st.write(r["chunk"])
            else:
                st.info("Sin coincidencias; intenta con otra consulta.")

st.write("---")

# ----- Chat con memoria
st.subheader("💬 Chat del agente")
for m in st.session_state["chat_hist"]:
    with st.chat_message("user" if m["role"] == "user" else "assistant"):
        st.write(m["content"])

prompt = st.chat_input("Escribe tu mensaje para el agente…")
if prompt:
    st.session_state["chat_hist"].append({"role": "user", "content": prompt})

    # Armar un contexto mínimo con lo disponible
    contexto = []
    contexto.append(f"Score: {st.session_state['score']}%")
    if st.session_state.get("diseno"):
        contexto.append("Diseño cargado.")
    if st.session_state.get("rag_index", {}).get("docs"):
        contexto.append("RAG listo con fuentes indexadas.")
    ctx = " | ".join(contexto)

    # Respuesta local (sin API). Sustituye por llamada real si tienes la clave.
    answer = chat_reply_local(prompt, ctx)
    st.session_state["chat_hist"].append({"role": "assistant", "content": answer})

    st.rerun()

st.write("---")

# ----- Marcado de listo y generación de PDF
colx, coly = st.columns([1, 2])

with colx:
    st.markdown("### 🧾 Listo para PDF")
    st.write("Marca cuando esta fase quede cerrada y el documento esté listo para generarse.")
    if st.button("Marcar Listo para PDF"):
        st.session_state["listo_pdf"] = True
        st.success("¡Listo para PDF marcado!")
        st.rerun()

with coly:
    st.markdown("### 📄 Generar PDF (desde Fase 4)")
    if not st.session_state["listo_pdf"]:
        st.info("Primero marca **Listo para PDF** para habilitar la descarga.")
    else:
        if st.button("Construir PDF"):
            try:
                pdf_bytes = build_pdf()
                st.download_button(
                    label="⬇️ Descargar Caso de Negocio (PDF)",
                    data=pdf_bytes,
                    file_name="Caso_de_Negocio_Babel.pdf",
                    mime="application/pdf",
                )
                st.success("PDF listo para descargar.")
            except Exception as e:
                st.error(f"Error al generar el PDF: {e}")
