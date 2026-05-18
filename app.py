import base64
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
TEXT_DARK    = "#1A1A1A"
TEXT_BODY    = "#3D3D3D"
BORDER_LIGHT = "#D4EAD6"

# Prioridades
COLOR_ALTA  = {"bg": "#FFE5E5", "border": "#D32F2F", "badge": "🔴"}
COLOR_MEDIA = {"bg": "#FFF8E1", "border": "#F9A825", "badge": "🟡"}
COLOR_BAJA  = {"bg": "#E8F5E9", "border": "#388E3C", "badge": "🟢"}
PRIO_MAP    = {"Alta": COLOR_ALTA, "Media": COLOR_MEDIA, "Baja": COLOR_BAJA}

# Estado de postulación → estilo del chip
ESTADO_CHIPS = {
    "Identificada": {"bg": "#F5F5F5", "color": "#616161"},
    "En análisis":  {"bg": "#E3F2FD", "color": "#1565C0"},
    "Postulada":    {"bg": "#FFF3E0", "color": "#E65100"},
    "Ganada":       {"bg": "#E8F5E9", "color": "#2E7D32"},
    "Descartada":   {"bg": "#FFEBEE", "color": "#B71C1C"},
}
ESTADOS_ORDEN = ["Identificada", "En análisis", "Postulada", "Ganada", "Descartada"]

# Consultores fijos del equipo CEO
CONSULTORES = [
    "—",
    "Federico Villareal",
    "Ana García",
    "Carlos López",
]

# ── Logo ──────────────────────────────────────────────────────────────────────

def get_logo_b64() -> str:
    if LOGO_PATH.exists():
        return base64.b64encode(LOGO_PATH.read_bytes()).decode()
    return ""

LOGO_B64 = get_logo_b64()

# ── CSS global ────────────────────────────────────────────────────────────────

