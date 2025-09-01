# pages/4_Desarrollo_y_Pruebas.py – RAG + Chat + Caso de Negocio guiado + Checklist + PDF
import os, re, json
import requests
import numpy as np
import streamlit as st
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from fpdf import FPDF
from openai import OpenAI

st.set_page_config(page_title="Fase 4 - Desarrollo/Pruebas + RAG", layout="wide")
st.title("🛠️ Fase 4: Desarrollo, Pruebas e Inteligencia Competitiva (RAG)")

# -------------------- Guardas de flujo --------------------
if not st.session_state.get("evaluacion_ok", False):
    st.warning("La oportunidad no alcanzó 70% en Evaluación. Ve a **Fase 1**.")
    st.stop()

# -------------------- Estado compartido --------------------
st.session_state.setdefault("ready_for_pdf", False)
st.session_state.setdefault("dev_checklist", {"casos_uso": False, "pruebas": False, "riesgos": False, "aprobacion": False})
st.session_state.setdefault("dev_chat", [])
st.session_state.setdefault("devtest", {})                # devtest['notas']
st.session_state.setdefault("competitive", {})            # {'comparison': str}
st.session_state.setdefault("caso_negocio", {})
st.session_state.setdefault("cn_resumen_md", None)
st.session_state.setdefault("cn_redaccion_md", None)

# -------------------- Constantes/paths --------------------
FONT_PATH = "DejaVuSans.ttf"
INDEX_PATH = "rag_competencia.json"           # índice persistente
UA = "Mozilla/5.0 (compatible; Babel-Agent/1.0)"
TIMEOUT = 12
MAX_PAGES_PER_SITE = 4
MAX_CHARS_PER_SITE = 8000
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
TOP_K = 6
EMBED_MODEL = "text-embedding-3-small"

# -------------------- Helpers generales --------------------
def clean_text(text: str) -> str:
    if not text:
        return ""
    t = str(text).replace("\r", " ").replace("\x00", "")
    return t if t.strip() else " "

def pdf_header(pdf: FPDF, title: str):
    if os.path.exists("logo_babel.jpeg"):
        try: pdf.image("logo_babel.jpeg", x=10, y=8, w=28)
        except Exception: pass
    pdf.ln(10)
    pdf.set_font_size(18)
    pdf.cell(0, 10, clean_text(title), ln=1, align="C")
    pdf.set_font_size(11)
    pdf.cell(0, 7, clean_text("Reporte generado desde Fase 4"), ln=1, align="C")
    pdf.ln(4)

def get_client():
    api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
    if not api_key:
        st.info("Agrega tu **OPENAI_API_KEY** en Settings → Secrets para usar la IA.")
        return None
    return OpenAI(api_key=api_key)

# -------------------- RAG: crawling + chunking + embeddings --------------------
def fetch_text(url: str) -> str:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        if r.status_code != 200 or "text/html" not in r.headers.get("content-type",""):
            return ""
        soup = BeautifulSoup(r.text, "html.parser")
        for t in soup(["script","style","noscript","header","footer","form"]): t.decompose()
        text = soup.get_text(separator=" ")
        return re.sub(r"\s+", " ", text).strip()
    except Exception:
        return ""

def discover_links(base_url: str, max_links=MAX_PAGES_PER_SITE-1):
    links=set()
    try:
        r = requests.get(base_url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            url = urljoin(base_url, a["href"])
            if urlparse(url).netloc == urlparse(base_url).netloc:
                if re.search(r"(servic|solution|soluc|capabil|industr|product|oferta|portfolio)", url, re.I):
                    links.add(url)
            if len(links) >= max_links:
                break
    except Exception:
        pass
    return list(links)

def harvest_site(base_url: str) -> str:
    seen = set([base_url])
    texts = [fetch_text(base_url)]
    for link in discover_links(base_url):
        if link in seen: continue
        seen.add(link)
        texts.append(fetch_text(link))
        if sum(len(t) for t in texts if t) > MAX_CHARS_PER_SITE: break
    return (" ".join([t for t in texts if t])[:MAX_CHARS_PER_SITE]).strip()

def chunk_text(t: str, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks=[]; i=0
    while i < len(t):
        chunk = t[i:i+size]
        chunks.append(chunk)
        i += max(1, size-overlap)
    return [c.strip() for c in chunks if c.strip()]

def embed_texts(client: OpenAI, texts):
    if not texts: return []
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]

def cosine_sim(a, b):
    a = np.array(a); b = np.array(b)
    denom = (np.linalg.norm(a)*np.linalg.norm(b)) or 1e-9
    return float(np.dot(a, b) / denom)

def load_index():
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH,"r",encoding="utf-8") as f:
            return json.load(f)
    return {"sources": []}

