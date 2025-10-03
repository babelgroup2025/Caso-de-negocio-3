import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="Babel · Agente Comercial",
    page_icon="💡",
    layout="wide",
)

# ---------- ESTILOS (únicos) ----------
CUSTOM_CSS = """
<style>
/* Tipografía */
html, body, [class*="css"]  { font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji","Segoe UI Emoji" !important; }

/* Hero */
.hero {
  background: linear-gradient(135deg,#ffb347 0%, #ffcc33 100%);
  border-radius: 18px;
  padding: 28px 28px 24px 28px;
  color: #1a1a1a;
  box-shadow: 0 8px 20px rgba(0,0,0,.08);
  border: 1px solid rgba(0,0,0,.05);
}

/* Chips / badges */
.badge{display:inline-block;padding:4px 10px;border-radius:9999px;font-size:12px;background:#1f2937;color:#fff;margin-right:6px;opacity:.9}
.badge.ok{background:#059669} .badge.warn{background:#b45309} .badge.neutral{background:#334155}

/* Card métrica */
.metric{
  border:1px solid rgba(0,0,0,.06);
  border-radius:14px; padding:14px 16px; background:#fff;
  box-shadow: 0 4px 14px rgba(0,0,0,.05);
}
.metric h3{margin:0 0 8px 0; font-size:14px; color:#6b7280; font-weight:600}
.metric .v{font-size:22px; font-weight:800}

/* Títulos secciones */
h2, h3 { letter-spacing:-.3px }

/* Botón prominente */
button[kind="primary"]{border-radius:10px !important; font-weight:700}

/* Sidebar */
section[data-testid="stSidebar"] {border-right:1px solid #eee}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------- HEADER ----------
colL, colC, colR = st.columns([1,4,2])
with colL:
    st.image("logo_babel.jpeg", width=110, clamp=True) if "logo_babel.jpeg" in st.session_state.get("_assets_", []) or True else st.empty()
with colC:
    st.markdown(f"""
<div class="hero">
  <div style="display:flex;justify-content:space-between;align-items:center">
    <div>
      <div class="badge neutral">Agente Comercial · Babel</div>
      <div class="badge">Memoria</div>
      <div class="badge">Chat guiado</div>
      <div class="badge">Competitividad</div>
      <h1 style="margin:8px 0 0 0; font-size:28px;">Caso de Negocio Inteligente</h1>
      <div style="opacity:.85;font-weight:600">v{datetime.now().strftime("%Y.%m")} · demo</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

with colR:
    # Estado resumido (si existe)
    sc = st.session_state.get("score", 0)
    ready = st.session_state.get("ready_for_case", False)
    st.markdown("<div class='metric'><h3>Score</h3><div class='v'>"
                f"{int(sc)} / 100</div></div>", unsafe_allow_html=True)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown("<div class='metric'><h3>Listo para caso</h3><div class='v'>"
                + ("✅ Sí" if ready else "—") + "</div></div>", unsafe_allow_html=True)

# ---------- SIDEBAR ----------
st.sidebar.title("Navegación")
st.sidebar.page_link("pages/1_Lead_y_Memoria.py", label="1) Lead & Memoria")
st.sidebar.page_link("pages/2_Calificacion_y_Caso.py", label="2) Calificación + Caso & Competencia")
st.sidebar.markdown("---")
st.sidebar.caption("Consejo: completa primero el Lead, luego califica para desbloquear el chat.")

# ---------- CONTENIDO HOME ----------
st.write("")
st.subheader("Cómo funciona")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("**1) Lead & Memoria**  \nCaptura datos del lead y guárdalos. El agente recuerda los leads activos.")
with c2:
    st.markdown("**2) Calificación**  \n5 preguntas ponderadas **20/30/30/10/10**. Con **≥70** se habilita el chat del caso.")
with c3:
    st.markdown("**3) Caso & Competencia**  \nChat guiado para construir el caso y módulo listo para integrar RAG con sitios de competidores.")
