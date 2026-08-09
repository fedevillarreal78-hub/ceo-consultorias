import base64
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[1]
STAGING_PATH = BASE_DIR / "candidatos_revision.csv"
MAIN_PATH = BASE_DIR / "oportunidades_consultoria.csv"
GITHUB_OWNER = "fedevillarreal78-hub"
GITHUB_REPO = "ceo-consultorias"
GITHUB_BRANCH = "main"

MAIN_COLUMNS = [
    "Título", "Organización", "Tipo", "Región", "País", "Fecha límite",
    "Enlace", "Afinidad", "Prioridad", "Estado", "Monto estimado (USD)",
    "Consultor", "Observaciones", "Socio vinculado", "Votos descarte",
]

st.set_page_config(page_title="Revisión de candidatos · Grupo CEO", page_icon="🔎", layout="wide")


def get_secret(name):
    value = os.environ.get(name, "")
    if value:
        return value
    try:
        return st.secrets.get(name, "")
    except Exception:
        return ""


def require_password():
    expected = get_secret("REVIEW_PASSWORD")
    if not expected:
        st.warning("La página no tiene REVIEW_PASSWORD configurada. Configure el secret para restringir las decisiones de aprobación y descarte.")
        return
    if st.session_state.get("review_authenticated"):
        return
    password = st.text_input("Contraseña de revisión", type="password")
    if st.button("Ingresar"):
        if password == expected:
            st.session_state.review_authenticated = True
            st.rerun()
        st.error("Contraseña incorrecta")
    st.stop()


def push_file(path, github_path, message):
    token = get_secret("GITHUB_TOKEN")
    if not token:
        return False, "GITHUB_TOKEN no configurado"
    api = "https://api.github.com/repos/{}/{}/contents/{}".format(GITHUB_OWNER, GITHUB_REPO, github_path)
    headers = {"Authorization": "Bearer {}".format(token), "Accept": "application/vnd.github+json"}
    content = base64.b64encode(path.read_bytes()).decode("ascii")
    for _ in range(3):
        current = requests.get(api, headers=headers, params={"ref": GITHUB_BRANCH}, timeout=15)
        sha = current.json().get("sha") if current.status_code == 200 else None
        payload = {"message": message, "content": content, "branch": GITHUB_BRANCH}
        if sha:
            payload["sha"] = sha
        response = requests.put(api, headers=headers, json=payload, timeout=30)
        if response.status_code in (200, 201):
            return True, ""
        if response.status_code != 409:
            return False, "GitHub respondió {}: {}".format(response.status_code, response.text[:300])
    return False, "Conflicto de concurrencia tras tres intentos"


def save_all(staging, main):
    staging.to_csv(STAGING_PATH, index=False)
    main.to_csv(MAIN_PATH, index=False)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    ok1, err1 = push_file(STAGING_PATH, STAGING_PATH.name, "Revisión de candidatos ({})".format(ts))
    ok2, err2 = push_file(MAIN_PATH, MAIN_PATH.name, "Aprobación de oportunidad ({})".format(ts))
    return ok1 and ok2, "; ".join(e for e in [err1, err2] if e)


def main_row(row, note):
    return {
        "Título": row.get("Título", ""), "Organización": row.get("Organización", ""),
        "Tipo": row.get("Tipo", "Ambos"), "Región": row.get("Región", "A verificar"),
        "País": row.get("País", "A verificar"), "Fecha límite": row.get("Fecha límite", "A verificar"),
        "Enlace": row.get("Enlace", ""), "Afinidad": row.get("Afinidad", "Ambos"),
        "Prioridad": row.get("Prioridad", "Media"), "Estado": "Identificada",
        "Monto estimado (USD)": "", "Consultor": "—",
        "Observaciones": "Aprobada desde bandeja de revisión. Fuente: {}. Puntaje: {}. {}".format(
            row.get("Fuente", ""), row.get("Puntaje", ""), note.strip()
        ),
        "Socio vinculado": "", "Votos descarte": "",
    }