st.markdown(f"""
<style>
  /* ── Google Fonts ── */
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');

  /* ── Reset Streamlit ── */
  html, body, [class*="css"] {{
    font-family: 'DM Sans', sans-serif !important;
  }}
  .main .block-container {{
    padding: 0 !important;
    max-width: 100% !important;
  }}
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

  /* ── Sidebar ── */
  section[data-testid="stSidebar"] {{
    background: {GREEN_DARK};
    min-width: 280px !important;
  }}
  section[data-testid="stSidebar"] * {{
    color: {WHITE} !important;
  }}
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
  section[data-testid="stSidebar"] hr {{
    border-color: rgba(255,255,255,0.15) !important;
  }}
  section[data-testid="stSidebar"] .stButton button {{
    background: {GREEN_ACCENT} !important;
    color: {WHITE} !important;
    border: none !important;
    border-radius: 24px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.55rem 1.2rem !important;
    transition: all 0.2s ease !important;
  }}
  section[data-testid="stSidebar"] .stButton button:hover {{
    background: {GREEN_LIGHT} !important;
    transform: translateY(-1px);
  }}

  /* ── Hero / Header ── */
  .ceo-hero {{
    background: linear-gradient(135deg, {BG_HERO_FROM} 0%, {BG_HERO_TO} 100%);
    padding: 1.6rem 2rem 1.2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 3px solid {GREEN_MID};
    position: relative;
    overflow: hidden;
  }}
  .ceo-hero::before {{
    content: 'CEO';
    position: absolute;
    right: -20px;
    top: -30px;
    font-size: 9rem;
    font-weight: 800;
    color: rgba(26,61,46,0.06);
    letter-spacing: -4px;
    pointer-events: none;
    line-height: 1;
  }}
  .ceo-hero-logo img {{ height: 56px; width: auto; }}
  .ceo-hero-text h1 {{
    color: {GREEN_DARK} !important;
    font-size: 1.45rem !important;
    font-weight: 700 !important;
    margin: 0 0 0.2rem !important;
    letter-spacing: -0.02em;
  }}
  .ceo-hero-text p {{
    color: {GREEN_MID};
    font-size: 0.84rem;
    margin: 0;
    font-weight: 400;
  }}
  .ceo-hero-dates {{
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.35rem;
  }}
  .ceo-hero-date {{
    background: {GREEN_DARK};
    color: {WHITE};
    padding: 0.4rem 1rem;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 500;
    white-space: nowrap;
  }}
  .ceo-hero-csv-date {{
    background: rgba(26,61,46,0.15);
    color: {GREEN_DARK};
    padding: 0.3rem 0.8rem;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 500;
    white-space: nowrap;
    border: 1px solid rgba(26,61,46,0.2);
  }}

  /* ── Banner de datos desactualizados ── */
  .stale-banner {{
    background: #FFF8E1;
    border-left: 4px solid #F9A825;
    color: #7B5000;
    padding: 0.7rem 1.5rem;
    font-size: 0.84rem;
    font-weight: 500;
    margin-left: -1.5rem;
    margin-right: -1.5rem;
  }}

  /* ── Metrics bar ── */
  .metrics-bar {{
    background: {WHITE};
    border-bottom: 1px solid {BORDER_LIGHT};
    padding: 0.9rem 2rem;
    display: flex;
    gap: 0;
  }}
  .metric-pill {{
    flex: 1;
    text-align: center;
    padding: 0.4rem 0.5rem;
    border-right: 1px solid {BORDER_LIGHT};
  }}
  .metric-pill:last-child {{ border-right: none; }}
  .metric-num {{
    font-size: 1.8rem;
    font-weight: 700;
    color: {GREEN_DARK};
    line-height: 1;
  }}
  .metric-num-sm {{
    font-size: 1.3rem;
    font-weight: 700;
    color: {GREEN_DARK};
    line-height: 1;
  }}
  .metric-label {{
    font-size: 0.72rem;
    color: #777;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 2px;
  }}

  /* ── Content area ── */
  .main {{ background: {BG_SAGE} !important; }}
  .main .block-container {{
    padding: 0 0 2rem 0 !important;
    max-width: 100% !important;
  }}
  .stMarkdown {{ padding: 0 !important; }}

  /* ── Opportunity card ── */
  .opp-card {{
    background: {WHITE};
    border-radius: 14px;
    border: 1px solid {BORDER_LIGHT};
    padding: 1rem 1.2rem 0.85rem;
    margin-bottom: 0.8rem;
    box-shadow: 0 1px 6px rgba(26,61,46,0.07);
    transition: box-shadow 0.2s ease, transform 0.15s ease;
    border-left-width: 4px;
    border-left-style: solid;
  }}
  .opp-card:hover {{
    box-shadow: 0 4px 18px rgba(26,61,46,0.13);
    transform: translateY(-1px);
  }}
  .opp-title {{
    font-size: 0.97rem;
    font-weight: 600;
    color: {GREEN_DARK};
    margin-bottom: 0.5rem;
    line-height: 1.35;
  }}
  .opp-title-descartada {{
    font-size: 0.97rem;
    font-weight: 600;
    color: #9E9E9E;
    margin-bottom: 0.5rem;
    line-height: 1.35;
    text-decoration: line-through;
  }}
  .opp-meta {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem 1rem;
    font-size: 0.78rem;
    color: {TEXT_BODY};
    margin-bottom: 0.55rem;
  }}
  .opp-meta span {{
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }}
  .opp-chips {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
    align-items: center;
  }}
  .chip {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.02em;
  }}
  .chip-dark  {{ background: {GREEN_DARK}; color: {WHITE}; }}
  .chip-mid   {{ background: {BG_SAGE}; color: {GREEN_DARK}; border: 1px solid {BORDER_LIGHT}; }}
  .chip-alta  {{ background: #FFE5E5; color: #B71C1C; }}
  .chip-media {{ background: #FFF8E1; color: #E65100; }}
  .chip-baja  {{ background: #E8F5E9; color: #1B5E20; }}
  .chip-monto {{ background: #E8F4FD; color: #0D47A1; border: 1px solid #BBDEFB; }}
  .opp-link a {{
    color: {GREEN_ACCENT};
    font-size: 0.78rem;
    font-weight: 600;
    text-decoration: none;
  }}
  .opp-link a:hover {{ text-decoration: underline; }}

  /* ── Section header ── */
  .section-header {{
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: {GREEN_MID};
    padding: 0.6rem 0 0.4rem;
    border-bottom: 2px solid {BORDER_LIGHT};
    margin-bottom: 0.8rem;
  }}

  /* ── Empty state ── */
  .empty-state {{
    text-align: center;
    padding: 3rem 1rem;
    color: {GREEN_MID};
  }}
  .empty-state .icon {{ font-size: 3rem; margin-bottom: 0.5rem; }}
  .empty-state p {{ font-size: 0.95rem; }}

  /* ── Download button ── */
  .stDownloadButton button {{
    background: {GREEN_DARK} !important;
    color: {WHITE} !important;
    border: none !important;
    border-radius: 24px !important;
    font-weight: 600 !important;
    width: 100% !important;
    padding: 0.6rem !important;
    margin-top: 0.5rem !important;
  }}
  .stDownloadButton button:hover {{ background: {GREEN_MID} !important; }}

  /* ── Padding contenido principal ── */
  div[data-testid="stVerticalBlock"] > div {{
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
  }}
  .ceo-hero, .metrics-bar, .stale-banner {{
    margin-left: -1.5rem;
    margin-right: -1.5rem;
  }}

  /* ── Mobile ── */
  @media (max-width: 768px) {{
    .ceo-hero {{
      flex-direction: column;
      align-items: flex-start;
      gap: 0.7rem;
      padding: 1rem 1.2rem 0.9rem;
    }}
    .ceo-hero::before {{ display: none; }}
    .ceo-hero-logo img {{ height: 38px; }}
    .ceo-hero-text h1 {{ font-size: 1.1rem !important; }}
    .ceo-hero-text p {{ font-size: 0.78rem; }}
    .ceo-hero-dates {{ align-items: flex-start; }}
    .ceo-hero-date {{ font-size: 0.7rem; padding: 0.3rem 0.75rem; }}
    .ceo-hero-csv-date {{ font-size: 0.67rem; }}
    .metrics-bar {{
      padding: 0.6rem 0.8rem;
      flex-wrap: wrap;
    }}
    .metric-pill {{
      flex: 1 1 45%;
      border-right: none !important;
      border-bottom: 1px solid {BORDER_LIGHT};
      padding: 0.4rem 0.3rem;
    }}
    .metric-num {{ font-size: 1.4rem; }}
    .metric-num-sm {{ font-size: 1.1rem; }}
    .metric-label {{ font-size: 0.65rem; }}
    .opp-card {{ padding: 0.8rem 0.9rem; border-radius: 10px; }}
    .opp-title {{ font-size: 0.9rem; }}
    .opp-meta {{ flex-direction: column; gap: 0.2rem; font-size: 0.75rem; }}
    .section-header {{ font-size: 0.72rem; }}
    div[data-testid="stVerticalBlock"] > div {{
      padding-left: 0.8rem !important;
      padding-right: 0.8rem !important;
    }}
    .stale-banner {{
      margin-left: -0.8rem;
      margin-right: -0.8rem;
    }}
  }}
  @media (max-width: 480px) {{
    .ceo-hero-text h1 {{ font-size: 0.95rem !important; }}
    .metric-pill {{ flex: 1 1 48%; }}
    .opp-card {{ margin-bottom: 0.6rem; }}
  }}

  /* ── Hint mobile sidebar ── */
  .mobile-hint {{ display: none; }}
  @media (max-width: 768px) {{
    .mobile-hint {{
      display: flex;
      align-items: center;
      gap: 0.6rem;
      background: {GREEN_DARK};
      color: {WHITE};
      font-size: 0.82rem;
      font-weight: 500;
      padding: 0.55rem 1.2rem;
      border-bottom: 2px solid {GREEN_MID};
      margin-left: -0.8rem;
      margin-right: -0.8rem;
    }}
    .mobile-hint .arrow-icon {{
      background: {GREEN_ACCENT};
      border-radius: 6px;
      padding: 2px 8px;
      font-size: 1rem;
      font-weight: 700;
      line-height: 1.4;
    }}
  }}
</style>
""", unsafe_allow_html=True)

