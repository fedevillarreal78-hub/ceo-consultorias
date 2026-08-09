import base64
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
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

STAGING_COLUMNS = [
    "ID canónico", "Título", "Organización", "Tipo", "Región", "País",
    "Fecha límite", "Enlace", "Afinidad", "Prioridad", "Fuente",
    "Referencia", "Fecha publicación", "Resumen", "Puntaje", "Motivos",
    "Estado revisión", "Detectada",
]


def _secret(name: str) -> str:
    value = os.environ.get(name, "")
    if value:
        return value
    try:
        return st.secrets.get(name, "")
    except Exception:
        return ""


def _push_file(path: Path, github_path: str, message: str):
    token = _secret("GITHUB_TOKEN")
    if not token:
        return False, "GITHUB_TOKEN no está configurado en Streamlit."

    api = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{github_path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    content = base64.b64encode(path.read_bytes()).decode("ascii")

    for _ in range(3):
        current = requests.get(api, headers=headers, params={"ref": GITHUB_BRANCH}, timeout=15)
        sha = current.json().get("sha") if current.status_code == 200 else None
        payload = {
            "message": message,
            "content": content,
            "branch": GITHUB_BRANCH,
        }
        if sha:
            payload["sha"] = sha
        response = requests.put(api, headers=headers, json=payload, timeout=30)
        if response.status_code in (200, 201):
            return True, ""
        if response.status_code != 409:
            return False, f"GitHub respondió {response.status_code}: {response.text[:300]}"

    return False, "Conflicto de concurrencia tras tres intentos."


def _save_all(staging: pd.DataFrame, main: pd.DataFrame):
    staging.to_csv(STAGING_PATH, index=False)
    main.to_csv(MAIN_PATH, index=False)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    ok_staging, err_staging = _push_file(
        STAGING_PATH,
        STAGING_PATH.name,
        f"Revisión de candidatos ({timestamp})",
    )
    ok_main, err_main = _push_file(
        MAIN_PATH,
        MAIN_PATH.name,
        f"Aprobación de oportunidad ({timestamp})",
    )
    errors = "; ".join(error for error in (err_staging, err_main) if error)
    return ok_staging and ok_main, errors


def _main_row(row: pd.Series, note: str):
    return {
        "Título": row.get("Título", ""),
        "Organización": row.get("Organización", ""),
        "Tipo": row.get("Tipo", "Ambos"),
        "Región": row.get("Región", "A verificar"),
        "País": row.get("País", "A verificar"),
        "Fecha límite": row.get("Fecha límite", "A verificar"),
        "Enlace": row.get("Enlace", ""),
        "Afinidad": row.get("Afinidad", "Ambos"),
        "Prioridad": row.get("Prioridad", "Media"),
        "Estado": "Identificada",
        "Monto estimado (USD)": "",
        "Consultor": "—",
        "Observaciones": (
            "Aprobada desde la bandeja de revisión. "
            f"Fuente: {row.get('Fuente', '')}. "
            f"Puntaje: {row.get('Puntaje', '')}. {note.strip()}"
        ).strip(),
        "Socio vinculado": "",
        "Votos descarte": "",
    }


def _ensure_columns(frame: pd.DataFrame, columns):
    result = frame.copy()
    for column in columns:
        if column not in result.columns:
            result[column] = ""
    return result


def render_revision_candidatos():
    """Renderiza la bandeja dentro del panel autenticado de app.py."""
    st.markdown("## 🔎 Revisión de candidatos")
    st.caption(
        "Resultados exploratorios o con información incompleta. "
        "Ningún candidato ingresa al pipeline sin aprobación humana."
    )

    if not STAGING_PATH.exists():
        st.info("Todavía no existe candidatos_revision.csv. Se creará en la próxima búsqueda.")
        return

    try:
        staging = pd.read_csv(STAGING_PATH).fillna("")
    except pd.errors.EmptyDataError:
        staging = pd.DataFrame(columns=STAGING_COLUMNS)
    staging = _ensure_columns(staging, STAGING_COLUMNS)

    if MAIN_PATH.exists():
        try:
            main = pd.read_csv(MAIN_PATH).fillna("")
        except pd.errors.EmptyDataError:
            main = pd.DataFrame(columns=MAIN_COLUMNS)
    else:
        main = pd.DataFrame(columns=MAIN_COLUMNS)
    main = _ensure_columns(main, MAIN_COLUMNS)

    pending = staging[staging["Estado revisión"].replace("", "Pendiente") == "Pendiente"].copy()

    total = len(staging)
    approved = int((staging["Estado revisión"] == "Aprobada").sum())
    discarded = int((staging["Estado revisión"] == "Descartada").sum())
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Pendientes", len(pending))
    m2.metric("Aprobadas", approved)
    m3.metric("Descartadas", discarded)
    m4.metric("Total revisado", total)

    if pending.empty:
        st.success("No hay candidatos pendientes de revisión.")
        st.info("La bandeja se completará cuando se ejecute una nueva búsqueda con fuentes exploratorias.")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        source = st.multiselect(
            "Fuente",
            sorted(value for value in pending["Fuente"].unique() if value),
            key="revision_fuente",
        )
    with c2:
        min_score = st.slider(
            "Puntaje mínimo",
            0,
            100,
            50,
            key="revision_puntaje",
        )
    with c3:
        country = st.multiselect(
            "País",
            sorted(value for value in pending["País"].unique() if value),
            key="revision_pais",
        )

    scores = pd.to_numeric(pending["Puntaje"], errors="coerce").fillna(0)
    filtered = pending[scores >= min_score]
    if source:
        filtered = filtered[filtered["Fuente"].isin(source)]
    if country:
        filtered = filtered[filtered["País"].isin(country)]

    st.metric("Pendientes filtrados", len(filtered))
    display_columns = [
        "Puntaje", "Título", "Organización", "País",
        "Fecha límite", "Fuente", "Motivos",
    ]
    st.dataframe(
        filtered[display_columns],
        use_container_width=True,
        hide_index=True,
    )

    if filtered.empty:
        return

    labels = {
        index: f"[{filtered.loc[index, 'Puntaje']}] "
        f"{filtered.loc[index, 'Título']} — {filtered.loc[index, 'Organización']}"
        for index in filtered.index
    }
    selected = st.selectbox(
        "Candidato",
        list(labels.keys()),
        format_func=lambda index: labels[index],
        key="revision_candidato",
    )
    row = filtered.loc[selected]

    st.markdown(f"### {row['Título']}")
    st.markdown(
        f"**Organización:** {row['Organización']}  \n"
        f"**País/región:** {row['País']} / {row['Región']}  \n"
        f"**Fecha límite:** {row['Fecha límite']}  \n"
        f"**Fuente:** {row['Fuente']}  \n"
        f"**Referencia:** {row['Referencia']}"
    )
    st.write(row["Resumen"] or "Sin resumen disponible.")
    if row["Enlace"]:
        st.link_button("Abrir fuente oficial", row["Enlace"])
    st.warning(row["Motivos"] or "Sin alertas registradas.")

    note = st.text_area("Nota de decisión", key="revision_nota")
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        if st.button(
            "Aprobar e incorporar",
            type="primary",
            use_container_width=True,
            key="revision_aprobar",
        ):
            main = pd.concat([main, pd.DataFrame([_main_row(row, note)])], ignore_index=True)
            staging.loc[selected, "Estado revisión"] = "Aprobada"
            staging.loc[selected, "Motivos"] = (
                f"{row['Motivos']}; Nota: {note}".strip("; ")
            )
            ok, error = _save_all(staging, main)
            if ok:
                st.success("Oportunidad incorporada y sincronizada con GitHub.")
                st.rerun()
            st.error(error)

    with col_b:
        if st.button(
            "Descartar",
            use_container_width=True,
            key="revision_descartar",
        ):
            staging.loc[selected, "Estado revisión"] = "Descartada"
            staging.loc[selected, "Motivos"] = (
                f"{row['Motivos']}; Motivo de descarte: {note}".strip("; ")
            )
            staging.to_csv(STAGING_PATH, index=False)
            ok, error = _push_file(
                STAGING_PATH,
                STAGING_PATH.name,
                f"Descartar candidato ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
            )
            if ok:
                st.success("Candidato descartado.")
                st.rerun()
            st.error(error)

    with col_c:
        if st.button(
            "Posponer",
            use_container_width=True,
            key="revision_posponer",
        ):
            st.info("El candidato permanece pendiente.")
