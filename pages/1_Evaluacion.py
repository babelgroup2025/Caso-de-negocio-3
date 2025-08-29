import streamlit as st

st.title("Fase 1: Evaluación de Proyecto")

st.write("Responde las siguientes preguntas para calcular el score:")

q1 = st.radio("¿Tiene fecha planeada para iniciar proyecto?", ["Sí", "No"])
q2 = st.radio("¿Cuenta con presupuesto?", ["Sí", "No"])
q3 = st.radio("¿Es un proyecto para incrementar ventas o marketing?", ["Sí", "No"])
q4 = st.radio("¿El proyecto resuelve un problema de prioridad 1,2 o 3 dentro de la empresa?", ["Sí", "No"])
q5 = st.radio("¿Quién toma la decisión? ¿Hablamos con tomador de decisión?", ["Sí", "No"])

# pesos
score = 0
score += 20 if q1 == "Sí" else 0
score += 30 if q2 == "Sí" else 0
score += 30 if q3 == "Sí" else 0
score += 15 if q4 == "Sí" else 0
score += 5 if q5 == "Sí" else 0

st.subheader(f"Calificación: {score} / 100")

if score >= 70:
    st.success("✅ Proyecto viable, puedes pasar a la siguiente fase")
else:
    st.error("❌ Proyecto no viable aún, no pases a la siguiente fase")