def save_index(index):
    with open(INDEX_PATH,"w",encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)

def add_site_to_index(client: OpenAI, index: dict, name: str, url: str):
    raw = harvest_site(url)
    if not raw:
        return False, "No se pudo extraer contenido"
    texts = chunk_text(raw)
    embs  = embed_texts(client, texts)
    entry = {"name": name or url, "url": url, "chunks": [{"text": t, "emb": e} for t, e in zip(texts, embs)]}
    index["sources"] = [s for s in index["sources"] if s["url"] != url]
    index["sources"].append(entry)
    save_index(index)
    return True, f"Indexado: {name or url} ({len(texts)} fragmentos)"

def retrieve(index, client: OpenAI, query: str, k=TOP_K):
    q_emb = embed_texts(client, [query])[0]
    scored=[]
    for src in index.get("sources", []):
        for ch in src["chunks"]:
            sim = cosine_sim(q_emb, ch["emb"])
            scored.append((sim, src["name"], src["url"], ch["text"]))
    scored.sort(key=lambda x: x[0], reverse=True)
    results = scored[:k]
    grouped = {}
    for sim, name, url, text in results:
        grouped.setdefault((name,url), []).append((sim,text))
    return results, grouped

# -------------------- LLM sobre RAG --------------------
def compare_with_rag(client: OpenAI, grouped_results, extra_context: str):
    bullets=[]
    for (name,url), pairs in grouped_results.items():
        top = "\n".join(f"- {t[:350]}" for _, t in pairs[:3])
        bullets.append(f"◼ {name} ({url}):\n{top}")
    context = "\n\n".join(bullets) or "No hay contexto recuperado."
    sys = ("Eres consultor senior de preventa. Con el contexto recuperado (RAG) compara competidores "
           "y propone una estrategia ganadora para Babel: (1) fortalezas/debilidades por empresa, "
           "(2) tabla rápida de diferenciadores, (3) propuesta final (alcance+KPIs).")
    user = (f"Contexto del cliente/proyecto:\n{extra_context or 'N/A'}\n\n"
            f"Contexto recuperado:\n{context}\n\n"
            "Entrega la comparativa y propuesta en bullets y subtítulos claros.")
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":sys},{"role":"user","content":user}],
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()

