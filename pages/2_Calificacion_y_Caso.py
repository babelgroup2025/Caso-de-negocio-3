# pages/2_Calificacion_y_Caso.py
import os, re, json
import streamlit as st
from fpdf import FPDF
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

st.set_page_config(page_title="Calificación + Caso + Competencia", page_icon="✅", layout="wide")

# ======================= OpenAI opcional =======================
def get_openai_client():
    try:
        from openai import OpenAI
        api_key = st.secrets.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return None
        return OpenAI(api_key=api_key)
    except Exception:
        return None

def llm_complete(prompt: str, temperature: float = 0.35, max_tokens: int = 900):
    client = get_openai_client()
    if client is None:
        return None
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role":"system","content":"Eres consultor de preventa senior. Redacta claro y conciso en español."},
                {"role":"user","content":prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        st.info(f"(IA opcional) No se pudo invocar OpenAI: {e}")
        return None

# ======================= Estado =======================
st.session_state.setdefault("lead", {})
st.session_state.setdefault("score_pct", 0)
st.session_state.setdefault("case_answers", {})
st.session_state.setdefault("chat_history", [])
st.session_state.setdefault("case_done", False)
st.session_state.setdefault("comp_urls", ["https://babelgroup.com","https://www.accenture.com","https://www.ibm.com/consulting"])
st.session_state.setdefault("comp_kb", {})
st.session_state.setdefault("comp_brief", "")
st.session_state.setdefault("pdf_bytes", None)

# ======================= Utils =======================
REQUIRED_FIELDS = [
    ("objetivos", "¿Cuáles son los objetivos de negocio?"),
    ("problema", "¿Cuál es el problema a resolver?"),
    ("solucion", "¿Cuál es la solución esperada?"),
    ("target", "¿Quién va a utilizar la solución? (TARGET)"),
    ("funcionalidades", "¿Qué funcionalidades espera tener?"),
    ("expectativas", "¿Qué expectativas tiene con esta solución?"),
    ("experiencia", "¿Ha tenido experiencia previa similar?"),
    ("adjudicacion", "¿Cuál es la forma de adjudicación?"),
    ("criterios", "¿Cuáles son los criterios de evaluación?"),
    ("fecha_lanzamiento", "¿Cuál sería la fecha de lanzamiento?"),
    ("presupuesto", "¿Cuál es el rango del presupuesto?"),
    ("nombre_proyecto", "¿Nombre del proyecto?"),
    ("notas", "¿Notas generales?")
]

def extract_info_es(text: str) -> dict:
    """Heurísticas simples para autocompletar campos desde texto libre."""
    t = text.lower()
    out = {}
    # presupuesto ($, k, m, millones, MXN, USD)
    m = re.search(r'(\$?\s?\d[\d\.,]*\s*(k|mil|m|mm|millones|usd|mxn)?)', t)
    if m: out["presupuesto"] = m.group(0)
    # fecha (meses, Qx, años, dd/mm/aaaa)
    f = re.search(r'(q[1-4]\s*\d{4}|ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic|\d{1,2}/\d{1,2}/\d{2,4}|20\d{2})', t)
    if f: out["fecha_lanzamiento"] = f.group(0)
    # gatillos
    if any(w in t for w in ["objetivo","meta","kpi","resultado de negocio"]): out["objetivos"] = text
    if any(w in t for w in ["problema","pain","dolor","barrera"]): out["problema"] = text
    if any(w in t for w in ["solución","solucion","implement","implantar"]): out["solucion"] = text
    if any(w in t for w in ["usuario","usuarios","target","ventas","marketing","finanzas","operaciones"]): out["target"] = text
    if any(w in t for w in ["funcionalidad","módulo","modulo","feature"]): out["funcionalidades"] = text
    if any(w in t for w in ["espera","éxito","exito","kpi","resultado"]): out["expectativas"] = text
    if any(w in t for w in ["experiencia","poc","piloto","antes hicimos"]): out["experiencia"] = text
    if any(w in t for w in ["adjudic","licitación","cotización","rfp","rfi"]): out["adjudicacion"] = text
    if any(w in t for w in ["criterio","evaluación","score","ponderación"]): out["criterios"] = text
    if any(w in t for w in ["se llamará","nombre del proyecto","codename"]): out["nombre_proyecto"] = text
    if any(w in t for w in ["nota","riesgo","aclaración","consideración"]): out["notas"] = text
    return out

def first_missing(answers: dict):
    for k, q in REQUIRED_FIELDS:
        if not str(answers.get(k,"")).strip():
            return k, q
    return None, None

def clean_text(s: str) -> str:
    if not s: return ""
    return s.replace("\u200b"," ").replace("\u00A0"," ").replace("\r"," ").replace("\t"," ")

# ======================= Encabezado + Tabs =======================
st.title("2) Calificación + Caso (chat) + Competencia")

tabA, tabB, tabC = st.tabs(["A) Calificación", "B) Caso (chat inteligente)", "C) Competencia & PDF"])

# ======================= A) CALIFICACIÓN =======================
with tabA:
    st.subheader("Calificación del lead (20/30/30/5/5)")
    st.caption("Debes alcanzar **≥ 70%** para habilitar el chat del caso.")

    c1, c2 = st.columns(2)
    q1 = c1.radio("¿Tiene fecha planeada para iniciar proyecto?", ["Sí","No"], index=None, horizontal=True)
    q2 = c2.radio("¿Cuenta con presupuesto?", ["Sí","No"], index=None, horizontal=True)
    q3 = c1.radio("¿Es un proyecto para incrementar ventas o marketing?", ["Sí","No"], index=None, horizontal=True)
    q4 = c2.radio("¿El proyecto resuelve un problema de prioridad 1, 2 o 3?", ["Sí","No"], index=None, horizontal=True)
    q5 = c1.radio("¿Hablamos con tomador de decisión?", ["Sí","No"], index=None, horizontal=True)

    pesos = {"q1":20,"q2":30,"q3":30,"q4":5,"q5":5}  # total 90
    responded = all(x in ("Sí","No") for x in [q1,q2,q3,q4,q5])
    if responded:
        puntos = (pesos["q1"] if q1=="Sí" else 0) + (pesos["q2"] if q2=="Sí" else 0) + \
                 (pesos["q3"] if q3=="Sí" else 0) + (pesos["q4"] if q4=="Sí" else 0) + \
                 (pesos["q5"] if q5=="Sí" else 0)
        pct = round((puntos/90)*100)
        st.session_state["score_pct"] = pct
        st.progress(pct/100)
        st.metric("Porcentaje", f"{pct}%")
        if pct >= 70:
            st.success("✅ Proyecto viable (≥ 70%). Abre la pestaña **B)** para el chat del caso.")
        else:
            st.warning("⚠️ Aún no alcanza 70%. Ajusta respuestas.")
    else:
        st.info("Responde las 5 preguntas para calcular la calificación.")

# ======================= B) CASO (CHAT) =======================
with tabB:
    if st.session_state["score_pct"] < 70:
        st.warning("Primero alcanza **≥ 70%** en la pestaña **A)** para desbloquear el chat.")
    else:
        st.subheader("Chat inteligente para construir el caso")
        st.caption("Habla en texto libre; extraigo lo importante y te pregunto solo lo que falta.")

        # Mensaje inicial
        if not st.session_state["chat_history"]:
            st.session_state["chat_history"].append(("assistant",
                f"Hola 👋 Construyamos el caso para **{st.session_state['lead'].get('empresa','tu empresa')}**. "
                "Cuéntame primero **objetivos de negocio** y **problema a resolver**.")
            )

        # Historial
        for role, content in st.session_state["chat_history"]:
            st.chat_message(role).write(content)

        # Input
        user_msg = st.chat_input("Escribe tu mensaje…")
        if user_msg:
            st.session_state["chat_history"].append(("user", user_msg))
            # autocompletar con reglas
            updates = extract_info_es(user_msg)
            for k, v in updates.items():
                if not st.session_state["case_answers"].get(k):
                    st.session_state["case_answers"][k] = user_msg if k not in ("presupuesto","fecha_lanzamiento") else v

            # decidir siguiente pregunta
            pending_key, next_q = first_missing(st.session_state["case_answers"])
            if pending_key:
                prefix = ""
                if updates:
                    found_labels = [lbl for (kk,lbl) in REQUIRED_FIELDS if kk in updates]
                    if found_labels:
                        prefix = "Anotado: " + "; ".join([lbl.replace("¿","").replace("?","") for lbl in found_labels]) + ". "
                bot = prefix + next_q
            else:
                bot = "¡Perfecto! Ya tenemos todo el caso. Revisa el **resumen** abajo y pasa a **C) Competencia & PDF**."
                st.session_state["case_done"] = True
            st.session_state["chat_history"].append(("assistant", bot))
            st.rerun()

        # Resumen en vivo / edición rápida
        st.markdown("#### Resumen en vivo (editable)")
        cols = st.columns(2)
        for i,(k,label) in enumerate(REQUIRED_FIELDS):
            with cols[i%2]:
                st.session_state["case_answers"][k] = st.text_area(
                    label.replace("¿","").replace("?",""),
                    value=st.session_state["case_answers"].get(k,""), height=80
                )

# ======================= C) COMPETENCIA & PDF =======================
with tabC:
    st.subheader("Competencia (crawler + comparativa) y PDF")

    # ------------ URLs ------------
    st.caption("Agrega URLs de Babel y competidores (una por línea).")
    urls_txt = st.text_area("URLs", value="\n".join(st.session_state["comp_urls"]), height=120)
    st.session_state["comp_urls"] = [u.strip() for u in urls_txt.splitlines() if u.strip()]

    # ------------ Crawler básico ------------
    def fetch_url(url: str, timeout=15) -> str:
        try:
            headers = {"User-Agent":"Mozilla/5.0 (BabelAgent/1.0)"}
            r = requests.get(url, timeout=timeout, headers=headers)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            for s in soup(["script","style","noscript"]): s.decompose()
            text = " ".join(t.get_text(" ", strip=True) for t in soup.find_all(["h1","h2","h3","p","li"]))
            text = clean_text(text)
            return text[:20000]
        except Exception:
            return ""

    def build_comp_brief(kb: dict, case: dict) -> str:
        # Si hay OpenAI, pedimos comparativa y propuesta
        comp_text = []
        for comp, docs in kb.items():
            merged = "\n\n".join(docs)[:5000]
            comp_text.append(f"### {comp}\n{merged}")
        comp_text = "\n\n".join(comp_text)

        if comp_text.strip():
            prompt = f"""
Eres consultor competitivo. Con el siguiente contenido de sitios públicos, haz:
1) Comparativo (3–6 bullets) entre Babel y competidores.
2) Propuesta de solución alineada a objetivos del caso, destacando diferenciadores de Babel.

Datos del caso:
{json.dumps(case, ensure_ascii=False, indent=2)}

Contenido:
{comp_text}
"""
            ai = llm_complete(prompt, temperature=0.4)
            if ai: 
                return ai

        # Si no hay IA o no hay contenido, heurística básica
        bullets = []
        for comp, docs in kb.items():
            txt = " ".join(docs).lower()
            score_ai = sum(txt.count(k) for k in ["ia","inteligencia artificial","ml","gpt","modelo"])
            score_cloud = sum(txt.count(k) for k in ["cloud","nube","aws","azure","gcp"])
            score_data = sum(txt.count(k) for k in ["datos","analytics","bi","data"])
            focus = []
            if score_ai: focus.append("IA/ML")
            if score_cloud: focus.append("Cloud")
            if score_data: focus.append("Data/Analytics")
            focus_txt = ", ".join(focus) if focus else "servicios generales"
            bullets.append(f"- **{comp}**: foco en {focus_txt}.")
        propuesta = (
            "**Resumen competitivo (básico):**\n" + "\n".join(bullets) +
            "\n\n**Propuesta Babel:**\n"
            "- Enfocar en resultados de negocio y time-to-value.\n"
            "- Roadmap 2 fases: MVP (6–8 semanas) + escalamiento con IA aplicada a KPIs.\n"
            "- Diferenciadores: aceleradores, conectores, acompañamiento end-to-end."
        )
        return propuesta

    if st.button("🔎 Analizar competencia"):
        kb = {}
        for u in st.session_state["comp_urls"]:
            domain = urlparse(u).netloc.replace("www.","") or u
            txt = fetch_url(u)
            if txt:
                kb.setdefault(domain, []).append(txt)
        st.session_state["comp_kb"] = kb
        if kb:
            st.session_state["comp_brief"] = build_comp_brief(
                kb, st.session_state["case_answers"]
            )
            st.success("Brief competitivo generado.")
        else:
            st.warning("No se pudo extraer contenido de las URLs (o están vacías).")

    if st.session_state.get("comp_brief"):
        st.markdown("#### Resultado competitivo")
        st.write(st.session_state["comp_brief"])

    st.divider()
    # ------------ PDF ------------
    st.subheader("🧾 Generar PDF")

    def render_pdf_bytes(lead, score_pct, answers, comp_brief):
        class PDF(FPDF): pass
        pdf = PDF(format="A4")
        pdf.set_auto_page_break(auto=True, margin=12)
        pdf.add_page()
        font_path = "DejaVuSans.ttf"
        if os.path.exists(font_path):
            pdf.add_font("DejaVu", "", font_path, uni=True)
            pdf.set_font("DejaVu", "", 14)
        else:
            pdf.set_font("Arial", "", 14)

        pdf.cell(0, 10, clean_text("Caso de Negocio – Babel"), ln=1)
        pdf.set_font_size(10)
        lead_line = f"Empresa: {lead.get('empresa','')}  |  Contacto: {lead.get('contacto','')}  |  Email: {lead.get('correo','')}  |  Tel: {lead.get('telefono','')}"
        pdf.multi_cell(0, 6, clean_text(lead_line))
        pdf.ln(2); pdf.set_font_size(12)
        pdf.cell(0, 8, clean_text(f"Calificación del Lead: {score_pct}%"), ln=1)
        pdf.ln(3)

        # Caso
        for title, key in [
            ("Objetivos de negocio","objetivos"),
            ("Problema a resolver","problema"),
            ("Solución esperada","solucion"),
            ("Usuarios / TARGET","target"),
            ("Funcionalidades esperadas","funcionalidades"),
            ("Expectativas","expectativas"),
            ("Experiencia previa","experiencia"),
            ("Forma de adjudicación","adjudicacion"),
            ("Criterios de evaluación","criterios"),
            ("Fecha de lanzamiento","fecha_lanzamiento"),
            ("Rango de presupuesto","presupuesto"),
            ("Nombre del proyecto","nombre_proyecto"),
            ("Notas generales","notas"),
        ]:
            pdf.set_font_size(13); pdf.cell(0, 8, clean_text(title), ln=1)
            pdf.set_font_size(11)
            pdf.multi_cell(0, 6, clean_text(answers.get(key,"—")))
            pdf.ln(1)

        # Competencia
        if comp_brief:
            pdf.set_font_size(13); pdf.cell(0,8, clean_text("Inteligencia Competitiva"), ln=1)
            pdf.set_font_size(11)
            pdf.multi_cell(0, 6, clean_text(comp_brief))

        return bytes(pdf.output(dest="S").encode("latin-1","replace"))

    ready_pdf = st.session_state["score_pct"] >= 70 and all(st.session_state["case_answers"].get(k) for k,_ in REQUIRED_FIELDS)
    if not ready_pdf:
        st.info("Para habilitar PDF: **≥ 70%** y **completar todos** los campos del caso.")
    else:
        if st.button("📄 Generar PDF"):
            try:
                st.session_state["pdf_bytes"] = render_pdf_bytes(
                    st.session_state["lead"],
                    st.session_state["score_pct"],
                    st.session_state["case_answers"],
                    st.session_state.get("comp_brief","")
                )
                st.success("PDF generado.")
            except Exception as e:
                st.error(f"Error al generar PDF: {e}")

        if st.session_state.get("pdf_bytes"):
            st.download_button(
                "⬇️ Descargar PDF",
                data=st.session_state["pdf_bytes"],
                file_name="Caso_de_Negocio_Babel.pdf",
                mime="application/pdf",
            )
