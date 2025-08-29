# pages/1_Evaluacion.py
# Fase 1: Evaluación (ponderada 20/30/30/5/5) y guardado en session_state

import streamlit as st
from datetime import datetime

st.title("📊 Fase 1: Evaluación de la Oportunidad")
st.caption("Responde las 5 preguntas. Si el puntaje es **≥ 70%** puedes avanzar a la siguiente fase.")

# -------------------- Config / pesos --------------------
PESOS = {
    "q1": 20,  # ¿Tiene fecha planeada para iniciar proyecto?
    "q2": 30,  # ¿Cuenta con presupuesto?
    "q3": 30,  # ¿Es un proyecto para incrementar ventas o marketing?
    "q4": 5,   # ¿El proyecto resuelve un problema de prioridad 1, 2 o 3?
    "q5": 5,   # ¿Hablamos con tomador de decisión?
}
UMBRAL = 70

# -------------------- Estado inicial --------------------
st.session_state.setdefault("eval_answers", {})     # dict con respuestas "Sí"/"No"
st.session_state.setdefault("score_total", 0)       # 0..100
st.session_state.setdefault("evaluacion_ok", False) # True/False
st.session_state.setdefault("eval_timestamp", None) # ISO time

# -------------------- Formulario (envío atómico) --------------------
with st.form("form_eval"):
    st.subheader("Preguntas")

    q1 = st.radio(
        "¿Tiene fecha planeada para iniciar proyecto?",
        ["Sí", "No"],
        index=0 if st.session_state["eval_answers"].get("q1") == "Sí" else 1
        if st.session_state["eval_answers"].get("q1") == "No" else 1,
        key="q1_eval",
        horizontal=True
    )

    q2 = st.radio(
        "¿Cuenta con presupuesto?",
        ["Sí", "No"],
        index=0 if st.session_state["eval_answers"].get("q2") == "Sí" else 1
        if st.session_state["eval_answers"].get("q2") == "No" else 1,
        key="q2_eval",
        horizontal=True
    )

    q3 = st.radio(
        "¿Es un proyecto para incrementar ventas o marketing?",
        ["Sí", "No"],
        index=0 if st.session_state["eval_answers"].get("q3") == "Sí" else 1
        if st.session_state["eval_answers"].get("q3") == "No" else 1,
        key="q3_eval",
        horizontal=True
    )

    q4 = st.radio(
        "¿El proyecto resuelve un problema de prioridad 1, 2 o 3 dentro de tu empresa?",
        ["Sí", "No"],
        index=0 if st.session_state["eval_answers"].get("q4") == "Sí" else 1
        if st.session_state["eval_answers"].get("q4") == "No" else 1,
        key="q4_eval",
        horizontal=True
    )

    q5 = st.radio(
        "¿Quién toma la decisión? ¿Hablamos con tomador de decisión?",
        ["Sí", "No"],
        index=0 if st.session_state["eval_answers"].get("q5") == "Sí" else 1
        if st.session_state["eval_answers"].get("q5") == "No" else 1,
        key="q5_eval",
        horizontal=True
    )

    submitted = st.form_submit_button("Calcular calificación ✅")

# -------------------- Lógica de cálculo --------------------
def calcular_score(respuestas: dict) -> int:
    """Suma de pesos sólo cuando la respuesta es 'Sí'."""
    total = 0
    for clave, peso in PESOS.items():
        if respuestas.get(clave) == "Sí":
            total += peso
    return int(total)

if submitted:
    # Guardar respuestas en un dict limpio
    respuestas = {
        "q1": st.session_state["q1_eval"],
        "q2": st.session_state["q2_eval"],
        "q3": st.session_state["q3_eval"],
        "q4": st.session_state["q4_eval"],
        "q5": st.session_state["q5_eval"],
    }

    score = calcular_score(respuestas)

    # Persistir en session_state (llaves únicas y consistentes para las otras fases)
    st.session_state["eval_answers"] = respuestas
    st.session_state["score_total"] = score
    st.session_state["evaluacion_ok"] = score >= UMBRAL
    st.session_state["eval_timestamp"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"

# -------------------- Resultado / Resumen --------------------
st.divider()
score = st.session_state["score_total"]
st.subheader("Resultado")
col1, col2 = st.columns([1, 2])
with col1:
    st.metric("Calificación", f"{score} / 100")
    st.metric("Estatus", "✅ Viable" if st.session_state["evaluacion_ok"] else "❌ No viable")
with col2:
    st.markdown("**Detalle por pregunta:**")
    detalle = [
        ("q1", "¿Tiene fecha planeada para iniciar proyecto?"),
        ("q2", "¿Cuenta con presupuesto?"),
        ("q3", "¿Es un proyecto para incrementar ventas o marketing?"),
        ("q4", "¿El proyecto resuelve un problema de prioridad 1, 2 o 3?"),
        ("q5", "¿Hablamos con tomador de decisión?"),
    ]
    for clave, texto in detalle:
        r = st.session_state["eval_answers"].get(clave, "No")
        peso = PESOS[clave]
        pts = peso if r == "Sí" else 0
        st.write(f"- {texto} → **{r}** *(peso {peso}, pts {pts})*")

if st.session_state["evaluacion_ok"]:
    st.success("✅ Proyecto viable: puedes pasar a la **Fase 2 (Memoria)**.")
else:
    st.warning(f"Para avanzar necesitas **≥ {UMBRAL}%**. Ajusta respuestas si aplica.")

# -------------------- Utilidades --------------------
col_a, col_b = st.columns([1, 1])
with col_a:
    if st.button("Reiniciar evaluación"):
        st.session_state["eval_answers"] = {}
        st.session_state["score_total"] = 0
        st.session_state["evaluacion_ok"] = False
        st.session_state["eval_timestamp"] = None
        # También reseteamos los widgets de radio
        for k in ["q1_eval", "q2_eval", "q3_eval", "q4_eval", "q5_eval"]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()

with col_b:
    if st.session_state.get("eval_timestamp"):
        st.caption(f"Último cálculo: {st.session_state['eval_timestamp']}")