require_password()
with st.sidebar:
    if st.button("← Volver al panel principal", use_container_width=True):
        st.switch_page("app.py")

st.title("Revisión de candidatos")
st.caption("Resultados exploratorios o con información incompleta. Nada de esta bandeja ingresa al pipeline sin aprobación humana.")

if not STAGING_PATH.exists():
    st.info("Todavía no existe candidatos_revision.csv. Se creará en la próxima búsqueda.")
    st.stop()

staging = pd.read_csv(STAGING_PATH).fillna("")
main = pd.read_csv(MAIN_PATH).fillna("") if MAIN_PATH.exists() else pd.DataFrame(columns=MAIN_COLUMNS)
pending = staging[staging.get("Estado revisión", "Pendiente") == "Pendiente"].copy()

if pending.empty:
    st.success("No hay candidatos pendientes de revisión.")
    st.stop()

c1, c2, c3 = st.columns(3)
with c1:
    source = st.multiselect("Fuente", sorted(pending["Fuente"].unique()))
with c2:
    min_score = st.slider("Puntaje mínimo", 0, 100, 50)
with c3:
    country = st.multiselect("País", sorted(pending["País"].unique()))

filtered = pending[pd.to_numeric(pending["Puntaje"], errors="coerce").fillna(0) >= min_score]
if source:
    filtered = filtered[filtered["Fuente"].isin(source)]
if country:
    filtered = filtered[filtered["País"].isin(country)]

st.metric("Pendientes filtrados", len(filtered))
st.dataframe(filtered[["Puntaje", "Título", "Organización", "País", "Fecha límite", "Fuente", "Motivos"]], use_container_width=True, hide_index=True)

if filtered.empty:
    st.stop()

labels = {idx: "[{}] {} — {}".format(filtered.loc[idx, "Puntaje"], filtered.loc[idx, "Título"], filtered.loc[idx, "Organización"]) for idx in filtered.index}
selected = st.selectbox("Candidato", list(labels.keys()), format_func=lambda idx: labels[idx])
row = filtered.loc[selected]

st.subheader(row["Título"])
st.write("**Organización:** {}  \n**País/región:** {} / {}  \n**Fecha límite:** {}  \n**Fuente:** {}  \n**Referencia:** {}".format(
    row["Organización"], row["País"], row["Región"], row["Fecha límite"], row["Fuente"], row["Referencia"]
))
st.write(row["Resumen"] or "Sin resumen disponible")
st.markdown("[Abrir fuente oficial]({})".format(row["Enlace"]))
st.warning(row["Motivos"] or "Sin alertas registradas")

note = st.text_area("Nota de decisión")
col_a, col_b, col_c = st.columns(3)
with col_a:
    if st.button("Aprobar e incorporar", type="primary", use_container_width=True):
        main = pd.concat([main, pd.DataFrame([main_row(row, note)])], ignore_index=True)
        staging.loc[selected, "Estado revisión"] = "Aprobada"
        staging.loc[selected, "Motivos"] = (row["Motivos"] + "; Nota: " + note).strip("; ")
        ok, error = save_all(staging, main)
        if ok:
            st.success("Oportunidad incorporada y sincronizada con GitHub.")
            st.rerun()
        st.error(error)
with col_b:
    if st.button("Descartar", use_container_width=True):
        staging.loc[selected, "Estado revisión"] = "Descartada"
        staging.loc[selected, "Motivos"] = (row["Motivos"] + "; Motivo de descarte: " + note).strip("; ")
        staging.to_csv(STAGING_PATH, index=False)
        ok, error = push_file(STAGING_PATH, STAGING_PATH.name, "Descartar candidato ({})".format(datetime.now().strftime("%Y-%m-%d %H:%M")))
        if ok:
            st.success("Candidato descartado.")
            st.rerun()
        st.error(error)
with col_c:
    if st.button("Posponer", use_container_width=True):
        st.info("El candidato permanece pendiente.")
