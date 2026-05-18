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
# Extraída directamente del sitio grupo-ceo.com
GREEN_DARK   = "#1A3D2E"   # verde bosque oscuro — textos, cards, logo
GREEN_MID    = "#3A7D58"   # verde medio — bordes, hover
GREEN_ACCENT = "#4CAF82"   # verde acento — links, highlights, "Grupo CEO" text
GREEN_LIGHT  = "#6DB86B"   # verde claro — logo interior, gradientes suaves
BG_SAGE      = "#EEF6EE"   # sage muy claro — fondo de secciones
BG_HERO_FROM = "#C8E8CA"   # gradiente hero inicio
BG_HERO_TO   = "#88C5B0"   # gradiente hero fin
WHITE        = "#FFFFFF"
TEXT_DARK    = "#1A1A1A"
TEXT_BODY    = "#3D3D3D"
BORDER_LIGHT = "#D4EAD6"

# Prioridades
COLOR_ALTA   = {"bg": "#FFE5E5", "border": "#D32F2F", "badge": "🔴"}
COLOR_MEDIA  = {"bg": "#FFF8E1", "border": "#F9A825", "badge": "🟡"}
COLOR_BAJA   = {"bg": "#E8F5E9", "border": "#388E3C", "badge": "🟢"}
PRIO_MAP     = {"Alta": COLOR_ALTA, "Media": COLOR_MEDIA, "Baja": COLOR_BAJA}

