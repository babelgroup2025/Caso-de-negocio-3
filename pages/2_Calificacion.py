# pages/2_Calificacion_y_Caso.py
import os
import re
import unicodedata
import streamlit as st
from fpdf import FPDF
import requests
from bs4 import BeautifulSoup

# ========= (Opcional) IA para redactar mejor =========
USE_AI = False
api_key = st.secrets.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
if api_key:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        USE_AI = True
    except Exception:
        USE_AI = False

# ========= Utilidades generales =========
def clean_text(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\u200b", " ").replace("\u00A0", " ")
    s = s.replace("\r", " ").replace("\t", " ")
    # Colapsa espacios multiples
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip()

def ensure_state():
    defaults = {
        "lead_info": {},
        "score_raw": 0,
        "score_pct": 0,
        "score_detail": {},
        "case_answers": {},
        "chat_history": [],
        "case_done": False,
        "pdf_bytes": None,
        "comp_kb": {},               # <-- aquí guardamos textos por empresa
        "comp_brief": "",            # <-- resumen competitivo generado
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def set_answer(key, value):
    st.session_state["case_answers"][key] = value

def next_question_key():
    order = [
        "objetivos","problema","solucion","target","funcionalidades",
        "expectativas","experiencia","adjudicacion","criterios",
        "fecha_lanzamiento","presupuesto","nombre_proyecto","notas",
    ]
    for k in order:
        if not st.session_state["case_answers"].get(k):
            return k
    return None

def question_text(key):
    mapping = {
        "objetivos": "¿Cuáles son los objetivos de negocio?",
        "problema": "¿Cuál es el problema a resolver?",
        "solucion": "¿Cuál es la solución esperada?",
        "target": "¿Quién va a utilizar la solución? (TARGET)",
        "funcionalidades": "¿Qué funcionalidades espera tener?",
        "expectativas": "¿Qué expectativas tiene con esta solución?",
        "experiencia": "¿Ha tenido experiencia previa similar a este proyecto?",
        "adjudicacion": "¿Cuál es la forma de adjudicación?",
        "criterios": "¿Cuáles son los criterios de evaluación?",
        "fecha_lanzamiento": "¿Cuál sería la fecha de lanzamiento?",
        "presupuesto": "¿Cuál es el rango del presupuesto?",
        "nombre_proyecto": "¿Nombre del proyecto?",
        "notas": "¿Notas o consideraciones generales?",
    }
    return mapping.get(key, key)

# ========= PDF =========
def render_pdf_bytes(lead, score_pct, answers, resumen, comp_brief):
    class PDF(FPDF):
        pass

    pdf = PDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    # DejaVu para acentos
    font_path = "DejaVuSans.ttf"
    if os.path.exists(font_path):
        pdf.add_font("DejaVu", "", font_path, uni=True)
        pdf.set_font("DejaVu", "", 14)
    else:
        pdf.set_font("Arial", "", 14)

    pdf.cell(0, 10, clean_text("Caso de Negocio – Agente Comercial Babel"), ln=1)
    pdf.set_font_size(10)
    lead_line = f"Empresa: {lead.get('empresa','')}  |  Contacto: {lead.get('nombre','')}  |  Email: {lead.get('correo','')}  |  Tel: {lead.get('telefono','')}"
    pdf.multi_cell(0, 6, clean_text(lead_line))
    pdf.ln(2)
    pdf.set_font_size(12)
    pdf.cell(0, 8, clean_text(f"Calificación del Lead: {score_pct:.0f}%"), ln=1)
    pdf.ln(3)

    pdf.set_font_size(13)
    pdf.cell(0, 8, clean_text("Resumen Ejecutivo"), ln=1)
    pdf.set_font_size(11)
    pdf.multi_cell(0, 6, clean_text(resumen))
    pdf.ln(3)

    if comp_brief:
        pdf.set_font_size(13)
        pdf.cell(0, 8, clean_text("Inteligencia Competitiva (Babel vs Competidores)"), ln=1)
        pdf.set_font_size(11)
        pdf.multi_cell(0, 6, clean_text(comp_brief))
        pdf.ln(3)

    # Detalle
    secciones = [
        ("Objetivos de negocio", "objetivos"),
        ("Problema a resolver", "problema"),
        ("Solución esperada", "solucion"),
        ("Usuarios / TARGET", "target"),
        ("Funcionalidades esperadas", "funcionalidades"),
        ("Expectativas", "expectativas"),
        ("Experiencia previa", "experiencia"),
        ("Forma de adjudicación", "adjudicacion"),
        ("Criterios de evaluación", "criterios"),
        ("Fecha de lanzamiento", "fecha_lanzamiento"),
        ("Rango de presupuesto", "presupuesto"),
        ("Nombre del proyecto", "nombre_proyecto"),
        ("Notas generales", "notas"),
    ]
    pdf.set_font_size(12)
    for title, k in secciones:
        pdf.ln(2)
        pdf.set_font_size(12)
        pdf.cell(0, 7, clean_text(title), ln=1)
        pdf.set_font_size(11)
        pdf.multi_cell(0, 6, clean_text(answers.get(k, "—")))

    return bytes(pdf.output(dest="S").encode("latin-1", "replace"))

def draft_resumen(lead, answers):
    resumen = f"""Contexto del cliente:
- Empresa: {lead.get('empresa','')}
- Contacto: {lead.get('nombre','')} | {lead.get('correo','')} | {lead.get('telefono','')}

Objetivos de negocio:
{answers.get('objetivos','—')}

Problema a resolver:
{answers.get('problema','—')}

Propuesta de solución (esperada):
{answers.get('solucion','—')}

Usuarios / TARGET:
{answers.get('target','—')}

Alcance funcional (inicial):
{answers.get('funcionalidades','—')}

Expectativas de éxito:
{answers.get('expectativas','—')}

Riesgos y antecedentes:
{answers.get('experiencia','—')}

Procurement:
- Adjudicación: {answers.get('adjudicacion','—')}
- Criterios: {answers.get('criterios','—')}

Fechas y presupuesto:
- Lanzamiento: {answers.get('fecha_lanzamiento','—')}
- Presupuesto: {answers.get('presupuesto','—')}

Nombre de proyecto:
{answers.get('nombre_proyecto','—')}

Notas:
{answers.get('notas','—')}
"""
    return resumen

def ai_rewrite_resumen(lead, answers):
    prompt = f"""
Eres consultor de preventa. Reescribe, resume y mejora el siguiente borrador en un tono ejecutivo, claro y orientado a decisión:

{draft_resumen(lead, answers)}
"""
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            messages=[
                {"role":"system","content":"Eres consultor de preventa B2B. Respondes claro y conciso en español."},
                {"role":"user","content":prompt}
            ]
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return draft_resumen(lead, answers)

# ========= Crawler & Competencia =========
DEFAULT_COMP = {
    "Babel": [
        "https://babelgroup.com/",            # <— cambia si tu dominio es otro
    ],
    "Accenture": [
        "https://www.accenture.com/",
    ],
    "Deloitte": [
        "https://www2.deloitte.com/",
    ],
}

def fetch_url(url: str, timeout=15) -> str:
    try:
        headers = {"User-Agent":"Mozilla/5.0 (compatible; BabelAgent/1.0)"}
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        # quita scripts/estilos
        for s in soup(["script","style","noscript"]):
            s.decompose()
        text = " ".join(t.get_text(separator=" ", strip=True) for t in soup.find_all(["h1","h2","h3","p","li"]))
        text = clean_text(text)
        return text[:20000]  # límite sano
    except Exception:
        return ""

def build_competitive_brief(kb: dict, lead, answers) -> str:
    """
    Si hay API -> pide comparación y posicionamiento.
    Sin API -> arma comparativo básico por keywords.
    """
    # Texto agregado
    corpus = []
    for comp, docs in kb.items():
        combined = "\n\n".join(docs)
        corpus.append(f"### {comp}\n{combined[:5000]}")  # límite por comp
    comp_text = "\n\n".join(corpus) if corpus else ""

    # Si no hay nada, salimos
    if not comp_text.strip():
        return ""

    if USE_AI:
        prompt = f"""
Contexto del cliente:
- Objetivos: {answers.get('objetivos','')}
- Problema: {answers.get('problema','')}
- Solución esperada: {answers.get('solucion','')}
- Funcionalidades: {answers.get('funcionalidades','')}
- Presupuesto: {answers.get('presupuesto','')}

A partir del siguiente contenido de sitios públicos (Babel y competidores), 
haz 1) un breve comparativo (3-5 bullets) y 2) una propuesta de solución donde 
Babel quede bien posicionado y con diferenciadores claros. Escribe en español:

{comp_text}
"""
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.4,
                messages=[
                    {"role":"system","content":"Eres un consultor competitivo. Das comparativos claros y propuesta ganadora para Babel."},
                    {"role":"user","content":prompt}
                ]
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            pass

    # --- Modo básico sin IA ---
    bullets = []
    for comp, docs in kb.items():
        text = " ".join(docs).lower()
        # heurística tontita por palabras clave
        score_ai = sum(text.count(k) for k in ["ai","ia","inteligencia artificial","ml"])
        score_cloud = sum(text.count(k) for k in ["cloud","nube","azure","aws","gcp"])
        score_data = sum(text.count(k) for k in ["data","datos","analytics","bi"])
        focus = []
        if score_ai: focus.append("IA/ML")
        if score_cloud: focus.append("Cloud")
        if score_data: focus.append("Data/Analytics")
        focus_txt = ", ".join(focus) if focus else "servicios generales"
        bullets.append(f"- **{comp}**: fuerte presencia en {focus_txt}.")
    bullets_txt = "\n".join(bullets)

    propuesta = f"""**Resumen competitivo (básico):**
{bullets_txt}

**Propuesta Babel:**
- Enfocar la solución en resultados de negocio ligados a los objetivos del cliente.
- Diferenciar con aceleradores propios (plantillas, conectores, assets) y acompañamiento end-to-end.
- Roadmap en 2 fases: MVP en 6–8 semanas y escalamiento con analítica/IA aplicada a KPIs.
"""
    return propuesta

# ========= APP =========
st.set_page_config(page_title="Calificación + Caso + Competidores", layout="wide")
ensure_state()

st.title("2) Calificación del Lead + Caso de Negocio + Competencia")

# ===== A) Calificación =====
st.subheader("A) Calificación (20/30/30/5/5)")
colL, colR = st.columns([1,1])

with colL:
    st.caption("Ninguna respuesta viene marcada por defecto.")
    q1 = st.radio("¿Tiene fecha planeada para iniciar proyecto?", ["Sí","No"], index=None, key="q1")
    q2 = st.radio("¿Cuenta con presupuesto?", ["Sí","No"], index=None, key="q2")
    q3 = st.radio("¿Es un proyecto para incrementar ventas o marketing?", ["Sí","No"], index=None, key="q3")
    q4 = st.radio("¿El proyecto resuelve un problema de prioridad 1, 2 o 3?", ["Sí","No"], index=None, key="q4")
    q5 = st.radio("¿Hablamos con tomador de decisión?", ["Sí","No"], index=None, key="q5")

with colR:
    pesos = {"q1":20, "q2":30, "q3":30, "q4":5, "q5":5}
    puntos = 0
    total = sum(pesos.values())
    detail = {}
    for k in ["q1","q2","q3","q4","q5"]:
        val = st.session_state.get(k, None)
        ok = (val == "Sí")
        pts = pesos[k] if ok else 0 if val == "No" else 0
        detail[k] = {"respuesta": val, "puntos": pts}
        puntos += pts
    pct = (puntos/total)*100 if total else 0
    st.metric("Puntuación", f"{puntos} / {total}")
    st.metric("Porcentaje", f"{pct:.0f}%")
    st.session_state["score_raw"] = puntos
    st.session_state["score_pct"] = pct
    st.session_state["score_detail"] = detail
    if pct >= 70:
        st.success("✅ Proyecto viable. Puedes pasar al chat y a la inteligencia competitiva.")
    else:
        st.warning("⚠️ Aún no alcanza 70%.")

st.divider()

# ===== B) Chat para armar el Caso =====
st.subheader("B) Caso de Negocio (chat guiado)")
st.caption("Responde en el chat. El asistente hará preguntas hasta completar el caso.")

with st.expander("Editar campos manualmente (opcional)"):
    c = st.session_state["case_answers"]
    col1, col2 = st.columns(2)
    with col1:
        set_answer("objetivos", st.text_area("Objetivos de negocio", value=c.get("objetivos",""), height=100))
        set_answer("problema", st.text_area("Problema a resolver", value=c.get("problema",""), height=100))
        set_answer("solucion", st.text_area("Solución esperada", value=c.get("solucion",""), height=100))
        set_answer("target", st.text_area("Usuarios/TARGET", value=c.get("target",""), height=100))
        set_answer("funcionalidades", st.text_area("Funcionalidades", value=c.get("funcionalidades",""), height=100))
        set_answer("expectativas", st.text_area("Expectativas", value=c.get("expectativas",""), height=100))
    with col2:
        set_answer("experiencia", st.text_area("Experiencia previa", value=c.get("experiencia",""), height=100))
        set_answer("adjudicacion", st.text_area("Forma de adjudicación", value=c.get("adjudicacion",""), height=100))
        set_answer("criterios", st.text_area("Criterios de evaluación", value=c.get("criterios",""), height=100))
        set_answer("fecha_lanzamiento", st.text_input("Fecha de lanzamiento", value=c.get("fecha_lanzamiento","")))
        set_answer("presupuesto", st.text_input("Rango de presupuesto", value=c.get("presupuesto","")))
        set_answer("nombre_proyecto", st.text_input("Nombre del proyecto", value=c.get("nombre_proyecto","")))
        set_answer("notas", st.text_area("Notas generales", value=c.get("notas",""), height=100))

chat_box = st.container()
with chat_box:
    for role, content in st.session_state["chat_history"]:
        (st.chat_message("assistant") if role=="assistant" else st.chat_message("user")).write(content)

    if st.session_state["score_pct"] < 70:
        st.info("Primero alcanza ≥ 70% en la calificación para continuar con el chat.")
    else:
        pending = next_question_key()
        if pending:
            qtxt = question_text(pending)
            st.chat_message("assistant").write(qtxt)
            user_msg = st.chat_input("Escribe tu respuesta…")
            if user_msg:
                st.session_state["chat_history"].append(("assistant", qtxt))
                st.session_state["chat_history"].append(("user", user_msg))
                set_answer(pending, user_msg)
                st.rerun()
        else:
            st.success("¡Listo! Caso de negocio completo.")
            st.session_state["case_done"] = True

st.divider()

# ===== C) Inteligencia Competitiva (crawler + comparativa) =====
st.subheader("C) Inteligencia Competitiva")
st.caption("Agrega URLs de Babel y competidores. Analizamos y generamos una propuesta comparativa.")

# URLs por empresa
with st.expander("URLs sugeridas (puedes editar/agregar)"):
    # Inicializamos con defaults si no existen
    if "comp_urls" not in st.session_state:
        st.session_state["comp_urls"] = {k: "\n".join(v) for k, v in DEFAULT_COMP.items()}
    comp_urls = st.session_state["comp_urls"]

    cols = st.columns(3)
    empresas = list(comp_urls.keys())
    # Asegura siempre Babel
    if "Babel" not in comp_urls:
        comp_urls["Babel"] = "https://babelgroup.com/"

    # Render dinámico
    rendered = {}
    for name in list(comp_urls.keys()):
        rendered[name] = st.text_area(f"{name} – URLs (una por línea)", comp_urls[name], height=140)

    # Agregar otra empresa
    new_name = st.text_input("Añadir otra empresa (opcional)")
    if new_name:
        rendered[new_name] = st.text_area(f"{new_name} – URLs (una por línea)", "", height=80)

    # Guardar cambios
    if st.button("Guardar URLs"):
        st.session_state["comp_urls"] = rendered
        st.success("URLs actualizadas.")

# Analizar competencia
if st.button("🔎 Analizar competencia"):
    kb = {}
    for comp, urls_blob in st.session_state["comp_urls"].items():
        docs = []
        for url in [u.strip() for u in urls_blob.splitlines() if u.strip()]:
            txt = fetch_url(url)
            if txt:
                docs.append(txt)
        if docs:
            kb[comp] = docs
    st.session_state["comp_kb"] = kb
    if kb:
        brief = build_competitive_brief(kb, st.session_state.get("lead_info", {}), st.session_state["case_answers"])
        st.session_state["comp_brief"] = brief
        st.success("Análisis competitivo generado.")
    else:
        st.warning("No se pudo obtener contenido de las URLs (o no se ingresaron).")

# Mostrar comparativo
if st.session_state.get("comp_brief"):
    st.markdown("#### Resultado competitivo")
    st.write(st.session_state["comp_brief"])

st.divider()

# ===== D) Resumen + PDF =====
lead = st.session_state.get("lead_info", {})
answers = st.session_state["case_answers"]

left, right = st.columns([2,1])
with left:
    st.subheader("Resumen Ejecutivo (auto)")
    if st.toggle("Usar IA para redactar mejor (si hay API Key)", value=False) and USE_AI:
        resumen = ai_rewrite_resumen(lead, answers)
    else:
        resumen = draft_resumen(lead, answers)
    # Si hay competencia, añade un cabezal
    if st.session_state.get("comp_brief"):
        resumen = resumen + "\n\n---\n**Inteligencia Competitiva (resumen):**\n" + st.session_state["comp_brief"]

    st.text_area("Vista previa del resumen", value=resumen, height=320)

with right:
    st.subheader("Exportar PDF")
    ready = st.session_state["score_pct"] >= 70 and st.session_state["case_done"]
    if not ready:
        st.info("Necesitas ≥ 70% y terminar el caso de negocio para habilitar el PDF.")
    else:
        if st.button("📄 Generar PDF"):
            try:
                pdf_bytes = render_pdf_bytes(
                    lead,
                    st.session_state["score_pct"],
                    answers,
                    resumen,
                    st.session_state.get("comp_brief","")
                )
                st.session_state["pdf_bytes"] = pdf_bytes
            except Exception as e:
                st.error(f"Error al generar PDF: {e}")

        if st.session_state.get("pdf_bytes"):
            st.download_button(
                "⬇️ Descargar PDF",
                data=st.session_state["pdf_bytes"],
                file_name="Caso_de_Negocio_Babel.pdf",
                mime="application/pdf",
            )

# Progreso general del caso
total_fields = 13
filled = sum(1 for v in answers.values() if v)
st.progress(int((filled/total_fields)*100))
st.caption(f"Campos completados: {filled}/{total_fields}")