# -------------------- PDF --------------------
def build_pdf() -> str:
    score = st.session_state.get("score_total", 0)
    eval_answers = st.session_state.get("eval_answers", {})
    diseno = st.session_state.get("diseno", {})
    proyectos = st.session_state.get("proyectos", [])
    notas = st.session_state.get("devtest", {}).get("notas", "")
    comp_text = st.session_state.get("competitive", {}).get("comparison", "")
    index = load_index()

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
        pdf.add_font("DejaVu", "", FONT_PATH, uni=True); pdf.set_font("DejaVu","",14)
    else:
        pdf.set_font("Arial","",14)

    pdf_header(pdf, "Caso de Negocio - Babel")

    pdf.set_font_size(12)
    pdf.multi_cell(190, 8, clean_text(f"Score Evaluación: {score}%"), align="L")
    pdf.multi_cell(190, 8, clean_text(f"Proyectos en memoria: {len(proyectos)}"), align="L")
    pdf.multi_cell(190, 8, clean_text(f"Listo para PDF: {'Sí' if st.session_state.get('ready_for_pdf') else 'No'}"), align="L")
    pdf.ln(2)

    pdf.set_font_size(14); pdf.cell(0,8,clean_text("Evaluación (detalle)"), ln=1)
    pdf.set_font_size(11)
    for k, texto, peso in detalle_preguntas:
        r = eval_answers.get(k, "No"); pts = peso if r == "Sí" else 0
        pdf.multi_cell(190, 6, clean_text(f"• {texto} → {r} (peso {peso}, pts {pts})"), align="L")
    pdf.ln(2)

    if diseno:
        pdf.set_font_size(14); pdf.cell(0,8,clean_text("Diseño de la solución (resumen)"), ln=1)
        pdf.set_font_size(11)
        for k,v in diseno.items():
            pdf.multi_cell(190, 6, clean_text(f"• {k}: {v}"), align="L")
        pdf.ln(2)

    if notas:
        pdf.set_font_size(14); pdf.cell(0,8,clean_text("Notas de desarrollo/pruebas"), ln=1)
        pdf.set_font_size(11); pdf.multi_cell(190,6,clean_text(notas), align="L"); pdf.ln(2)

    # --- Caso de Negocio (si existe) ---
    cn = st.session_state.get("caso_negocio", {})
    cn_resumen = st.session_state.get("cn_resumen_md")
    cn_redaccion = st.session_state.get("cn_redaccion_md")
    if cn or cn_resumen or cn_redaccion:
        pdf.set_font_size(14); pdf.cell(0, 8, clean_text("Caso de Negocio"), ln=1)
        pdf.set_font_size(11)
        if cn_resumen:
            for line in cn_resumen.splitlines():
                pdf.multi_cell(190, 6, clean_text(line), align="L")
            pdf.ln(2)
        else:
            mapping = [
                ("Objetivos de negocio", "objetivos_negocio"),
                ("Problema a resolver", "problema"),
                ("Solución esperada", "solucion_esperada"),
                ("Target (usuarios)", "target"),
                ("Funcionalidades esperadas", "funcionalidades"),
                ("Expectativas", "expectativas"),
                ("Experiencia previa", "experiencia_previa"),
                ("Forma de adjudicación", "adjudicacion"),
                ("Criterios de evaluación", "criterios_eval"),
                ("Fecha de lanzamiento", "fecha_lanzamiento"),
                ("Rango de presupuesto", "rango_presupuesto"),
                ("Caso de negocio (narrativo)", "caso_negocio"),
                ("Nombre del proyecto", "nombre_proyecto"),
                ("Notas generales", "notas"),
            ]
            for label, key in mapping:
                val = clean_text(cn.get(key, "—"))
                pdf.multi_cell(190, 6, clean_text(f"• {label}: {val}"), align="L")
            pdf.ln(2)

        if cn_redaccion:
            pdf.set_font_size(12)
            pdf.multi_cell(190, 6, clean_text("— Redacción ejecutiva (IA) —"), align="L")
            pdf.set_font_size(11)
            for line in cn_redaccion.splitlines():
                pdf.multi_cell(190, 6, clean_text(line), align="L")
            pdf.ln(2)

    # Fuentes del índice (RAG)
    idx = load_index().get("sources", [])
    if idx:
        pdf.set_font_size(14); pdf.cell(0,8,clean_text("Base de conocimiento (RAG) – Fuentes"), ln=1)
        pdf.set_font_size(11)
        for s in idx:
            pdf.multi_cell(190,6,clean_text(f"◼ {s['name']} – {s['url']} ({len(s['chunks'])} fragmentos)"), align="L")
        pdf.ln(2)

    # Comparativa/propuesta del RAG
    comp_text = st.session_state.get("competitive", {}).get("comparison", "")
    if comp_text:
        pdf.set_font_size(14); pdf.cell(0,8,clean_text("Comparativa y propuesta para Babel (RAG)"), ln=1)
        pdf.set_font_size(11); pdf.multi_cell(190,6,clean_text(comp_text), align="L"); pdf.ln(2)

    out = "caso_negocio_babel.pdf"
    pdf.output(out)
    return out

# -------------------- UI (Tabs) --------------------
tab_kb, tab_qa, tab_cn, tab_chat, tab_pdf = st.tabs([
    "📚 Base de conocimiento (RAG)", "🔎 Consultar/Comparar", "🧾 Caso de Negocio (chat guiado)", "💬 Chat", "✅ Checklist y PDF"
])

