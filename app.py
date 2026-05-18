import base64
import html as _html
import os
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# ── Configuración ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Oportunidades · Grupo CEO",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSV_PATH    = Path(__file__).parent / "oportunidades_consultoria.csv"
SCRIPT_PATH = Path(__file__).parent / "buscar_consultorias.py"
LOGO_PATH   = Path(__file__).parent / "logo_ceo.png"

# ── Paleta CEO ─────────────────────────────────────────────────────────────────
GREEN_DARK   = "#1A3D2E"
GREEN_MID    = "#3A7D58"
GREEN_ACCENT = "#4CAF82"
GREEN_LIGHT  = "#6DB86B"
BG_SAGE      = "#EEF6EE"
BG_HERO_FROM = "#C8E8CA"
BG_HERO_TO   = "#88C5B0"
WHITE        = "#FFFFFF"
TEXT_BODY    = "#3D3D3D"
BORDER_LIGHT = "#D4EAD6"

# Prioridades
COLOR_ALTA  = {"bg": "#FFE5E5", "border": "#D32F2F", "badge": "🔴"}
COLOR_MEDIA = {"bg": "#FFF8E1", "border": "#F9A825", "badge": "🟡"}
COLOR_BAJA  = {"bg": "#E8F5E9", "border": "#388E3C", "badge": "🟢"}
PRIO_MAP    = {"Alta": COLOR_ALTA, "Media": COLOR_MEDIA, "Baja": COLOR_BAJA}

# Estado → estilo chip
ESTADO_CHIPS = {
    "Identificada": {"bg": "#F5F5F5", "color": "#616161"},
    "En análisis":  {"bg": "#E3F2FD", "color": "#1565C0"},
    "Postulada":    {"bg": "#FFF3E0", "color": "#E65100"},
    "Ganada":       {"bg": "#E8F5E9", "color": "#2E7D32"},
    "Descartada":   {"bg": "#FFEBEE", "color": "#B71C1C"},
}
ESTADOS_ORDEN = ["Identificada", "En análisis", "Postulada", "Ganada", "Descartada"]

# Equipo CEO
CONSULTORES = [
    "—",
    "Martín Piñeiro",
    "Eduardo Trigo",
    "Federico Villareal",
    "Nelson Illescas",
    "Jimena Vicente",
    "Pablo Elverdin",
    "Agustín Tejeda",
    "Valeria Piñeiro",
]

MESES_ES = {
    1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
    7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def esc(text) -> str:
    """Escape para HTML + evita que Markdown interprete [ ] como links."""
    s = _html.escape(str(text or "—"), quote=True)
    return s.replace("[", "&#91;").replace("]", "&#93;")

def fmt_date_es(dt: datetime) -> str:
    return f"{dt.day} {MESES_ES[dt.month]} {dt.year}"

def csv_mtime() -> datetime | None:
    if CSV_PATH.exists():
        return datetime.fromtimestamp(CSV_PATH.stat().st_mtime)
    return None

def get_logo_b64() -> str:
    if LOGO_PATH.exists():
        return base64.b64encode(LOGO_PATH.read_bytes()).decode()
    return ""

LOGO_B64 = get_logo_b64()

# ── Datos ─────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    if not CSV_PATH.exists():
        return pd.DataFrame(columns=[
            "Título", "Organización", "Tipo", "Región", "País",
            "Fecha límite", "Enlace", "Afinidad", "Prioridad",
            "Estado", "Monto estimado (USD)", "Consultor",
        ])
    df = pd.read_csv(CSV_PATH)
    df.columns = df.columns.str.strip()

    for col in ["Prioridad", "Afinidad", "Tipo", "Región", "Fecha límite"]:
        df[col] = df.get(col, pd.Series(dtype=str)).fillna("—").str.strip()

    if "Estado" not in df.columns:
        df["Estado"] = "Identificada"
    else:
        df["Estado"] = df["Estado"].fillna("Identificada").str.strip()

    if "País" not in df.columns:
        df["País"] = "—"
    else:
        df["País"] = df["País"].fillna("—").str.strip()

    if "Monto estimado (USD)" not in df.columns:
        df["Monto estimado (USD)"] = 0
    else:
        df["Monto estimado (USD)"] = pd.to_numeric(
            df["Monto estimado (USD)"].astype(str)
                .str.replace(",", "").str.replace("$", "").str.strip(),
            errors="coerce",
        ).fillna(0)

    if "Consultor" not in df.columns:
        df["Consultor"] = "—"
    else:
        df["Consultor"] = df["Consultor"].fillna("—").str.strip()

    return df

MONTH_ES = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "ene": 1, "abr": 4, "ago": 8, "dic": 12,
}

def parse_deadline(raw: str) -> datetime:
    s = (raw or "").strip().lower()
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    m = re.search(r"(\d{1,2})-([a-z]{3})-(\d{4})", s)
    if m:
        mon = MONTH_ES.get(m.group(2))
        if mon:
            try:
                return datetime(int(m.group(3)), mon, int(m.group(1)))
            except ValueError:
                pass
    return datetime(2099, 12, 31)