# ── Logo en base64 ────────────────────────────────────────────────────────────

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
  #MainMenu, footer, header {{ visibility: hidden; }}
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
  .ceo-hero-logo img {{
    height: 56px;
    width: auto;
  }}
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
  .ceo-hero-date {{
    background: {GREEN_DARK};
    color: {WHITE};
    padding: 0.4rem 1rem;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 500;
    white-space: nowrap;
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
  .metric-label {{
    font-size: 0.72rem;
    color: #777;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 2px;
  }}

  /* ── Content area — fondo aplicado al main, sin div wrapper ── */
  .main {{
    background: {BG_SAGE} !important;
  }}
  .main .block-container {{
    padding: 0 0 2rem 0 !important;
    max-width: 100% !important;
  }}
  /* Padding interno para las cards */
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
  .chip-dark {{
    background: {GREEN_DARK};
    color: {WHITE};
  }}
  .chip-mid {{
    background: {BG_SAGE};
    color: {GREEN_DARK};
    border: 1px solid {BORDER_LIGHT};
  }}
  .chip-alta {{ background: #FFE5E5; color: #B71C1C; }}
  .chip-media {{ background: #FFF8E1; color: #E65100; }}
  .chip-baja {{ background: #E8F5E9; color: #1B5E20; }}
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
  .stDownloadButton button:hover {{
    background: {GREEN_MID} !important;
  }}

  /* ── Padding contenido principal ── */
  div[data-testid="stVerticalBlock"] > div {{
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
  }}
  /* Hero y metrics ocupan el ancho completo sin padding lateral */
  .ceo-hero, .metrics-bar {{
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
    .ceo-hero-date {{ font-size: 0.7rem; padding: 0.3rem 0.75rem; }}
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
    .metric-label {{ font-size: 0.65rem; }}
    .opp-card {{ padding: 0.8rem 0.9rem; border-radius: 10px; }}
    .opp-title {{ font-size: 0.9rem; }}
    .opp-meta {{ flex-direction: column; gap: 0.2rem; font-size: 0.75rem; }}
    .section-header {{ font-size: 0.72rem; }}
    div[data-testid="stVerticalBlock"] > div {{
      padding-left: 0.8rem !important;
      padding-right: 0.8rem !important;
    }}
  }}

  @media (max-width: 480px) {{
    .ceo-hero-text h1 {{ font-size: 0.95rem !important; }}
    .metric-pill {{ flex: 1 1 48%; }}
    .opp-card {{ margin-bottom: 0.6rem; }}
  }}
</style>
""", unsafe_allow_html=True)

# ── Datos ─────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    if not CSV_PATH.exists():
        return pd.DataFrame(columns=[
            "Título", "Organización", "Tipo", "Región",
            "Fecha límite", "Enlace", "Afinidad", "Prioridad",
        ])
    df = pd.read_csv(CSV_PATH)
    df.columns = df.columns.str.strip()
    for col in ["Prioridad", "Afinidad", "Tipo", "Región", "Fecha límite"]:
        df[col] = df.get(col, pd.Series(dtype=str)).fillna("—").str.strip()
    return df

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    if LOGO_B64:
        st.markdown(
            f"<div style='padding:0.4rem 0 1rem'>"
            f"<img src='data:image/png;base64,{LOGO_B64}' style='height:44px;filter:brightness(0) invert(1);'>"
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
    regiones = sorted(df_full["Región"].dropna().unique().tolist())
    region_sel = st.multiselect("Región", regiones, default=regiones)
    texto = st.text_input("Buscar", placeholder="UNDP, cacao, agroecología…")

    st.divider()
    st.markdown("### ⚙️ Actualizar datos")

    # API key: primero st.secrets (nube), luego variable de entorno (local)
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

    # El botón de búsqueda solo funciona en local (tiene acceso al script y al disco)
    _is_cloud = not SCRIPT_PATH.exists()
    if _is_cloud:
        st.info(
            "**Actualización automática:** lunes y jueves a las 8 AM desde tu Mac.\n\n"
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
if region_sel:
    df = df[df["Región"].isin(region_sel)]
if texto.strip():
    mask = (
        df["Título"].str.contains(texto, case=False, na=False) |
        df["Organización"].str.contains(texto, case=False, na=False)
    )
    df = df[mask]

MONTH_ES = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "ene": 1, "abr": 4, "ago": 8, "dic": 12,
}

def parse_deadline(raw: str) -> datetime:
    """Convierte la fecha de cierre a datetime para ordenamiento.
    Las fechas no reconocidas van al final (año 2099)."""
    s = (raw or "").strip().lower()
    # ISO: 2026-05-18
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    # DD-Mmm-YYYY: 18-may-2026
    m = re.search(r"(\d{1,2})-([a-z]{3})-(\d{4})", s)
    if m:
        mon = MONTH_ES.get(m.group(2))
        if mon:
            try:
                return datetime(int(m.group(3)), mon, int(m.group(1)))
            except ValueError:
                pass
    # Sin fecha reconocible → al final
    return datetime(2099, 12, 31)

orden_prio = {"Alta": 0, "Media": 1, "Baja": 2}
df = df.copy()
df["_ord_prio"]  = df["Prioridad"].map(orden_prio).fillna(3)
df["_ord_fecha"] = df["Fecha límite"].apply(parse_deadline)
df = df.sort_values(["_ord_prio", "_ord_fecha"]).drop(columns=["_ord_prio", "_ord_fecha"])

# ── Hero / Header ─────────────────────────────────────────────────────────────

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
  <div class="ceo-hero-date">📅 {date.today().strftime('%d %b %Y')}</div>
</div>
""", unsafe_allow_html=True)

# ── Métricas ──────────────────────────────────────────────────────────────────

total     = len(df)
n_alta    = len(df[df["Prioridad"] == "Alta"])
n_ind     = len(df[df["Afinidad"].isin(["Individual", "Ambos"])])
n_empresa = len(df[df["Afinidad"].isin(["Empresarial", "Ambos"])])

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
</div>
""", unsafe_allow_html=True)

# ── Cards ─────────────────────────────────────────────────────────────────────

if df.empty:
    st.markdown("""
    <div class="empty-state">
      <div class="icon">🌿</div>
      <p>No hay oportunidades con los filtros actuales.<br>
      Ajusta los filtros o ejecuta una nueva búsqueda.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    grupo_actual = None
    for _, row in df.iterrows():
        prio  = row.get("Prioridad", "Media")
        pconf = PRIO_MAP.get(prio, PRIO_MAP["Media"])

        # Separador de grupo por prioridad
        if prio != grupo_actual:
            grupo_actual = prio
            labels = {"Alta": "🔴 Prioridad Alta", "Media": "🟡 Prioridad Media", "Baja": "🟢 Otras oportunidades"}
            st.markdown(f'<div class="section-header">{labels.get(prio, prio)}</div>', unsafe_allow_html=True)

        titulo = row.get("Título", "Sin título")
        org    = row.get("Organización", "—")
        tipo   = row.get("Tipo", "—")
        region = row.get("Región", "—")
        fecha  = row.get("Fecha límite", "—")
        enlace = row.get("Enlace", "")
        afin   = row.get("Afinidad", "—")

        chip_prio_cls = {"Alta": "chip-alta", "Media": "chip-media", "Baja": "chip-baja"}.get(prio, "chip-mid")

        link_html = (
            f'<a href="{enlace}" target="_blank">🔗 Ver convocatoria</a>'
            if enlace.startswith("http") else "—"
        )

        st.markdown(f"""
        <div class="opp-card" style="border-left-color:{pconf['border']}; background:{pconf['bg']}08;">
          <div class="opp-title">{titulo}</div>
          <div class="opp-meta">
            <span>🏛 <strong>{org}</strong></span>
            <span>📍 {region}</span>
            <span>📅 <strong>{fecha}</strong></span>
          </div>
          <div class="opp-chips">
            <span class="chip chip-dark">{tipo}</span>
            <span class="chip chip-mid">{afin}</span>
            <span class="chip {chip_prio_cls}">{pconf['badge']} {prio}</span>
            <span class="opp-link">{link_html}</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

# ── Descarga ──────────────────────────────────────────────────────────────────

st.download_button(
    label="⬇️ Descargar resultados filtrados (CSV)",
    data=df.drop(columns=["_ord"], errors="ignore").to_csv(index=False).encode("utf-8"),
    file_name=f"ceo_consultorias_{date.today()}.csv",
    mime="text/csv",
)