# ===== TAB 1: Construir/gestionar índice =====
with tab_kb:
    st.subheader("📚 Base de conocimiento (RAG) – Babel y competidores")
    st.caption("Indexa una vez y reutiliza. Puedes actualizar cuando cambien los sitios.")

    client = get_client()
    index = load_index()

    col1, col2 = st.columns([1,1])
    with col1:
        name = st.text_input("Nombre (ej. Babel)", value="Babel")
        url = st.text_input("URL raíz", value="https://www.babelgroup.com/")
        if st.button("➕ Indexar/Actualizar este sitio"):
            if not client: st.stop()
            ok,msg = add_site_to_index(client, index, name.strip(), url.strip())
            st.success(msg) if ok else st.error(msg)

    with col2:
        multi = st.text_area("Varias URLs (una por línea, formato: Nombre|URL)",
                             placeholder="Accenture|https://www.accenture.com/\nIBM Consulting|https://www.ibm.com/consulting/")
        if st.button("📥 Indexar en lote"):
            if not client: st.stop()
            total_ok=0; fails=[]
            for line in multi.splitlines():
                if "|" not in line: continue
                n,u = [x.strip() for x in line.split("|",1)]
                ok,msg = add_site_to_index(client, index, n, u)
                total_ok += int(ok)
                if not ok: fails.append(f"{n}: {msg}")
            st.success(f"Sitios indexados: {total_ok}")
            if fails: st.warning("No indexados:\n- " + "\n- ".join(fails))

    st.markdown("---")
    st.subheader("Fuentes actuales")
    idx = load_index().get("sources", [])
    if not idx:
        st.info("Aún no hay fuentes indexadas.")
    else:
        for s in idx:
            st.markdown(f"**◼ {s['name']}** – {s['url']}  · Fragmentos: {len(s['chunks'])}")
        colx, coly = st.columns(2)
        if colx.button("🗑️ Vaciar índice"):
            save_index({"sources":[]}); st.success("Índice vaciado.")
        if coly.button("🔄 Recargar índice"):
            st.experimental_rerun()

# ===== TAB 2: Consulta/Comparativa con RAG =====
with tab_qa:
    st.subheader("🔎 Consulta y comparativa (usa la base de conocimiento)")
    query = st.text_input("Escribe una pregunta/consulta",
                          value="¿Qué propuestas de valor ofrece cada competidor y cómo debería posicionarse Babel?")
    extra = st.text_area("Contexto adicional (sector, objetivos, restricciones)", height=120)

    client = get_client()
    if st.button("🧠 Generar comparativa con RAG"):
        if not client: st.stop()
        index = load_index()
        if not index.get("sources"):
            st.error("No hay fuentes en el índice. Ve a **Base de conocimiento** para indexar.")
            st.stop()

        results, grouped = retrieve(index, client, query, k=TOP_K)
        if not results:
            st.error("No se recuperó contexto.")
        else:
            with st.expander("Ver fragmentos recuperados"):
                for (name,url), pairs in grouped.items():
                    st.markdown(f"**{name}** – {url}")
                    for sim, text in pairs[:2]:
                        st.caption(f"sim={sim:.3f}")
                        st.write(text[:700] + ("..." if len(text)>700 else ""))
                    st.divider()

            comp = compare_with_rag(client, grouped, extra)
            st.session_state["competitive"]["comparison"] = comp
            st.success("Comparativa generada y almacenada para el PDF.")
            st.markdown("### Resultado (propuesta para Babel)")
            st.write(comp)