# ── Datos ─────────────────────────────────────────────────────────────────────

MESES_ES = {
    1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
    7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic",
}

def fmt_date_es(dt: datetime) -> str:
    return f"{dt.day} {MESES_ES[dt.month]} {dt.year}"

def csv_mtime() -> datetime | None:
    if CSV_PATH.exists():
        return datetime.fromtimestamp(CSV_PATH.stat().st_mtime)
    return None

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

    # Columnas existentes con limpieza estándar
    for col in ["Prioridad", "Afinidad", "Tipo", "Región", "Fecha límite"]:
        df[col] = df.get(col, pd.Series(dtype=str)).fillna("—").str.strip()

    # Columnas nuevas opcionales — se crean con default si no existen
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
            df["Monto estimado (USD)"].astype(str).str.replace(",", "").str.replace("$", ""),
            errors="coerce",
        ).fillna(0)

    if "Consultor" not in df.columns:
        df["Consultor"] = "—"
    else:
        df["Consultor"] = df["Consultor"].fillna("—").str.strip()

    return df

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

    prioridad_sel = st.multiselect(
        "Prioridad",
        ["Alta", "Media", "Baja"],
        default=["Alta", "Media"],
    )
    afinidad_sel = st.multiselect(
        "Afinidad",
        ["Individual", "Empresarial", "Ambos"],
        default=["Individual", "Empresarial", "Ambos"],
    )
    estado_sel = st.multiselect(
        "Estado",
        ESTADOS_ORDEN,
        default=[e for e in ESTADOS_ORDEN if e != "Descartada"],
    )

    # Consultor: combinar lista fija + valores del CSV
    consultores_csv = df_full["Consultor"].dropna().unique().tolist()
    consultores_opts = sorted(set(CONSULTORES + consultores_csv))
    consultor_sel = st.multiselect("Consultor", consultores_opts, default=consultores_opts)

    regiones = sorted(df_full["Región"].dropna().unique().tolist())
    region_sel = st.multiselect("Región", regiones, default=regiones)

    paises = sorted(df_full["País"].dropna().unique().tolist())
    pais_sel = st.multiselect("País", paises, default=paises)

    texto = st.text_input("Buscar", placeholder="UNDP, cacao, agroecología…")

    st.divider()
    st.markdown("### ⚙️ Actualizar datos")

    _default_key = (
        st.secrets.get("TAVILY_API_KEY", "")
        if hasattr(st, "secrets") else ""
    ) or os.environ.get("TAVILY_API_KEY", "")

    tavily_key = st.text_input(
        "Tavily API Key",
        type="password",
        value=_default_key,
        help="Opcional — mejora la búsqueda con IA.",
    )

    _is_cloud = not SCRIPT_PATH.exists()
    if _is_cloud:
        st.info(
            "**Actualización automática:** lunes y jueves vía GitHub Actions.\n\n"
            "Para actualizar ahora, abrí una Terminal en tu Mac y ejecutá:\n\n"
            "`/Users/fvillareal/actualizar_y_publicar.sh`",
            icon="ℹ️",
        )
    else:
        if st.button("▶ Buscar nuevas oportunidades", use_container_width=True):
            with st.spinner("Buscando en UNDP, ReliefWeb, FAO, IDB, Devex…"):
                env = os.environ.copy()
                if tavily_key.strip():
                    env["TAVILY_API_KEY"] = tavily_key.strip()
                result = subprocess.run(
                    [sys.executable, str(SCRIPT_PATH)],
                    capture_output=True, text=True, env=env,
                )
            if result.returncode == 0:
                st.success("¡Búsqueda completada!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Error al ejecutar el script:")
                st.code((result.stderr or result.stdout)[-1500:])

    st.divider()
    st.markdown(
        f"<div style='font-size:0.72rem;color:rgba(255,255,255,0.45);text-align:center;'>"
        f"grupo-ceo.com · {date.today().year}</div>",
        unsafe_allow_html=True,
    )

