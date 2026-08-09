"""Bandeja de revisión humana para candidatos exploratorios.

La interfaz está integrada dentro de app.py y usa el mismo esquema de autenticación.
Los cambios se persisten en CSV y, cuando existe GITHUB_TOKEN, se sincronizan con GitHub.
"""
from __future__ import annotations

import base64
import csv
import html
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import pandas as pd
import requests
import streamlit as st

from ceo_theme import apply_ceo_theme

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
    "Estado revisión", "Detectada", "Comentario revisión", "Revisado por",
    "Fecha revisión",
]

ACTIVE_STATUSES = {"", "Pendiente", "Pospuesta"}
FINAL_STATUSES = {"Aprobada", "Descartada"}


def _secret(name: str) -> str:
    value = os.environ.get(name, "")
    if value:
        return value
    try:
        return str(st.secrets.get(name, ""))
    except Exception:
        return ""


def _reviewer() -> str:
    for key in ("usuario", "user", "username", "nombre_usuario", "logged_user"):
        value = st.session_state.get(key)
        if value:
            return str(value)
    return "Federico"


def _ensure_columns(frame: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    result = frame.copy()
    for column in columns:
        if column not in result.columns:
            result[column] = ""
    return result[list(columns)]


def _load_csv(path: Path, columns: Sequence[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=list(columns))
    try:
        frame = pd.read_csv(path, dtype=str).fillna("")
    except (pd.errors.EmptyDataError, UnicodeDecodeError):
        frame = pd.DataFrame(columns=list(columns))
    return _ensure_columns(frame, columns)


def _write_csv(path: Path, frame: pd.DataFrame, columns: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    _ensure_columns(frame, columns).to_csv(temp, index=False)
    temp.replace(path)


def _push_file(path: Path, github_path: str, message: str) -> Tuple[bool, str]:
    token = _secret("GITHUB_TOKEN")
    if not token:
        return False, "GITHUB_TOKEN no está configurado en Streamlit. El cambio quedó guardado solo en la sesión local."

    api = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{github_path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    content = base64.b64encode(path.read_bytes()).decode("ascii")

    for attempt in range(3):
        try:
            current = requests.get(
                api,
                headers=headers,
                params={"ref": GITHUB_BRANCH},
                timeout=20,
            )
            sha = current.json().get("sha") if current.status_code == 200 else None
            payload: Dict[str, str] = {
                "message": message,
                "content": content,
                "branch": GITHUB_BRANCH,
            }
            if sha:
                payload["sha"] = sha
            response = requests.put(api, headers=headers, json=payload, timeout=35)
        except requests.RequestException as exc:
            if attempt == 2:
                return False, f"No se pudo conectar con GitHub: {exc}"
            continue

        if response.status_code in (200, 201):
            return True, ""
        if response.status_code != 409:
            detail = response.text[:350].replace("\n", " ")
            return False, f"GitHub respondió {response.status_code}: {detail}"

    return False, "GitHub informó un conflicto de concurrencia después de tres intentos."


def _normalise(value: str) -> str:
    value = (value or "").lower().strip()
    value = re.sub(r"\s+", " ", value)
    return value


def _is_duplicate(main: pd.DataFrame, row: pd.Series) -> bool:
    if main.empty:
        return False
    link = _normalise(str(row.get("Enlace", "")))
    title = _normalise(str(row.get("Título", "")))
    org = _normalise(str(row.get("Organización", "")))
    for _, existing in main.iterrows():
        if link and _normalise(str(existing.get("Enlace", ""))) == link:
            return True
        if title and org:
            if (
                _normalise(str(existing.get("Título", ""))) == title
                and _normalise(str(existing.get("Organización", ""))) == org
            ):
                return True
    return False


def _main_row(row: pd.Series, note: str) -> Dict[str, str]:
    observations = [
        "Aprobada desde la bandeja de revisión.",
        f"Fuente: {row.get('Fuente', '')}.",
        f"Puntaje automático: {row.get('Puntaje', '')}/100.",
    ]
    if note.strip():
        observations.append(f"Comentario de revisión: {note.strip()}")
    return {
        "Título": str(row.get("Título", "")),
        "Organización": str(row.get("Organización", "")),
        "Tipo": str(row.get("Tipo", "Ambos")) or "Ambos",
        "Región": str(row.get("Región", "A verificar")) or "A verificar",
        "País": str(row.get("País", "A verificar")) or "A verificar",
        "Fecha límite": str(row.get("Fecha límite", "A verificar")) or "A verificar",
        "Enlace": str(row.get("Enlace", "")),
        "Afinidad": str(row.get("Afinidad", "Alineación general con Grupo CEO")),
        "Prioridad": str(row.get("Prioridad", "Media")) or "Media",
        "Estado": "Identificada",
        "Monto estimado (USD)": "",
        "Consultor": "—",
        "Observaciones": " ".join(observations).strip(),
        "Socio vinculado": "",
        "Votos descarte": "",
    }


def _save_decision(
    staging: pd.DataFrame,
    main: pd.DataFrame,
    push_main: bool,
    action: str,
) -> Tuple[bool, str]:
    _write_csv(STAGING_PATH, staging, STAGING_COLUMNS)
    if push_main:
        _write_csv(MAIN_PATH, main, MAIN_COLUMNS)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    ok_stage, err_stage = _push_file(
        STAGING_PATH,
        STAGING_PATH.name,
        f"Revisión de candidato: {action} ({timestamp})",
    )
    if not ok_stage:
        return False, err_stage

    if push_main:
        ok_main, err_main = _push_file(
            MAIN_PATH,
            MAIN_PATH.name,
            f"Incorporar oportunidad aprobada ({timestamp})",
        )
        if not ok_main:
            return False, err_main

    return True, ""


def _status_series(frame: pd.DataFrame) -> pd.Series:
    return frame["Estado revisión"].replace("", "Pendiente")


def _candidate_key(row: pd.Series, index: int) -> str:
    canonical = str(row.get("ID canónico", "")).strip()
    return canonical or f"fila-{index}"


def _safe(value: object) -> str:
    return html.escape(str(value or ""))


def _candidate_label(row: pd.Series) -> str:
    score = str(row.get("Puntaje", "—")) or "—"
    title = str(row.get("Título", "Sin título"))[:110]
    org = str(row.get("Organización", "A verificar"))[:60]
    country = str(row.get("País", "A verificar"))[:35]
    return f"{score}/100 · {title} · {org} · {country}"


def _render_candidate_card(row: pd.Series) -> None:
    score = _safe(row.get("Puntaje", "—"))
    title = _safe(row.get("Título", "Sin título"))
    org = _safe(row.get("Organización", "A verificar"))
    country = _safe(row.get("País", "A verificar"))
    region = _safe(row.get("Región", "A verificar"))
    deadline = _safe(row.get("Fecha límite", "A verificar"))
    source = _safe(row.get("Fuente", "A verificar"))
    affinity = _safe(row.get("Afinidad", "A verificar"))
    reference = _safe(row.get("Referencia", ""))
    summary = _safe(row.get("Resumen", "Sin resumen disponible."))
    reasons = _safe(row.get("Motivos", "Sin alertas registradas."))

    st.markdown(
        f"""
        <div class="ceo-candidate-card">
          <div class="ceo-kicker">Puntaje {score}/100 · {source}</div>
          <h3 style="margin:.35rem 0 .4rem 0">{title}</h3>
          <div class="ceo-muted"><strong>{org}</strong> · {country} / {region}</div>
          <div style="margin-top:.65rem"><strong>Fecha límite:</strong> {deadline}</div>
          <div><strong>Línea de trabajo:</strong> {affinity}</div>
          <div><strong>Referencia:</strong> {reference or 'No identificada'}</div>
          <p style="margin-top:.9rem">{summary}</p>
          <div style="background:#F4FAF6;border-radius:8px;padding:10px 12px;margin-top:.8rem">
            <strong>Alertas automáticas:</strong> {reasons}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    link = str(row.get("Enlace", "")).strip()
    if link:
        st.link_button("Abrir convocatoria original", link, use_container_width=False)


def _filter_active(frame: pd.DataFrame) -> pd.DataFrame:
    status = _status_series(frame)
    return frame[status.isin(ACTIVE_STATUSES)].copy()


def render_revision_candidatos() -> None:
    """Renderiza la bandeja dentro del panel autenticado de app.py."""
    apply_ceo_theme()
    st.markdown(
        """
        <div class="ceo-section-header">
          <h2>Revisión de candidatos</h2>
          <p>Validación humana de oportunidades exploratorias antes de incorporarlas al pipeline de Grupo CEO.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    staging = _load_csv(STAGING_PATH, STAGING_COLUMNS)
    main = _load_csv(MAIN_PATH, MAIN_COLUMNS)
    statuses = _status_series(staging) if not staging.empty else pd.Series(dtype=str)

    pending_count = int(statuses.isin({"Pendiente", ""}).sum()) if not staging.empty else 0
    postponed_count = int((statuses == "Pospuesta").sum()) if not staging.empty else 0
    approved_count = int((statuses == "Aprobada").sum()) if not staging.empty else 0
    discarded_count = int((statuses == "Descartada").sum()) if not staging.empty else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Pendientes", pending_count)
    m2.metric("Pospuestas", postponed_count)
    m3.metric("Aprobadas", approved_count)
    m4.metric("Descartadas", discarded_count)

    tab_review, tab_history = st.tabs(["Revisar", "Historial"])

    with tab_review:
        active = _filter_active(staging)
        if active.empty:
            st.success("No hay candidatos pendientes de revisión.")
            st.info(
                "La bandeja se completará cuando se ejecute una nueva búsqueda con fuentes exploratorias. "
                "Las oportunidades aceptadas automáticamente continúan directamente al pipeline."
            )
        else:
            with st.expander("Filtros", expanded=False):
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    source_options = sorted(v for v in active["Fuente"].unique() if str(v).strip())
                    sources = st.multiselect("Fuente", source_options, key="revision_filter_source")
                with c2:
                    country_options = sorted(v for v in active["País"].unique() if str(v).strip())
                    countries = st.multiselect("País", country_options, key="revision_filter_country")
                with c3:
                    status_options = ["Pendiente", "Pospuesta"]
                    selected_status = st.multiselect(
                        "Estado",
                        status_options,
                        default=status_options,
                        key="revision_filter_status",
                    )
                with c4:
                    min_score = st.slider("Puntaje mínimo", 0, 100, 45, key="revision_filter_score")

            filtered = active.copy()
            filtered_scores = pd.to_numeric(filtered["Puntaje"], errors="coerce").fillna(0)
            filtered = filtered[filtered_scores >= min_score]
            if sources:
                filtered = filtered[filtered["Fuente"].isin(sources)]
            if countries:
                filtered = filtered[filtered["País"].isin(countries)]
            if selected_status:
                filtered_status = _status_series(filtered)
                filtered = filtered[filtered_status.isin(selected_status)]

            st.caption(f"{len(filtered)} candidatos cumplen los filtros seleccionados.")

            if filtered.empty:
                st.warning("No hay candidatos que coincidan con estos filtros.")
            else:
                key_to_index: Dict[str, int] = {}
                options: List[str] = []
                for idx, row in filtered.iterrows():
                    key = _candidate_key(row, int(idx))
                    key_to_index[key] = int(idx)
                    options.append(key)

                selected_key = st.session_state.get("revision_selected_candidate")
                if selected_key not in options:
                    st.session_state["revision_selected_candidate"] = options[0]

                selected_key = st.selectbox(
                    "Elegí el candidato que querés revisar",
                    options,
                    format_func=lambda key: _candidate_label(filtered.loc[key_to_index[key]]),
                    key="revision_selected_candidate",
                )
                selected_index = key_to_index[selected_key]
                row = filtered.loc[selected_index]
                _render_candidate_card(row)

                existing_comment = str(row.get("Comentario revisión", ""))
                with st.form("revision_decision_form", clear_on_submit=False):
                    action = st.radio(
                        "Decisión",
                        ["Aprobar e incorporar", "Posponer", "Descartar"],
                        horizontal=True,
                        key=f"revision_action_{selected_key}",
                    )
                    note = st.text_area(
                        "Comentario de revisión",
                        value=existing_comment,
                        placeholder="Fundamento de la decisión, aspectos a verificar o instrucciones para el equipo.",
                        height=120,
                        key=f"revision_comment_{selected_key}",
                    )
                    submitted = st.form_submit_button(
                        "Guardar decisión",
                        type="primary",
                        use_container_width=True,
                    )

                if submitted:
                    if action == "Descartar" and len(note.strip()) < 5:
                        st.error("Para descartar, agregá un comentario breve que fundamente la decisión.")
                    else:
                        now = datetime.now().strftime("%Y-%m-%d %H:%M")
                        reviewer = _reviewer()
                        staging.loc[selected_index, "Comentario revisión"] = note.strip()
                        staging.loc[selected_index, "Revisado por"] = reviewer
                        staging.loc[selected_index, "Fecha revisión"] = now
                        push_main = False

                        if action == "Aprobar e incorporar":
                            staging.loc[selected_index, "Estado revisión"] = "Aprobada"
                            if not _is_duplicate(main, row):
                                main = pd.concat(
                                    [main, pd.DataFrame([_main_row(row, note)])],
                                    ignore_index=True,
                                )
                                push_main = True
                            else:
                                st.warning("La oportunidad ya estaba en el pipeline; se registró la aprobación sin duplicarla.")
                        elif action == "Posponer":
                            staging.loc[selected_index, "Estado revisión"] = "Pospuesta"
                        else:
                            staging.loc[selected_index, "Estado revisión"] = "Descartada"

                        ok, error = _save_decision(staging, main, push_main, action)
                        if ok:
                            st.success("Decisión guardada y sincronizada con GitHub.")
                            st.session_state.pop("revision_selected_candidate", None)
                            st.session_state.pop(f"revision_comment_{selected_key}", None)
                            st.session_state.pop(f"revision_action_{selected_key}", None)
                            st.rerun()
                        else:
                            st.error(error)

                with st.expander("Ver listado técnico", expanded=False):
                    columns = [
                        "Puntaje", "Título", "Organización", "País", "Fecha límite",
                        "Afinidad", "Fuente", "Estado revisión",
                    ]
                    st.dataframe(
                        filtered[columns],
                        use_container_width=True,
                        hide_index=True,
                    )

    with tab_history:
        if staging.empty:
            st.info("Todavía no hay historial de revisión.")
        else:
            history = staging[_status_series(staging).isin(FINAL_STATUSES)].copy()
            if history.empty:
                st.info("Todavía no hay decisiones finalizadas.")
            else:
                history = history.sort_values("Fecha revisión", ascending=False)
                st.dataframe(
                    history[[
                        "Estado revisión", "Título", "Organización", "País", "Puntaje",
                        "Comentario revisión", "Revisado por", "Fecha revisión",
                    ]],
                    use_container_width=True,
                    hide_index=True,
                )