# ===== TAB 3: Caso de Negocio (chat guiado) =====
with tab_cn:
    st.subheader("🧾 Caso de Negocio — Captura guiada por chat")

    st.session_state.setdefault("cn_idx", 0)
    st.session_state.setdefault("cn_done", False)
    st.session_state.setdefault("cn_chat", [])

    CN_QUESTIONS = [
        ("objetivos_negocio", "¿Cuáles son los objetivos de negocio?"),
        ("problema", "¿Cuál es el problema a resolver?"),
        ("solucion_esperada", "¿Cuál es la solución esperada?"),
        ("target", "¿Quién va a utilizar la solución? – TARGET"),
        ("funcionalidades", "¿Qué funcionalidades espera tener?"),
        ("expectativas", "¿Qué expectativas tiene con esta solución?"),
        ("experiencia_previa", "¿Ha tenido experiencia previa similar a este proyecto?"),
        ("adjudicacion", "¿Cuál es la forma de adjudicación?"),
        ("criterios_eval", "¿Cuáles son los criterios de evaluación?"),
        ("fecha_lanzamiento", "¿Cuál sería la fecha de lanzamiento?"),
        ("rango_presupuesto", "¿Cuál es el rango del presupuesto?"),
        ("caso_negocio", "Caso de negocio (resumen narrativo corto)"),
        ("nombre_proyecto", "Nombre de proyecto"),
        ("notas", "Notas generales"),
    ]

    # Historial visual
    with st.container(height=380, border=True):
        if not st.session_state["cn_chat"]:
            st.markdown("> 👋 Empecemos. Te haré preguntas para construir el Caso de Negocio.")
        for m in st.session_state["cn_chat"]:
            with st.chat_message(m["role"]):
                st.write(m["content"])

    if not st.session_state["cn_done"]:
        clave, pregunta = CN_QUESTIONS[st.session_state["cn_idx"]]
        if not st.session_state["cn_chat"] or st.session_state["cn_chat"][-1]["role"] != "assistant":
            st.session_state["cn_chat"].append({"role": "assistant", "content": pregunta})

        user_msg = st.chat_input("Responde aquí…")
        if user_msg:
            st.session_state["cn_chat"].append({"role": "user", "content": user_msg})
            st.session_state["caso_negocio"][clave] = user_msg.strip()
            st.session_state["cn_idx"] += 1
            if st.session_state["cn_idx"] >= len(CN_QUESTIONS):
                st.session_state["cn_done"] = True
                st.session_state["cn_chat"].append({"role":"assistant","content":"✅ ¡Listo! Ya tengo toda la información. Abajo puedes generar el resumen."})
            else:
                siguiente = CN_QUESTIONS[st.session_state["cn_idx"]][1]
                st.session_state["cn_chat"].append({"role": "assistant", "content": siguiente})
            st.experimental_rerun()
    else:
        st.success("Formulario completo. Puedes revisar/editar debajo o generar la redacción ejecutiva.")

    # Ver/editar respuestas
    with st.expander("📝 Ver y editar respuestas capturadas"):
        for clave, label in CN_QUESTIONS:
            val = st.session_state["caso_negocio"].get(clave, "")
            st.session_state["caso_negocio"][clave] = st.text_area(label, val, height=80, key=f"cn_edit_{clave}")
        st.caption("Los cambios se guardan en el estado y se usarán en el PDF.")

    # Resumen estructurado (sin IA)
    def build_cn_resumen_md(cn: dict) -> str:
        def g(k): return (cn.get(k, "—") or "—").strip() or "—"
        return f"""### Caso de Negocio — Resumen Estructurado

- **Objetivos de negocio:** {g('objetivos_negocio')}
- **Problema a resolver:** {g('problema')}
- **Solución esperada:** {g('solucion_esperada')}
- **Target (usuarios):** {g('target')}
- **Funcionalidades esperadas:** {g('funcionalidades')}
- **Expectativas:** {g('expectativas')}
- **Experiencia previa:** {g('experiencia_previa')}
- **Forma de adjudicación:** {g('adjudicacion')}
- **Criterios de evaluación:** {g('criterios_eval')}
- **Fecha de lanzamiento:** {g('fecha_lanzamiento')}
- **Rango de presupuesto:** {g('rango_presupuesto')}
- **Caso de negocio (narrativo):** {g('caso_negocio')}
- **Nombre del proyecto:** {g('nombre_proyecto')}
- **Notas generales:** {g('notas')}
"""

    colA, colB, colC = st.columns(3)
    if colA.button("🧩 Generar resumen estructurado"):
        st.session_state["cn_resumen_md"] = build_cn_resumen_md(st.session_state["caso_negocio"])
        st.success("Resumen estructurado generado.")
    if colB.button("🧹 Reiniciar conversación"):
        st.session_state["cn_chat"] = []
        st.session_state["caso_negocio"] = {}
        st.session_state["cn_idx"] = 0
        st.session_state["cn_done"] = False
        st.session_state["cn_resumen_md"] = None
        st.session_state["cn_redaccion_md"] = None
        st.experimental_rerun()

    # Redacción ejecutiva con IA (opcional)
    api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
    if api_key and colC.button("🤖 Redacción ejecutiva (IA)"):
        client = OpenAI(api_key=api_key)
        brief = st.session_state.get("cn_resumen_md") or build_cn_resumen_md(st.session_state["caso_negocio"])
        sys = "Eres consultor senior. Redacta una síntesis ejecutiva clara y persuasiva (máx 300-400 palabras)."
        user = f"Base del caso de negocio:\n\n{brief}"
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"system","content":sys},{"role":"user","content":user}],
                temperature=0.3,
            )
            st.session_state["cn_redaccion_md"] = resp.choices[0].message.content.strip()
            st.success("Redacción ejecutiva generada.")
        except Exception as e:
            st.error(f"Error IA: {e}")

    if st.session_state.get("cn_resumen_md"):
        st.markdown("### 📄 Resumen Estructurado")
        st.markdown(st.session_state["cn_resumen_md"])
    if st.session_state.get("cn_redaccion_md"):
        st.markdown("### 🧠 Redacción Ejecutiva (IA)")
        st.markdown(st.session_state["cn_redaccion_md"])

    st.info("El resumen y la redacción (si existe) se incluirán en el PDF final.")