def save_df(df: pd.DataFrame) -> None:
    """Escribe el DataFrame al CSV y limpia la caché."""
    export_cols = [
        "Título", "Organización", "Tipo", "Región", "País",
        "Fecha límite", "Enlace", "Afinidad", "Prioridad",
        "Estado", "Monto estimado (USD)", "Consultor",
    ]
    out = df[[c for c in export_cols if c in df.columns]]
    out.to_csv(CSV_PATH, index=False)
    st.cache_data.clear()

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');

  html, body, [class*="css"] {{ font-family: 'DM Sans', sans-serif !important; }}
  .main .block-container {{ padding: 0 !important; max-width: 100% !important; }}
  #MainMenu, footer {{ visibility: hidden; }}
  header[data-testid="stHeader"] {{ background: transparent !important; }}
  header[data-testid="stHeader"] a,
  header[data-testid="stHeader"] img {{ visibility: hidden; }}
  button[data-testid="collapsedControl"],
  button[data-testid="baseButton-headerNoPadding"] {{
    visibility: visible !important;
    background: {GREEN_DARK} !important;
    color: {WHITE} !important;
    border-radius: 8px !important;
  }}

  /* Sidebar */
  section[data-testid="stSidebar"] {{ background: {GREEN_DARK}; min-width: 280px !important; }}
  section[data-testid="stSidebar"] * {{ color: {WHITE} !important; }}
  section[data-testid="stSidebar"] .stTextInput input,
  section[data-testid="stSidebar"] .stMultiSelect div {{
    background: rgba(255,255,255,0.12) !important;
    color: {WHITE} !important;
    border-color: rgba(255,255,255,0.25) !important;
    border-radius: 8px !important;
  }}
  section[data-testid="stSidebar"] label {{
    color: {BG_SAGE} !important;
    font-weight: 500 !important;
    font-size: 0.82rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }}
  section[data-testid="stSidebar"] .stMultiSelect span {{
    background: {GREEN_ACCENT} !important;
    color: {WHITE} !important;
    border-radius: 20px !important;
  }}
  section[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.15) !important; }}
  section[data-testid="stSidebar"] .stButton button {{
    background: {GREEN_ACCENT} !important; color: {WHITE} !important;
    border: none !important; border-radius: 24px !important;
    font-weight: 600 !important; font-size: 0.9rem !important;
    padding: 0.55rem 1.2rem !important; transition: all 0.2s ease !important;
  }}
  section[data-testid="stSidebar"] .stButton button:hover {{
    background: {GREEN_LIGHT} !important; transform: translateY(-1px);
  }}

  /* Hero */
  .ceo-hero {{
    background: linear-gradient(135deg, {BG_HERO_FROM} 0%, {BG_HERO_TO} 100%);
    padding: 1.6rem 2rem 1.2rem;
    display: flex; align-items: center; justify-content: space-between;
    border-bottom: 3px solid {GREEN_MID};
    position: relative; overflow: hidden;
  }}
  .ceo-hero::before {{
    content: 'CEO'; position: absolute; right: -20px; top: -30px;
    font-size: 9rem; font-weight: 800; color: rgba(26,61,46,0.06);
    letter-spacing: -4px; pointer-events: none; line-height: 1;
  }}
  .ceo-hero-logo img {{ height: 56px; width: auto; }}
  .ceo-hero-text h1 {{
    color: {GREEN_DARK} !important; font-size: 1.45rem !important;
    font-weight: 700 !important; margin: 0 0 0.2rem !important; letter-spacing: -0.02em;
  }}
  .ceo-hero-text p {{ color: {GREEN_MID}; font-size: 0.84rem; margin: 0; font-weight: 400; }}
  .ceo-hero-dates {{ display: flex; flex-direction: column; align-items: flex-end; gap: 0.35rem; }}
  .ceo-hero-date {{
    background: {GREEN_DARK}; color: {WHITE};
    padding: 0.4rem 1rem; border-radius: 20px;
    font-size: 0.78rem; font-weight: 500; white-space: nowrap;
  }}
  .ceo-hero-csv-date {{
    background: rgba(26,61,46,0.15); color: {GREEN_DARK};
    padding: 0.3rem 0.8rem; border-radius: 20px;
    font-size: 0.72rem; font-weight: 500; white-space: nowrap;
    border: 1px solid rgba(26,61,46,0.2);
  }}

  /* Banner datos viejos */
  .stale-banner {{
    background: #FFF8E1; border-left: 4px solid #F9A825; color: #7B5000;
    padding: 0.7rem 1.5rem; font-size: 0.84rem; font-weight: 500;
    margin-left: -1.5rem; margin-right: -1.5rem;
  }}

  /* Metrics bar */
  .metrics-bar {{
    background: {WHITE}; border-bottom: 1px solid {BORDER_LIGHT};
    padding: 0.9rem 2rem; display: flex; gap: 0;
  }}
  .metric-pill {{
    flex: 1; text-align: center; padding: 0.4rem 0.5rem;
    border-right: 1px solid {BORDER_LIGHT};
  }}
  .metric-pill:last-child {{ border-right: none; }}
  .metric-num {{ font-size: 1.8rem; font-weight: 700; color: {GREEN_DARK}; line-height: 1; }}
  .metric-num-sm {{ font-size: 1.3rem; font-weight: 700; color: {GREEN_DARK}; line-height: 1; }}
  .metric-label {{ font-size: 0.72rem; color: #777; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 2px; }}

  /* Content */
  .main {{ background: {BG_SAGE} !important; }}
  .main .block-container {{ padding: 0 0 2rem 0 !important; max-width: 100% !important; }}
  .stMarkdown {{ padding: 0 !important; }}

  /* Cards */
  .opp-card {{
    background: {WHITE}; border-radius: 14px; border: 1px solid {BORDER_LIGHT};
    padding: 1rem 1.2rem 0.85rem; margin-bottom: 0.4rem;
    box-shadow: 0 1px 6px rgba(26,61,46,0.07);
    transition: box-shadow 0.2s ease, transform 0.15s ease;
    border-left-width: 4px; border-left-style: solid;
  }}
  .opp-card:hover {{ box-shadow: 0 4px 18px rgba(26,61,46,0.13); transform: translateY(-1px); }}
  .opp-title {{ font-size: 0.97rem; font-weight: 600; color: {GREEN_DARK}; margin-bottom: 0.45rem; line-height: 1.35; }}
  .opp-title-descartada {{ font-size: 0.97rem; font-weight: 600; color: #9E9E9E; margin-bottom: 0.45rem; line-height: 1.35; text-decoration: line-through; }}
  .opp-meta {{ display: flex; flex-wrap: wrap; gap: 0.35rem 1rem; font-size: 0.78rem; color: {TEXT_BODY}; margin-bottom: 0.45rem; }}
  .opp-meta span {{ display: flex; align-items: center; gap: 0.25rem; }}
  .opp-chips {{ display: flex; flex-wrap: wrap; gap: 0.3rem; align-items: center; }}
  .chip {{
    display: inline-block; padding: 2px 10px; border-radius: 20px;
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.02em;
  }}
  .chip-dark  {{ background: {GREEN_DARK}; color: {WHITE}; }}
  .chip-mid   {{ background: {BG_SAGE}; color: {GREEN_DARK}; border: 1px solid {BORDER_LIGHT}; }}
  .chip-alta  {{ background: #FFE5E5; color: #B71C1C; }}
  .chip-media {{ background: #FFF8E1; color: #E65100; }}
  .chip-baja  {{ background: #E8F5E9; color: #1B5E20; }}
  .chip-monto {{ background: #E8F4FD; color: #0D47A1; border: 1px solid #BBDEFB; }}
  .chip-link  {{ background: {GREEN_DARK}; color: {WHITE}; text-decoration: none; padding: 3px 12px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; }}
  .chip-link:hover {{ background: {GREEN_MID}; }}

  /* Section header */
  .section-header {{
    font-size: 0.78rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.08em; color: {GREEN_MID};
    padding: 0.6rem 0 0.4rem; border-bottom: 2px solid {BORDER_LIGHT}; margin-bottom: 0.8rem;
  }}

  /* Edit row below card */
  .edit-row {{ margin-bottom: 0.9rem; }}

  /* Empty state */
  .empty-state {{ text-align: center; padding: 3rem 1rem; color: {GREEN_MID}; }}
  .empty-state .icon {{ font-size: 3rem; margin-bottom: 0.5rem; }}

  /* Cartera cards */
  .cartera-card {{
    background: {WHITE}; border-radius: 12px; border: 1px solid {BORDER_LIGHT};
    padding: 1rem 1.2rem; margin-bottom: 0.8rem;
    box-shadow: 0 1px 4px rgba(26,61,46,0.07);
    border-left: 4px solid {GREEN_ACCENT};
  }}
  .cartera-name {{ font-size: 1rem; font-weight: 700; color: {GREEN_DARK}; margin-bottom: 0.4rem; }}
  .cartera-stats {{ display: flex; flex-wrap: wrap; gap: 0.4rem 1.5rem; font-size: 0.82rem; color: {TEXT_BODY}; margin-bottom: 0.5rem; }}
  .cartera-stats span {{ display: flex; align-items: center; gap: 0.3rem; font-weight: 500; }}
  .cartera-estados {{ display: flex; flex-wrap: wrap; gap: 0.25rem; }}

  /* Download */
  .stDownloadButton button {{
    background: {GREEN_DARK} !important; color: {WHITE} !important;
    border: none !important; border-radius: 24px !important;
    font-weight: 600 !important; width: 100% !important;
    padding: 0.6rem !important; margin-top: 0.5rem !important;
  }}
  .stDownloadButton button:hover {{ background: {GREEN_MID} !important; }}

  /* Padding principal */
  div[data-testid="stVerticalBlock"] > div {{
    padding-left: 1.5rem !important; padding-right: 1.5rem !important;
  }}
  .ceo-hero, .metrics-bar, .stale-banner {{
    margin-left: -1.5rem; margin-right: -1.5rem;
  }}

  /* Mobile */
  @media (max-width: 768px) {{
    .ceo-hero {{ flex-direction: column; align-items: flex-start; gap: 0.7rem; padding: 1rem 1.2rem 0.9rem; }}
    .ceo-hero::before {{ display: none; }}
    .ceo-hero-logo img {{ height: 38px; }}
    .ceo-hero-text h1 {{ font-size: 1.1rem !important; }}
    .ceo-hero-dates {{ align-items: flex-start; }}
    .metrics-bar {{ padding: 0.6rem 0.8rem; flex-wrap: wrap; }}
    .metric-pill {{ flex: 1 1 45%; border-right: none !important; border-bottom: 1px solid {BORDER_LIGHT}; padding: 0.4rem 0.3rem; }}
    .metric-num {{ font-size: 1.4rem; }} .metric-num-sm {{ font-size: 1.1rem; }}
    .metric-label {{ font-size: 0.65rem; }}
    .opp-card {{ padding: 0.8rem 0.9rem; border-radius: 10px; }}
    .opp-title {{ font-size: 0.9rem; }}
    .opp-meta {{ flex-direction: column; gap: 0.2rem; font-size: 0.75rem; }}
    .section-header {{ font-size: 0.72rem; }}
    div[data-testid="stVerticalBlock"] > div {{ padding-left: 0.8rem !important; padding-right: 0.8rem !important; }}
    .stale-banner {{ margin-left: -0.8rem; margin-right: -0.8rem; }}
  }}
  @media (max-width: 480px) {{
    .ceo-hero-text h1 {{ font-size: 0.95rem !important; }}
    .metric-pill {{ flex: 1 1 48%; }}
  }}

  /* Mobile hint */
  .mobile-hint {{ display: none; }}
  @media (max-width: 768px) {{
    .mobile-hint {{
      display: flex; align-items: center; gap: 0.6rem;
      background: {GREEN_DARK}; color: {WHITE};
      font-size: 0.82rem; font-weight: 500;
      padding: 0.55rem 1.2rem; border-bottom: 2px solid {GREEN_MID};
      margin-left: -0.8rem; margin-right: -0.8rem;
    }}
    .mobile-hint .arrow-icon {{
      background: {GREEN_ACCENT}; border-radius: 6px;
      padding: 2px 8px; font-size: 1rem; font-weight: 700; line-height: 1.4;
    }}
  }}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    if LOGO_B64:
        st.markdown(
            f"<div style='padding:0.4rem 0 1rem'>"
            f"<img src='data:image/png;base64,{LOGO_B64}' "
            f"style='height:44px;filter:brightness(0) invert(1);'>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("### 🔎 Filtros")
    df_full = load_data()

    prioridad_sel = st.multiselect("Prioridad", ["Alta", "Media", "Baja"], default=["Alta", "Media"])
    afinidad_sel  = st.multiselect("Afinidad", ["Individual", "Empresarial", "Ambos"], default=["Individual", "Empresarial", "Ambos"])
    estado_sel    = st.multiselect("Estado", ESTADOS_ORDEN, default=[e for e in ESTADOS_ORDEN if e != "Descartada"])

    consultores_csv  = df_full["Consultor"].dropna().unique().tolist()
    consultores_opts = sorted(set(CONSULTORES + consultores_csv))
    consultor_sel    = st.multiselect("Consultor", consultores_opts, default=consultores_opts)

    regiones   = sorted(df_full["Región"].dropna().unique().tolist())
    region_sel = st.multiselect("Región", regiones, default=regiones)

    paises   = sorted(df_full["País"].dropna().unique().tolist())
    pais_sel = st.multiselect("País", paises, default=paises)

    texto = st.text_input("Buscar", placeholder="UNDP, cacao, agroecología…")

    st.divider()
    st.markdown("### ⚙️ Actualizar datos")

    _default_key = (
        st.secrets.get("TAVILY_API_KEY", "") if hasattr(st, "secrets") else ""
    ) or os.environ.get("TAVILY_API_KEY", "")

    tavily_key = st.text_input("Tavily API Key", type="password", value=_default_key, help="Opcional — mejora la búsqueda.")

    _is_cloud = not SCRIPT_PATH.exists()
    if _is_cloud:
        st.info(
            "**Actualización automática:** lunes y jueves vía GitHub Actions.\n\n"
            "Para actualizar ahora, abrí Terminal en tu Mac y ejecutá:\n\n"
            "`/Users/fvillareal/actualizar_y_publicar.sh`",
            icon="ℹ️",
        )
    else:
        if st.button("▶ Buscar nuevas oportunidades", use_container_width=True):
            with st.spinner("Buscando…"):
                env = os.environ.copy()
                if tavily_key.strip():
                    env["TAVILY_API_KEY"] = tavily_key.strip()
                result = subprocess.run([sys.executable, str(SCRIPT_PATH)], capture_output=True, text=True, env=env)
            if result.returncode == 0:
                st.success("¡Búsqueda completada!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Error:")
                st.code((result.stderr or result.stdout)[-1500:])

    st.divider()
    st.markdown(
        f"<div style='font-size:0.72rem;color:rgba(255,255,255,0.45);text-align:center;'>"
        f"grupo-ceo.com · {date.today().year}</div>",
        unsafe_allow_html=True,
    )

# ── Filtrar y ordenar ─────────────────────────────────────────────────────────

df = load_data()
if prioridad_sel:  df = df[df["Prioridad"].isin(prioridad_sel)]
if afinidad_sel:   df = df[df["Afinidad"].isin(afinidad_sel)]
if estado_sel:     df = df[df["Estado"].isin(estado_sel)]
if consultor_sel:  df = df[df["Consultor"].isin(consultor_sel)]
if region_sel:     df = df[df["Región"].isin(region_sel)]
if pais_sel:       df = df[df["País"].isin(pais_sel)]
if texto.strip():
    mask = (
        df["Título"].str.contains(texto, case=False, na=False) |
        df["Organización"].str.contains(texto, case=False, na=False)
    )
    df = df[mask]

orden_prio = {"Alta": 0, "Media": 1, "Baja": 2}
df = df.copy()
df["_ord_prio"]  = df["Prioridad"].map(orden_prio).fillna(3)
df["_ord_fecha"] = df["Fecha límite"].apply(parse_deadline)
df = df.sort_values(["_ord_prio", "_ord_fecha"]).drop(columns=["_ord_prio", "_ord_fecha"])

# ── Hero ──────────────────────────────────────────────────────────────────────

mtime    = csv_mtime()
hoy      = date.today()
days_old = (datetime.now() - mtime).days if mtime else 999

csv_date_html = (
    f'<div class="ceo-hero-csv-date">🔄 Datos: {fmt_date_es(mtime)}</div>'
    if mtime else ""
)
logo_html = (
    f"<img src='data:image/png;base64,{LOGO_B64}' alt='Grupo CEO'>"
    if LOGO_B64 else
    f"<span style='font-size:1.4rem;font-weight:800;color:{GREEN_DARK}'>Grupo <b>CEO</b></span>"
)

st.markdown(f"""
<div class="ceo-hero">
  <div class="ceo-hero-logo">{logo_html}</div>
  <div class="ceo-hero-text">
    <h1>Oportunidades de Consultoría</h1>
    <p>Monitoreo de convocatorias · Perfiles Individual &amp; Empresarial · ALC &amp; Global</p>
  </div>
  <div class="ceo-hero-dates">
    <div class="ceo-hero-date">📅 {hoy.strftime('%d %b %Y')}</div>
    {csv_date_html}
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="mobile-hint">
  <span class="arrow-icon">☰</span>
  <span>Tocá el ícono de arriba a la izquierda para <strong>filtrar oportunidades</strong></span>
</div>
""", unsafe_allow_html=True)

if days_old > 7:
    st.markdown(
        f'<div class="stale-banner">⚠️ Los datos tienen más de {days_old} días. Considerá ejecutar una nueva búsqueda.</div>',
        unsafe_allow_html=True,
    )

# ── Métricas ──────────────────────────────────────────────────────────────────

total        = len(df)
n_alta       = len(df[df["Prioridad"] == "Alta"])
n_ind        = len(df[df["Afinidad"].isin(["Individual", "Ambos"])])
n_empresa    = len(df[df["Afinidad"].isin(["Empresarial", "Ambos"])])
pipeline     = df["Monto estimado (USD)"].sum()
pipeline_fmt = f"${pipeline:,.0f}" if pipeline > 0 else "—"

st.markdown(f"""
<div class="metrics-bar">
  <div class="metric-pill">
    <div class="metric-num">{total}</div>
    <div class="metric-label">Total filtradas</div>
  </div>
  <div class="metric-pill">
    <div class="metric-num" style="color:#C62828">{n_alta}</div>
    <div class="metric-label">🔴 Prioridad Alta</div>
  </div>
  <div class="metric-pill">
    <div class="metric-num">{n_ind}</div>
    <div class="metric-label">👤 Para Individual</div>
  </div>
  <div class="metric-pill">
    <div class="metric-num">{n_empresa}</div>
    <div class="metric-label">🏢 Para CEO</div>
  </div>
  <div class="metric-pill">
    <div class="metric-num-sm" style="color:#0D47A1">{pipeline_fmt}</div>
    <div class="metric-label">💰 Pipeline USD</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs(["📋  Oportunidades", "📊  Cartera", "✏️  Editar datos"])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — OPORTUNIDADES
# ════════════════════════════════════════════════════════════════════════════

with tab1:
    if df.empty:
        st.markdown("""
        <div class="empty-state">
          <div class="icon">🌿</div>
          <p>No hay oportunidades con los filtros actuales.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        grupo_actual = None
        df_all_editable = load_data()   # referencia completa para guardar cambios

        for idx, (orig_idx, row) in enumerate(df.iterrows()):
            prio   = row.get("Prioridad", "Media")
            pconf  = PRIO_MAP.get(prio, PRIO_MAP["Media"])
            estado = row.get("Estado", "Identificada")
            econf  = ESTADO_CHIPS.get(estado, ESTADO_CHIPS["Identificada"])

            # Separador de grupo
            if prio != grupo_actual:
                grupo_actual = prio
                labels = {"Alta": "🔴 Prioridad Alta", "Media": "🟡 Prioridad Media", "Baja": "🟢 Otras oportunidades"}
                st.markdown(f'<div class="section-header">{labels.get(prio, prio)}</div>', unsafe_allow_html=True)

            titulo    = row.get("Título", "Sin título")
            org       = row.get("Organización", "—")
            region    = row.get("Región", "—")
            pais      = row.get("País", "—")
            fecha     = row.get("Fecha límite", "—")
            enlace    = str(row.get("Enlace", "") or "")
            afin      = row.get("Afinidad", "—")
            consultor = row.get("Consultor", "—")
            monto     = float(row.get("Monto estimado (USD)", 0) or 0)

            descartada = (estado == "Descartada")
            title_cls  = "opp-title-descartada" if descartada else "opp-title"
            chip_prio  = {"Alta": "chip-alta", "Media": "chip-media", "Baja": "chip-baja"}.get(prio, "chip-mid")

            # Link: renderizado como chip HTML puro, sin markdown
            link_chip = ""
            if enlace.startswith("http"):
                link_chip = f'<a class="chip chip-link" href="{esc(enlace)}" target="_blank">🔗 Ver convocatoria</a>'

            pais_chip = f'<span class="chip chip-mid">📍 {esc(pais)}</span>' if pais and pais != "—" else ""
            monto_chip = f'<span class="chip chip-monto">💰 ${monto:,.0f}</span>' if monto > 0 else ""
            consultor_chip = f'<span class="chip chip-mid">👤 {esc(consultor)}</span>' if consultor and consultor != "—" else ""

            # Card HTML — todo el texto dinámico pasa por esc()
            st.markdown(f"""
<div class="opp-card" style="border-left-color:{pconf['border']}; background:{pconf['bg']}08;">
  <div class="{title_cls}">{esc(titulo)}</div>
  <div class="opp-meta">
    <span>🏛 <strong>{esc(org)}</strong></span>
    <span>📍 {esc(region)}</span>
    <span>📅 <strong>{esc(fecha)}</strong></span>
  </div>
  <div class="opp-chips">
    <span class="chip chip-dark">{esc(afin)}</span>
    <span class="chip {chip_prio}">{pconf['badge']} {esc(prio)}</span>
    <span class="chip" style="background:{econf['bg']};color:{econf['color']};">{esc(estado)}</span>
    {pais_chip}{monto_chip}{consultor_chip}{link_chip}
  </div>
</div>
""", unsafe_allow_html=True)

            # Fila de edición inline bajo cada card
            with st.container():
                ec1, ec2, ec3 = st.columns([3, 3, 2])
                with ec1:
                    cur_est_idx = ESTADOS_ORDEN.index(estado) if estado in ESTADOS_ORDEN else 0
                    new_estado = st.selectbox(
                        "Estado", ESTADOS_ORDEN, index=cur_est_idx,
                        key=f"est_{orig_idx}", label_visibility="collapsed",
                    )
                with ec2:
                    cur_con_idx = CONSULTORES.index(consultor) if consultor in CONSULTORES else 0
                    new_consultor = st.selectbox(
                        "Consultor", CONSULTORES, index=cur_con_idx,
                        key=f"con_{orig_idx}", label_visibility="collapsed",
                    )
                with ec3:
                    changed = (new_estado != estado or new_consultor != consultor)
                    if changed:
                        if st.button("💾 Guardar", key=f"save_{orig_idx}", type="primary"):
                            df_all_editable.at[orig_idx, "Estado"]    = new_estado
                            df_all_editable.at[orig_idx, "Consultor"] = new_consultor
                            save_df(df_all_editable)
                            st.rerun()

        # Descarga
        st.divider()
        export_cols = ["Título", "Organización", "Tipo", "Región", "País", "Fecha límite", "Enlace", "Afinidad", "Prioridad", "Estado", "Monto estimado (USD)", "Consultor"]
        export_df = df[[c for c in export_cols if c in df.columns]]
        st.download_button(
            label="⬇️ Descargar resultados filtrados (CSV)",
            data=export_df.to_csv(index=False).encode("utf-8"),
            file_name=f"ceo_consultorias_{date.today()}.csv",
            mime="text/csv",
        )

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — CARTERA
# ════════════════════════════════════════════════════════════════════════════

with tab2:
    df_c = load_data()   # datos completos, sin filtro de sidebar

    # ── Resumen CEO total ────────────────────────────────────────────────────
    total_c   = len(df_c)
    pipeline_c = df_c["Monto estimado (USD)"].sum()
    ganadas_c  = len(df_c[df_c["Estado"] == "Ganada"])
    en_proceso = len(df_c[df_c["Estado"].isin(["Identificada", "En análisis", "Postulada"])])

    st.markdown(f"""
<div style="background:{GREEN_DARK};border-radius:14px;padding:1.2rem 1.6rem;margin-bottom:1.2rem;display:flex;flex-wrap:wrap;gap:1.2rem 2.5rem;align-items:center;">
  <div>
    <div style="color:rgba(255,255,255,0.6);font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em;">Total cartera CEO</div>
    <div style="color:{WHITE};font-size:2rem;font-weight:700;line-height:1.1;">{total_c}</div>
  </div>
  <div>
    <div style="color:rgba(255,255,255,0.6);font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em;">En proceso</div>
    <div style="color:{GREEN_ACCENT};font-size:2rem;font-weight:700;line-height:1.1;">{en_proceso}</div>
  </div>
  <div>
    <div style="color:rgba(255,255,255,0.6);font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em;">Ganadas</div>
    <div style="color:#A5D6A7;font-size:2rem;font-weight:700;line-height:1.1;">{ganadas_c}</div>
  </div>
  <div>
    <div style="color:rgba(255,255,255,0.6);font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em;">Pipeline estimado</div>
    <div style="color:#90CAF9;font-size:1.6rem;font-weight:700;line-height:1.1;">${pipeline_c:,.0f}</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # Estado breakdown CEO total
    estado_counts = df_c["Estado"].value_counts()
    chips_html = " ".join(
        f'<span class="chip" style="background:{ESTADO_CHIPS.get(e, {}).get("bg","#eee")};color:{ESTADO_CHIPS.get(e, {}).get("color","#333")};">'
        f'{e}: <strong>{estado_counts.get(e, 0)}</strong></span>'
        for e in ESTADOS_ORDEN
    )
    st.markdown(f'<div style="margin-bottom:1.5rem;display:flex;flex-wrap:wrap;gap:0.4rem;">{chips_html}</div>', unsafe_allow_html=True)

    # ── Por consultor ────────────────────────────────────────────────────────
    st.markdown(f'<div class="section-header">Por Consultor</div>', unsafe_allow_html=True)

    # Incluir solo consultores con al menos 1 oportunidad asignada (excluye "—")
    df_asignadas = df_c[df_c["Consultor"] != "—"]
    sin_asignar  = df_c[df_c["Consultor"] == "—"]

    if df_asignadas.empty:
        st.info("Aún no hay oportunidades asignadas a consultores. Usá la pestaña **Editar datos** o los selectores en **Oportunidades** para asignar responsables.")
    else:
        for nombre in [c for c in CONSULTORES if c != "—"]:
            sub = df_asignadas[df_asignadas["Consultor"] == nombre]
            if sub.empty:
                continue

            pipeline_p = sub["Monto estimado (USD)"].sum()
            n_alta_p   = len(sub[sub["Prioridad"] == "Alta"])
            ganadas_p  = len(sub[sub["Estado"] == "Ganada"])

            est_html = " ".join(
                f'<span class="chip" style="background:{ESTADO_CHIPS.get(e,{}).get("bg","#eee")};color:{ESTADO_CHIPS.get(e,{}).get("color","#333")};">'
                f'{e}: {len(sub[sub["Estado"]==e])}</span>'
                for e in ESTADOS_ORDEN if len(sub[sub["Estado"]==e]) > 0
            )
            monto_str = f" · 💰 ${pipeline_p:,.0f}" if pipeline_p > 0 else ""

            st.markdown(f"""
<div class="cartera-card">
  <div class="cartera-name">👤 {esc(nombre)}</div>
  <div class="cartera-stats">
    <span>📋 {len(sub)} oportunidad{'es' if len(sub)!=1 else ''}</span>
    <span>🔴 {n_alta_p} Alta prioridad</span>
    <span>🏆 {ganadas_p} Ganada{'s' if ganadas_p!=1 else ''}</span>
    {'<span>💰 $' + f'{pipeline_p:,.0f}</span>' if pipeline_p > 0 else ''}
  </div>
  <div class="cartera-estados">{est_html}</div>
</div>
""", unsafe_allow_html=True)

            # Listado de oportunidades del consultor (colapsable)
            with st.expander(f"Ver oportunidades asignadas a {nombre} ({len(sub)})"):
                for _, r in sub.sort_values("Prioridad").iterrows():
                    pconf2    = PRIO_MAP.get(r.get("Prioridad", "Media"), PRIO_MAP["Media"])
                    econf2    = ESTADO_CHIPS.get(r.get("Estado", "Identificada"), ESTADO_CHIPS["Identificada"])
                    enlace2   = str(r.get("Enlace", "") or "")
                    link2     = f'<a class="chip chip-link" href="{esc(enlace2)}" target="_blank">🔗 Ver</a>' if enlace2.startswith("http") else ""
                    chip_p2   = {"Alta": "chip-alta", "Media": "chip-media", "Baja": "chip-baja"}.get(r.get("Prioridad", "Media"), "chip-mid")
                    st.markdown(f"""
<div class="opp-card" style="border-left-color:{pconf2['border']};background:{pconf2['bg']}08;margin-bottom:0.5rem;">
  <div class="opp-title">{esc(r.get('Título',''))}</div>
  <div class="opp-meta">
    <span>🏛 {esc(r.get('Organización','—'))}</span>
    <span>📅 {esc(r.get('Fecha límite','—'))}</span>
  </div>
  <div class="opp-chips">
    <span class="chip {chip_p2}">{pconf2['badge']} {esc(r.get('Prioridad',''))}</span>
    <span class="chip" style="background:{econf2['bg']};color:{econf2['color']};">{esc(r.get('Estado',''))}</span>
    {link2}
  </div>
</div>
""", unsafe_allow_html=True)

    # Sin asignar
    if len(sin_asignar) > 0:
        st.markdown(f'<div class="section-header" style="margin-top:1rem;">Sin asignar ({len(sin_asignar)})</div>', unsafe_allow_html=True)
        with st.expander(f"Ver {len(sin_asignar)} oportunidades sin consultor asignado"):
            for _, r in sin_asignar.head(30).iterrows():
                pconf3  = PRIO_MAP.get(r.get("Prioridad", "Media"), PRIO_MAP["Media"])
                enlace3 = str(r.get("Enlace", "") or "")
                link3   = f'<a class="chip chip-link" href="{esc(enlace3)}" target="_blank">🔗 Ver</a>' if enlace3.startswith("http") else ""
                chip_p3 = {"Alta": "chip-alta", "Media": "chip-media", "Baja": "chip-baja"}.get(r.get("Prioridad", "Media"), "chip-mid")
                st.markdown(f"""
<div class="opp-card" style="border-left-color:{pconf3['border']};background:{pconf3['bg']}08;margin-bottom:0.5rem;">
  <div class="opp-title">{esc(r.get('Título',''))}</div>
  <div class="opp-meta"><span>🏛 {esc(r.get('Organización','—'))}</span><span>📅 {esc(r.get('Fecha límite','—'))}</span></div>
  <div class="opp-chips">
    <span class="chip chip-dark">{esc(r.get('Afinidad','—'))}</span>
    <span class="chip {chip_p3}">{pconf3['badge']} {esc(r.get('Prioridad',''))}</span>
    {link3}
  </div>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — EDITAR DATOS
# ════════════════════════════════════════════════════════════════════════════

with tab3:
    st.markdown("**Editá Estado, Consultor, Monto y País directamente en la tabla. Guardá al terminar.**")
    if _is_cloud:
        st.info("Estás en la versión en la nube. Los cambios se guardan en el servidor hasta la próxima actualización. Descargá el CSV para conservarlos de forma permanente.", icon="ℹ️")

    df_edit = load_data()

    EDIT_COLS = ["Título", "Organización", "Fecha límite", "Prioridad", "Estado", "Consultor", "Monto estimado (USD)", "País"]
    df_show   = df_edit[[c for c in EDIT_COLS if c in df_edit.columns]].copy()

    edited = st.data_editor(
        df_show,
        use_container_width=True,
        height=550,
        num_rows="fixed",
        key="data_editor_main",
        column_config={
            "Título":              st.column_config.TextColumn("Título", width="large", disabled=True),
            "Organización":        st.column_config.TextColumn("Organización", disabled=True),
            "Fecha límite":        st.column_config.TextColumn("Fecha límite", disabled=True),
            "Prioridad":           st.column_config.SelectboxColumn("Prioridad", options=["Alta", "Media", "Baja"]),
            "Estado":              st.column_config.SelectboxColumn("Estado", options=ESTADOS_ORDEN),
            "Consultor":           st.column_config.SelectboxColumn("Consultor", options=CONSULTORES),
            "Monto estimado (USD)":st.column_config.NumberColumn("Monto (USD)", min_value=0, format="$%d"),
            "País":                st.column_config.TextColumn("País"),
        },
    )

    col_save, col_dl = st.columns([1, 1])
    with col_save:
        if st.button("💾 Guardar cambios en CSV", type="primary", use_container_width=True):
            for col in ["Estado", "Consultor", "Monto estimado (USD)", "País", "Prioridad"]:
                if col in edited.columns:
                    df_edit[col] = edited[col].values
            save_df(df_edit)
            st.success("¡Cambios guardados! La app se actualizará en unos segundos.")
            st.rerun()
    with col_dl:
        st.download_button(
            "⬇️ Descargar CSV editado",
            data=edited.to_csv(index=False).encode("utf-8"),
            file_name=f"ceo_consultorias_editado_{date.today()}.csv",
            mime="text/csv",
            use_container_width=True,
        )