# ── Aplicar filtros ───────────────────────────────────────────────────────────

df = load_data()
if prioridad_sel:
    df = df[df["Prioridad"].isin(prioridad_sel)]
if afinidad_sel:
    df = df[df["Afinidad"].isin(afinidad_sel)]
if estado_sel:
    df = df[df["Estado"].isin(estado_sel)]
if consultor_sel:
    df = df[df["Consultor"].isin(consultor_sel)]
if region_sel:
    df = df[df["Región"].isin(region_sel)]
if pais_sel:
    df = df[df["País"].isin(pais_sel)]
if texto.strip():
    mask = (
        df["Título"].str.contains(texto, case=False, na=False) |
        df["Organización"].str.contains(texto, case=False, na=False)
    )
    df = df[mask]

# ── Ordenamiento ──────────────────────────────────────────────────────────────

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

orden_prio = {"Alta": 0, "Media": 1, "Baja": 2}
df = df.copy()
df["_ord_prio"]  = df["Prioridad"].map(orden_prio).fillna(3)
df["_ord_fecha"] = df["Fecha límite"].apply(parse_deadline)
df = df.sort_values(["_ord_prio", "_ord_fecha"]).drop(columns=["_ord_prio", "_ord_fecha"])

# ── Hero / Header ─────────────────────────────────────────────────────────────

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

# ── Hint mobile ───────────────────────────────────────────────────────────────

st.markdown("""
<div class="mobile-hint">
  <span class="arrow-icon">☰</span>
  <span>Tocá el ícono de arriba a la izquierda para <strong>filtrar oportunidades</strong></span>
</div>
""", unsafe_allow_html=True)