# ===== TAB 4: Chat libre (contexto general del proyecto) =====
with tab_chat:
    st.subheader("💬 Chat con el agente")
    client = get_client()
    if client:
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
                st.markdown("> 👇 Escribe tu primera pregunta…")
            for m in st.session_state["dev_chat"]:
                with st.chat_message("user" if m["role"] == "user" else "assistant"):
                    st.write(m["content"])

        user_msg = st.chat_input("Pregunta al agente…")
        if user_msg:
            st.session_state["dev_chat"].append({"role": "user", "content": user_msg})
            msgs = [{"role":"system","content": system_prompt}] + st.session_state["dev_chat"]
            try:
                resp = client.chat.completions.create(model="gpt-4o-mini", messages=msgs, temperature=0.3)
                answer = resp.choices[0].message.content.strip()
            except Exception as e:
                answer = f"Error API: {e}"
            st.session_state["dev_chat"].append({"role": "assistant", "content": answer})
            st.experimental_rerun()

        cols = st.columns(2)
        if cols[0].button("🧹 Limpiar chat"):
            st.session_state["dev_chat"] = []
            st.experimental_rerun()
        with st.expander("📎 Notas de pruebas (se incluyen en PDF)"):
            notas = st.text_area("Notas/criterios", height=140, value=st.session_state.get("devtest",{}).get("notas",""))
            if st.button("Guardar notas"):
                st.session_state.setdefault("devtest", {})["notas"] = notas
                st.success("Notas guardadas.")
    else:
        st.stop()

# ===== TAB 5: Checklist + PDF =====
with tab_pdf:
    st.subheader("✅ Checklist y generación de PDF")
    dc = st.session_state["dev_checklist"]
    dc["casos_uso"]  = st.checkbox("Casos de uso definidos", value=dc["casos_uso"])
    dc["pruebas"]    = st.checkbox("Criterios de prueba definidos", value=dc["pruebas"])
    dc["riesgos"]    = st.checkbox("Riesgos y mitigaciones", value=dc["riesgos"])
    dc["aprobacion"] = st.checkbox("Aprobación interna", value=dc["aprobacion"])
    all_ok = all(dc.values())
    st.metric("Listo para PDF", "Sí" if st.session_state.get("ready_for_pdf") else "No")
    if st.button("📄 Marcar **Listo para PDF**"):
        if all_ok:
            st.session_state["ready_for_pdf"] = True
            st.success("¡Listo para PDF marcado!")
            st.experimental_rerun()
        else:
            st.warning("Faltan puntos del checklist.")

    st.markdown("---")
    if not st.session_state["ready_for_pdf"]:
        st.button("⬇️ Generar PDF", disabled=True)
        st.info("Primero marca **Listo para PDF**.")
    else:
        if st.button("⬇️ Generar PDF"):
            if not os.path.exists(FONT_PATH):
                st.error("No se encontró **DejaVuSans.ttf** en la raíz del repo.")
            else:
                try:
                    path = build_pdf()
                    with open(path,"rb") as f:
                        st.download_button("Descargar PDF", f, file_name="caso_negocio_babel.pdf", mime="application/pdf")
                    st.success("PDF generado.")
                except Exception as e:
                    st.error(f"Error al generar PDF: {e}")
