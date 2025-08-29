# pages/4_Desarrollo_y_Pruebas.py
# Fase 4: Desarrollo/Pruebas + Chat con el agente + bandera ready_for_pdf

import os
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="Fase 4 - Desarrollo y Pruebas", layout="wide")
st.title("🛠️ Fase 4: Desarrollo y Pruebas")

# --- Guardas de flujo ---
if not st.session_state.get("evaluacion_ok", False):
    st.warning("La oportunidad no alcanzó 70% en Evaluación. Ve a **Fase 1** y vuelve después.")
    st.stop()

# Estado compartido
st.session_state.setdefault("ready_for_pdf", False)
st.session_state.setdefault("dev_checklist", {
    "casos_uso": False,
    "pruebas": False,
    "riesgos": False,
    "aprobacion": False,
})
st.session_state.setdefault("dev_chat", [])  # historial de chat (lista de dicts role/content)

# === Panel izquierdo: checklist de preparación ===
left, right = st.columns([1, 2], gap="large")

with left:
    st.subheader("Checklist de preparación")
    st.caption("Marca los puntos cuando estén listos. Puedes usar el chat para pedir ayuda.")
    st.session_state["dev_checklist"]["casos_uso"] = st.checkbox("✅ Casos de uso definidos")
    st.session_state["dev_checklist"]["pruebas"] = st.checkbox("✅ Criterios de prueba definidos")
    st.session_state["dev_checklist"]["riesgos"] = st.checkbox("✅ Riesgos y mitigaciones")
    st.session_state["dev_checklist"]["aprobacion"] = st.checkbox("✅ Aprobación interna")

    all_ok = all(st.session_state["dev_checklist"].values())

    st.markdown("---")
    if all_ok:
        st.success("Todo listo en el checklist.")
    else:
        st.info("Completa el checklist para poder marcar **Listo para PDF**.")

    # Botón para marcar listo
    btn = st.button("📄 Marcar **Listo para PDF**")
    if btn:
        if all_ok:
            st.session_state["ready_for_pdf"] = True
            st.success("¡Perfecto! Marcado como **Listo para PDF**. Ahora puedes ir a la **Fase 5**.")
        else:
            st.warning("Aún faltan puntos del checklist antes de marcar **Listo para PDF**.")

    # Estado
    st.metric("Listo para PDF", "Sí" if st.session_state["ready_for_pdf"] else "No")

# === Panel derecho: Chat con el agente ===
with right:
    st.subheader("💬 Chat con el agente (soporte técnico/funcional)")

    # Preparamos cliente OpenAI (manejo seguro de clave)
    api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
    if not api_key:
        st.error("No se encontró `OPENAI_API_KEY` en los Secrets/variables de entorno.")
        st.stop()
    client = OpenAI(api_key=api_key)

    # Contexto del proyecto (lo que traemos de fases anteriores)
    score = st.session_state.get("score_total", 0)
    eval_answers = st.session_state.get("eval_answers", {})
    diseno = st.session_state.get("diseno", {})
    proyectos = st.session_state.get("proyectos", [])

    # Mensaje de sistema con contexto
    system_prompt = f"""
Eres un asistente técnico de Babel. Ayudas a cerrar la Fase 4 (desarrollo/pruebas) del caso de negocio.
Contexto:
- Score de evaluación: {score}%
- Respuestas evaluación: {eval_answers}
- Diseño (si existe): {diseno}
- Proyectos en memoria (si existen): {len(proyectos)} elementos.

Responde de forma concreta, con listas cuando convenga. Si el usuario pide plantillas de pruebas,
proporciona ejemplos de **casos de prueba**, **criterios de aceptación** y **métricas**.
"""

    # Pintamos historial
    with st.container(height=420, border=True):
        if not st.session_state["dev_chat"]:
            st.markdown("> 👇 Escribe tu primera pregunta en el cuadro de abajo.")
        for m in st.session_state["dev_chat"]:
            if m["role"] == "user":
                with st.chat_message("user"):
                    st.write(m["content"])
            else:
                with st.chat_message("assistant"):
                    st.write(m["content"])

    # Entrada de chat
    user_msg = st.chat_input("Pregunta al agente (p.ej. 'dame 5 casos de prueba para el flujo principal')")
    if user_msg:
        # Añadimos el turno del usuario
        st.session_state["dev_chat"].append({"role": "user", "content": user_msg})

        # Construimos el historial para la API (incluye system)
        messages = [{"role": "system", "content": system_prompt}] + st.session_state["dev_chat"]

        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",  # modelo ligero y rápido; puedes cambiar si quieres
                messages=messages,
                temperature=0.3,
            )
            answer = resp.choices[0].message.content.strip()
        except Exception as e:
            answer = f"Hubo un error llamando a la API: {e}"

        st.session_state["dev_chat"].append({"role": "assistant", "content": answer})
        st.rerun()

    # Botón para limpiar chat
    cols = st.columns(2)
    if cols[0].button("🧹 Limpiar chat"):
        st.session_state["dev_chat"] = []
        st.rerun()

    # Guardado opcional de insumos de pruebas al estado (si el usuario copia algo del chat)
    with st.expander("📎 Guardar notas de pruebas en el estado (opcional)"):
        notas = st.text_area("Pega aquí notas/criterios de prueba a conservar", height=140)
        if st.button("Guardar notas en estado"):
            st.session_state["devtest"]["notas"] = notas
            st.success("Notas guardadas en el estado `devtest.notas`. Se incluirán en el PDF si lo deseas.")