# ── Banner datos desactualizados ──────────────────────────────────────────────

if days_old > 7:
    st.markdown(
        '<div class="stale-banner">'
        f'⚠️ Los datos tienen más de {days_old} días. Considerá ejecutar una nueva búsqueda.'
        '</div>',
        unsafe_allow_html=True,
    )

# ── Métricas ──────────────────────────────────────────────────────────────────

total     = len(df)
n_alta    = len(df[df["Prioridad"] == "Alta"])
n_ind     = len(df[df["Afinidad"].isin(["Individual", "Ambos"])])
n_empresa = len(df[df["Afinidad"].isin(["Empresarial", "Ambos"])])
pipeline  = df["Monto estimado (USD)"].sum()
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

# ── Cards ─────────────────────────────────────────────────────────────────────

if df.empty:
    st.markdown("""
    <div class="empty-state">
      <div class="icon">🌿</div>
      <p>No hay oportunidades con los filtros actuales.<br>
      Ajustá los filtros o ejecutá una nueva búsqueda.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    grupo_actual = None
    for _, row in df.iterrows():
        prio   = row.get("Prioridad", "Media")
        pconf  = PRIO_MAP.get(prio, PRIO_MAP["Media"])
        estado = row.get("Estado", "Identificada")
        econf  = ESTADO_CHIPS.get(estado, ESTADO_CHIPS["Identificada"])

        if prio != grupo_actual:
            grupo_actual = prio
            labels = {
                "Alta":  "🔴 Prioridad Alta",
                "Media": "🟡 Prioridad Media",
                "Baja":  "🟢 Otras oportunidades",
            }
            st.markdown(
                f'<div class="section-header">{labels.get(prio, prio)}</div>',
                unsafe_allow_html=True,
            )

        titulo    = row.get("Título", "Sin título")
        org       = row.get("Organización", "—")
        region    = row.get("Región", "—")
        pais      = row.get("País", "—")
        fecha     = row.get("Fecha límite", "—")
        enlace    = row.get("Enlace", "")
        afin      = row.get("Afinidad", "—")
        consultor = row.get("Consultor", "—")
        monto     = float(row.get("Monto estimado (USD)", 0) or 0)

        descartada = (estado == "Descartada")
        title_cls  = "opp-title-descartada" if descartada else "opp-title"

        chip_prio_cls = {"Alta": "chip-alta", "Media": "chip-media", "Baja": "chip-baja"}.get(prio, "chip-mid")

        link_html = (
            f'<a href="{enlace}" target="_blank">🔗 Ver convocatoria</a>'
            if enlace.startswith("http") else "—"
        )

        pais_chip = (
            f'<span class="chip chip-mid">📍 {pais}</span>'
            if pais and pais != "—" else ""
        )
        monto_chip = (
            f'<span class="chip chip-monto">💰 ${monto:,.0f}</span>'
            if monto > 0 else ""
        )
        consultor_chip = (
            f'<span class="chip chip-mid">👤 {consultor}</span>'
            if consultor and consultor != "—" else ""
        )

        st.markdown(f"""
        <div class="opp-card" style="border-left-color:{pconf['border']}; background:{pconf['bg']}08;">
          <div class="{title_cls}">{titulo}</div>
          <div class="opp-meta">
            <span>🏛 <strong>{org}</strong></span>
            <span>📍 {region}</span>
            <span>📅 <strong>{fecha}</strong></span>
          </div>
          <div class="opp-chips">
            <span class="chip chip-dark">{afin}</span>
            <span class="chip {chip_prio_cls}">{pconf['badge']} {prio}</span>
            <span class="chip" style="background:{econf['bg']};color:{econf['color']};">{estado}</span>
            {pais_chip}
            {monto_chip}
            {consultor_chip}
            <span class="opp-link">{link_html}</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

# ── Descarga ──────────────────────────────────────────────────────────────────

export_cols = [
    "Título", "Organización", "Tipo", "Región", "País",
    "Fecha límite", "Enlace", "Afinidad", "Prioridad",
    "Estado", "Monto estimado (USD)", "Consultor",
]
export_df = df[[c for c in export_cols if c in df.columns]]

st.download_button(
    label="⬇️ Descargar resultados filtrados (CSV)",
    data=export_df.to_csv(index=False).encode("utf-8"),
    file_name=f"ceo_consultorias_{date.today()}.csv",
    mime="text/csv",
)
