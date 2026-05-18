import base64
import html as _html
import os
import re
import subprocess
import sys
from datetime import date, datetime
from io import BytesIO
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

# Estado → chip
ESTADO_CHIPS = {
    "Identificada": {"bg": "#F5F5F5", "color": "#616161"},
    "En análisis":  {"bg": "#E3F2FD", "color": "#1565C0"},
    "Postulada":    {"bg": "#FFF3E0", "color": "#E65100"},
    "Ganada":       {"bg": "#E8F5E9", "color": "#2E7D32"},
    "Descartada":   {"bg": "#FFEBEE", "color": "#B71C1C"},
}
ESTADOS_ORDEN = ["Identificada", "En análisis", "Postulada", "Ganada", "Descartada"]

# Regiones agrupadas (filtro del sidebar)
REGIONES_GRUPO = ["Cono Sur", "América Latina", "Caribe", "Europa", "Otros"]

# Palabras clave para clasificación regional
_RG_CONO_SUR = ["cono sur", "argentina", "chile", "uruguay", "paraguay"]
_RG_CARIBE   = [
    "caribe", "caribbean", "trinidad", "tobago", "jamaica", "haiti",
    "cuba", "dominicana", "barbados", "bahamas", "aruba", "curazao",
    "guadalupe", "martinica", "saint lucia", "antigua", "grenada",
    "puerto rico", "guyana", "surinam",
]
_RG_EUROPA = [
    "europa", "europe", "european", "roma", "rome", "ginebra", "geneva",
    "bruselas", "brussels", "paris", "viena", "vienna", "madrid",
    "london", "londres", "hague", "amsterdam", "berlin", "berna", "berne",
    "copenhague", "estocolmo", "oslo", "lisboa",
]
_RG_ALC = [
    "latinoam", "latin am", "centroam", "central am", "américas",
    "méxico", "mexico", "colombia", "perú", "peru", "ecuador",
    "venezuela", "bolivia", "brasil", "brazil", "nicaragua",
    "honduras", "guatemala", "el salvador", "costa rica", "panamá",
    "panama", "alc", "lac", "america del sur", "america latina",
    "sudamérica", "sudamerica", "andina", "andino",
]

# Todos los países del mundo (para el editor de datos)
TODOS_PAISES = sorted([
    "—",
    "Afganistán", "Albania", "Alemania", "Andorra", "Angola",
    "Antigua y Barbuda", "Arabia Saudita", "Argelia", "Argentina", "Armenia",
    "Australia", "Austria", "Azerbaiyán", "Bahamas", "Bahrein",
    "Bangladesh", "Barbados", "Bélgica", "Belice", "Benín",
    "Bolivia", "Bosnia y Herzegovina", "Botsuana", "Brasil", "Brunéi",
    "Bulgaria", "Burkina Faso", "Burundi", "Bután", "Cabo Verde",
    "Camboya", "Camerún", "Canadá", "Chad", "Chile", "China",
    "Chipre", "Colombia", "Comoras", "Congo", "Corea del Norte",
    "Corea del Sur", "Costa de Marfil", "Costa Rica", "Croacia",
    "Cuba", "Dinamarca", "Djibouti", "Dominica", "Ecuador",
    "Egipto", "El Salvador", "Emiratos Árabes Unidos", "Eritrea",
    "Eslovaquia", "Eslovenia", "España", "Estados Unidos", "Estonia",
    "Etiopía", "Fiyi", "Filipinas", "Finlandia", "Francia",
    "Gabón", "Gambia", "Georgia", "Ghana", "Granada",
    "Grecia", "Guatemala", "Guinea", "Guinea-Bisáu", "Guinea Ecuatorial",
    "Guyana", "Haití", "Honduras", "Hungría", "India",
    "Indonesia", "Irak", "Irán", "Irlanda", "Islandia",
    "Islas Marshall", "Islas Salomón", "Israel", "Italia", "Jamaica",
    "Japón", "Jordania", "Kazajistán", "Kenia", "Kirguistán",
    "Kiribati", "Kuwait", "Laos", "Lesoto", "Letonia",
    "Líbano", "Liberia", "Libia", "Liechtenstein", "Lituania",
    "Luxemburgo", "Madagascar", "Malasia", "Malaui", "Maldivas",
    "Malí", "Malta", "Marruecos", "Mauricio", "Mauritania",
    "México", "Micronesia", "Moldavia", "Mónaco", "Mongolia",
    "Montenegro", "Mozambique", "Namibia", "Nauru", "Nepal",
    "Nicaragua", "Níger", "Nigeria", "Noruega", "Nueva Zelanda",
    "Omán", "Países Bajos", "Pakistán", "Palaos", "Panamá",
    "Papúa Nueva Guinea", "Paraguay", "Perú", "Polonia", "Portugal",
    "Qatar", "Reino Unido", "República Centroafricana", "República Checa",
    "República del Congo", "República Democrática del Congo",
    "República Dominicana", "Ruanda", "Rumanía", "Rusia",
    "Samoa", "San Cristóbal y Nieves", "San Marino",
    "San Vicente y las Granadinas", "Santa Lucía", "Santo Tomé y Príncipe",
    "Senegal", "Serbia", "Seychelles", "Sierra Leona", "Singapur",
    "Siria", "Somalia", "Sri Lanka", "Suazilandia", "Sudáfrica",
    "Sudán", "Sudán del Sur", "Suecia", "Suiza", "Surinam",
    "Tailandia", "Tanzania", "Tayikistán", "Timor Oriental", "Togo",
    "Tonga", "Trinidad y Tobago", "Túnez", "Turkmenistán", "Turquía",
    "Tuvalu", "Ucrania", "Uganda", "Uruguay", "Uzbekistán",
    "Vanuatu", "Venezuela", "Vietnam", "Yemen", "Zambia", "Zimbabue",
    # Entradas regionales
    "Regional", "Global", "América Latina", "América Central",
    "América del Sur", "Caribe", "Centroamérica",
])

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
MESES_LARGO = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
    7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def esc(text) -> str:
    """Escapa HTML y corchetes para evitar que Markdown rompa el renderizado."""
    s = _html.escape(str(text or "—"), quote=True)
    return s.replace("[", "&#91;").replace("]", "&#93;")

def fmt_date_es(dt: datetime) -> str:
    return f"{dt.day} {MESES_ES[dt.month]} {dt.year}"

def csv_mtime() -> datetime | None:
    return datetime.fromtimestamp(CSV_PATH.stat().st_mtime) if CSV_PATH.exists() else None

def get_logo_b64() -> str:
    return base64.b64encode(LOGO_PATH.read_bytes()).decode() if LOGO_PATH.exists() else ""

def agrupar_region(region: str) -> str:
    r = (region or "").lower()
    for kw in _RG_CONO_SUR:
        if kw in r:
            return "Cono Sur"
    for kw in _RG_CARIBE:
        if kw in r:
            return "Caribe"
    for kw in _RG_EUROPA:
        if kw in r:
            return "Europa"
    for kw in _RG_ALC:
        if kw in r:
            return "América Latina"
    return "Otros"

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

    for col, default in [("Estado", "Identificada"), ("País", "—"), ("Consultor", "—")]:
        if col not in df.columns:
            df[col] = default
        else:
            df[col] = df[col].fillna(default).str.strip()

    if "Observaciones" not in df.columns:
        df["Observaciones"] = ""
    else:
        df["Observaciones"] = df["Observaciones"].fillna("")

    if "Monto estimado (USD)" not in df.columns:
        df["Monto estimado (USD)"] = 0.0
    else:
        df["Monto estimado (USD)"] = pd.to_numeric(
            df["Monto estimado (USD)"].astype(str)
                .str.replace(",", "").str.replace("$", "").str.strip(),
            errors="coerce",
        ).fillna(0.0)

    # Región agrupada para filtro
    df["_region_grupo"] = df["Región"].apply(agrupar_region)
    return df

MONTH_ES_PARSE = {
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
        mon = MONTH_ES_PARSE.get(m.group(2))
        if mon:
            try:
                return datetime(int(m.group(3)), mon, int(m.group(1)))
            except ValueError:
                pass
    return datetime(2099, 12, 31)

def save_df(df: pd.DataFrame) -> None:
    export_cols = [
        "Título", "Organización", "Tipo", "Región", "País",
        "Fecha límite", "Enlace", "Afinidad", "Prioridad",
        "Estado", "Monto estimado (USD)", "Consultor", "Observaciones",
    ]
    df[[c for c in export_cols if c in df.columns]].to_csv(CSV_PATH, index=False)
    st.cache_data.clear()

# ── PDF ───────────────────────────────────────────────────────────────────────

def generar_pdf(df_all: pd.DataFrame, hoy: date) -> bytes:
    from fpdf import FPDF  # lazy import

    # RGB CEO palette
    RD, GD, BD = 26, 61, 46       # GREEN_DARK
    RM, GM, BM = 58, 125, 88      # GREEN_MID
    RA, GA, BA = 76, 175, 130     # GREEN_ACCENT
    RS, GS, BS = 238, 246, 238    # BG_SAGE

    def safe(text, max_chars=None) -> str:
        s = (str(text or "-")
             .replace("—", "-").replace("–", "-")
             .replace("·", ".").replace("…", "..."))
        s = s.encode("latin-1", "replace").decode("latin-1")
        if max_chars and len(s) > max_chars:
            s = s[:max_chars - 1] + "."
        return s

    df_active = df_all[df_all["Estado"] != "Descartada"].copy()
    orden_prio = {"Alta": 0, "Media": 1, "Baja": 2}
    df_active["_op"] = df_active["Prioridad"].map(orden_prio).fillna(3)
    df_active["_of"] = df_active["Fecha límite"].apply(parse_deadline)
    df_active = df_active.sort_values(["_op", "_of"])

    total_act  = len(df_active)
    pipeline_t = df_active["Monto estimado (USD)"].sum()
    n_alta_t   = len(df_active[df_active["Prioridad"] == "Alta"])
    n_proc_t   = len(df_active[df_active["Estado"].isin(["Postulada", "Ganada"])])

    class PDF(FPDF):
        def header(self):
            if self.page_no() == 1:
                return
            self.set_fill_color(RD, GD, BD)
            self.rect(0, 0, 297, 14, "F")
            self.set_font("Helvetica", "B", 8)
            self.set_text_color(255, 255, 255)
            self.set_xy(10, 3)
            self.cell(0, 8, safe(f"GRUPO CEO - Informe de Pipeline | {hoy.day} de {MESES_LARGO[hoy.month]} de {hoy.year}"))
            self.ln(14)

        def footer(self):
            self.set_y(-12)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(160, 160, 160)
            self.cell(0, 5, safe(f"Pagina {self.page_no()} - Confidencial | Uso interno Grupo CEO"), align="C")

        def section_title(self, title: str, r=RD, g=GD, b=BD):
            self.set_fill_color(r, g, b)
            self.set_text_color(255, 255, 255)
            self.set_font("Helvetica", "B", 9)
            self.cell(0, 8, f"  {safe(title)}", ln=True, fill=True)
            self.ln(2)

        def opps_table(self, df_t, col_w=None):
            if df_t.empty:
                self.set_font("Helvetica", "I", 8)
                self.set_text_color(140, 140, 140)
                self.cell(0, 7, "  Sin oportunidades en esta categoría.", ln=True)
                return

            if col_w is None:
                col_w = [5, 82, 38, 25, 22, 30, 27, 38]
            headers = ["#", "Título", "Organización", "País", "Fecha límite", "Monto USD", "Estado", "Consultor"]

            # Header row
            self.set_fill_color(RD, GD, BD)
            self.set_text_color(255, 255, 255)
            self.set_font("Helvetica", "B", 7)
            for h, w in zip(headers, col_w):
                self.cell(w, 7, h, border=1, fill=True)
            self.ln()

            alt = True
            for i, (_, row) in enumerate(df_t.iterrows(), 1):
                monto = float(row.get("Monto estimado (USD)", 0) or 0)
                monto_s = f"${monto:,.0f}" if monto > 0 else "-"
                vals = [
                    str(i),
                    safe(row.get("Título", "—"), 55),
                    safe(row.get("Organización", "—"), 25),
                    safe(row.get("País", "—"), 16),
                    safe(row.get("Fecha límite", "—"), 14),
                    monto_s,
                    safe(row.get("Estado", "—"), 17),
                    safe(row.get("Consultor", "—"), 24),
                ]
                self.set_fill_color(RS, GS, BS) if alt else self.set_fill_color(255, 255, 255)
                self.set_text_color(30, 30, 30)
                self.set_font("Helvetica", "", 7)
                row_h = 6
                for v, w in zip(vals, col_w):
                    self.cell(w, row_h, v, border=1, fill=True)
                self.ln()
                alt = not alt

    pdf = PDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.set_margins(10, 16, 10)

    # ── PORTADA ───────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(RD, GD, BD)
    pdf.rect(0, 0, 297, 210, "F")

    # Franja accent
    pdf.set_fill_color(RA, GA, BA)
    pdf.rect(0, 150, 297, 6, "F")

    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 42)
    pdf.set_xy(20, 55)
    pdf.cell(0, 18, "GRUPO CEO", ln=True)

    pdf.set_font("Helvetica", "", 22)
    pdf.set_xy(20, 82)
    pdf.cell(0, 11, safe("Informe de Pipeline de Consultoría"), ln=True)

    pdf.set_font("Helvetica", "", 14)
    pdf.set_xy(20, 102)
    pdf.cell(0, 8, safe(f"{hoy.day} de {MESES_LARGO[hoy.month]} de {hoy.year}"), ln=True)

    pdf.set_text_color(RA, GA, BA)
    pdf.set_font("Helvetica", "I", 11)
    pdf.set_xy(20, 118)
    pdf.cell(0, 7, "Análisis para socios · Confidencial · Uso interno", ln=True)

    # Mini summary on cover
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(RA, GA, BA)
    summary_items = [
        (str(total_act), "Oportunidades activas"),
        (str(n_alta_t), "Alta prioridad"),
        (str(n_proc_t), "En proceso"),
        (f"${pipeline_t:,.0f}", "Pipeline USD"),
    ]
    box_w, box_h = 58, 22
    x0 = 20
    for i, (val, label) in enumerate(summary_items):
        bx = x0 + i * (box_w + 5)
        pdf.rect(bx, 165, box_w, box_h, "FD")
        pdf.set_text_color(RD, GD, BD)
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_xy(bx + 3, 167)
        pdf.cell(box_w - 6, 9, safe(val))
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(80, 80, 80)
        pdf.set_xy(bx + 3, 178)
        pdf.cell(box_w - 6, 5, safe(label))

    # ── RESUMEN EJECUTIVO ─────────────────────────────────────────────────────
    pdf.add_page()
    pdf.section_title("RESUMEN EJECUTIVO")

    # Tabla por estado
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(RD, GD, BD)
    pdf.cell(0, 7, "Distribución por Estado", ln=True)

    estado_counts = df_active["Estado"].value_counts()
    pdf.set_fill_color(RD, GD, BD)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 8)
    for h, w in [("Estado", 45), ("N°", 18), ("% del total", 28), ("Pipeline estimado USD", 45)]:
        pdf.cell(w, 7, h, border=1, fill=True)
    pdf.ln()
    alt = True
    for estado in ESTADOS_ORDEN:
        cnt = estado_counts.get(estado, 0)
        if cnt == 0:
            continue
        pct = f"{cnt / total_act * 100:.1f}%" if total_act > 0 else "-"
        mont = df_active[df_active["Estado"] == estado]["Monto estimado (USD)"].sum()
        mont_s = f"${mont:,.0f}" if mont > 0 else "-"
        pdf.set_fill_color(RS, GS, BS) if alt else pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(30, 30, 30)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(45, 6, safe(estado), border=1, fill=True)
        pdf.cell(18, 6, str(cnt), border=1, fill=True)
        pdf.cell(28, 6, pct, border=1, fill=True)
        pdf.cell(45, 6, mont_s, border=1, fill=True)
        pdf.ln()
        alt = not alt

    pdf.ln(6)

    # Tabla por consultor
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(RD, GD, BD)
    pdf.cell(0, 7, safe("Distribución por Consultor"), ln=True)

    pdf.set_fill_color(RD, GD, BD)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 8)
    for h, w in [("Consultor", 55), ("Asignadas", 22), ("Alta prioridad", 28), ("En proceso", 28), ("Pipeline USD", 40)]:
        pdf.cell(w, 7, h, border=1, fill=True)
    pdf.ln()

    df_asig = df_active[df_active["Consultor"] != "—"]
    sin_asig_n = len(df_active[df_active["Consultor"] == "—"])
    alt = True
    for nombre in CONSULTORES[1:]:
        sub = df_asig[df_asig["Consultor"] == nombre]
        if sub.empty:
            continue
        n_alt_c = len(sub[sub["Prioridad"] == "Alta"])
        n_pro_c = len(sub[sub["Estado"].isin(["En análisis", "Postulada", "Ganada"])])
        pipe_c  = sub["Monto estimado (USD)"].sum()
        pdf.set_fill_color(RS, GS, BS) if alt else pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(30, 30, 30)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(55, 6, safe(nombre), border=1, fill=True)
        pdf.cell(22, 6, str(len(sub)), border=1, fill=True)
        pdf.cell(28, 6, str(n_alt_c), border=1, fill=True)
        pdf.cell(28, 6, str(n_pro_c), border=1, fill=True)
        pdf.cell(40, 6, f"${pipe_c:,.0f}" if pipe_c > 0 else "-", border=1, fill=True)
        pdf.ln()
        alt = not alt

    if sin_asig_n > 0:
        pdf.set_fill_color(255, 248, 225)
        pdf.set_text_color(100, 60, 0)
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(55, 6, "Sin asignar", border=1, fill=True)
        pdf.cell(22, 6, str(sin_asig_n), border=1, fill=True)
        pdf.cell(28, 6, "-", border=1, fill=True)
        pdf.cell(28, 6, "-", border=1, fill=True)
        pdf.cell(40, 6, "-", border=1, fill=True)
        pdf.ln()

    # ── PIPELINE ACTIVO — ALTA PRIORIDAD ─────────────────────────────────────
    df_alta = df_active[df_active["Prioridad"] == "Alta"]
    pdf.add_page()
    pdf.section_title("PIPELINE ACTIVO — ALTA PRIORIDAD", r=180, g=0, b=0)
    pdf.opps_table(df_alta)

    # ── EN PROCESO ────────────────────────────────────────────────────────────
    df_proc = df_active[df_active["Estado"].isin(["En análisis", "Postulada"])]
    pdf.add_page()
    pdf.section_title(safe("EN PROCESO — EN ANÁLISIS Y POSTULADAS"), r=RM, g=GM, b=BM)
    pdf.opps_table(df_proc)

    # ── PIPELINE POTENCIAL ────────────────────────────────────────────────────
    df_pot = df_active[df_active["Estado"] == "Identificada"]
    pdf.add_page()
    pdf.section_title("PIPELINE POTENCIAL — IDENTIFICADAS", r=RD, g=GD, b=BD)
    pdf.opps_table(df_pot)

    # ── GANADAS ───────────────────────────────────────────────────────────────
    df_gan = df_active[df_active["Estado"] == "Ganada"]
    if not df_gan.empty:
        pdf.add_page()
        pdf.section_title("GANADAS", r=46, g=125, b=50)
        pdf.opps_table(df_gan)

    return bytes(pdf.output())

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap');

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

  /* ── Sidebar ── */
  section[data-testid="stSidebar"] {{
    background: #0A1A10;
    min-width: 280px !important;
  }}
  section[data-testid="stSidebar"] * {{ color: {WHITE} !important; }}

  /* Inputs y multiselects */
  section[data-testid="stSidebar"] .stTextInput input,
  section[data-testid="stSidebar"] .stMultiSelect div[data-baseweb="select"] {{
    background: rgba(255,255,255,0.12) !important;
    border-color: rgba(255,255,255,0.3) !important;
    border-radius: 8px !important;
    font-size: 0.83rem !important;
  }}

  /* Etiquetas — tipografía mejorada */
  section[data-testid="stSidebar"] label,
  section[data-testid="stSidebar"] .stMultiSelect label {{
    color: rgba(255,255,255,0.9) !important;
    font-weight: 600 !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-bottom: 2px !important;
  }}

  /* Chips de multiselect — compactos y legibles */
  section[data-testid="stSidebar"] [data-baseweb="tag"] {{
    background: rgba(76,175,130,0.35) !important;
    border: 1px solid rgba(76,175,130,0.6) !important;
    border-radius: 14px !important;
    padding: 1px 6px !important;
    margin: 1px !important;
    max-width: 130px !important;
  }}
  section[data-testid="stSidebar"] [data-baseweb="tag"] span {{
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100px !important;
    display: inline-block !important;
  }}
  section[data-testid="stSidebar"] [data-baseweb="tag"] [role="button"] {{
    font-size: 0.7rem !important;
    padding: 0 2px !important;
  }}

  /* Dropdown opciones */
  section[data-testid="stSidebar"] [data-baseweb="popover"] *,
  section[data-testid="stSidebar"] [role="listbox"] * {{
    background: #0A1A10 !important;
    color: {WHITE} !important;
    font-size: 0.82rem !important;
  }}

  /* Divider */
  section[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.12) !important; }}

  /* Botones sidebar */
  section[data-testid="stSidebar"] .stButton button {{
    background: {GREEN_ACCENT} !important; color: {WHITE} !important;
    border: none !important; border-radius: 20px !important;
    font-weight: 600 !important; font-size: 0.85rem !important;
    padding: 0.5rem 1rem !important;
    transition: all 0.2s ease !important;
    letter-spacing: 0.02em;
  }}
  section[data-testid="stSidebar"] .stButton button:hover {{
    background: {GREEN_LIGHT} !important; transform: translateY(-1px);
  }}

  /* Text input buscar */
  section[data-testid="stSidebar"] .stTextInput input {{
    color: {WHITE} !important;
    font-size: 0.85rem !important;
  }}
  section[data-testid="stSidebar"] .stTextInput input::placeholder {{
    color: rgba(255,255,255,0.4) !important;
  }}

  /* ── Hero ── */
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
    padding: 0.65rem 1.5rem; font-size: 0.83rem; font-weight: 500;
    margin-left: -1.5rem; margin-right: -1.5rem;
  }}

  /* ── Metrics bar ── */
  .metrics-bar {{
    background: {WHITE}; border-bottom: 1px solid {BORDER_LIGHT};
    padding: 0.9rem 2rem; display: flex; gap: 0;
  }}
  .metric-pill {{
    flex: 1; text-align: center; padding: 0.4rem 0.5rem;
    border-right: 1px solid {BORDER_LIGHT};
  }}
  .metric-pill:last-child {{ border-right: none; }}
  .metric-num    {{ font-size: 1.8rem; font-weight: 700; color: {GREEN_DARK}; line-height: 1; }}
  .metric-num-sm {{ font-size: 1.25rem; font-weight: 700; color: {GREEN_DARK}; line-height: 1; }}
  .metric-label  {{ font-size: 0.71rem; color: #777; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 3px; }}

  /* ── Content ── */
  .main {{ background: {BG_SAGE} !important; }}
  .main .block-container {{ padding: 0 0 2rem 0 !important; max-width: 100% !important; }}
  .stMarkdown {{ padding: 0 !important; }}

  /* ── Cards ── */
  .opp-card {{
    background: {WHITE}; border-radius: 14px; border: 1px solid {BORDER_LIGHT};
    padding: 0.9rem 1.1rem 0.75rem; margin-bottom: 0.35rem;
    box-shadow: 0 1px 5px rgba(26,61,46,0.07);
    transition: box-shadow 0.2s ease, transform 0.15s ease;
    border-left-width: 4px; border-left-style: solid;
  }}
  .opp-card:hover {{ box-shadow: 0 4px 16px rgba(26,61,46,0.12); transform: translateY(-1px); }}
  .opp-title {{
    font-size: 0.95rem; font-weight: 600; color: {GREEN_DARK};
    margin-bottom: 0.4rem; line-height: 1.35;
  }}
  .opp-title-descartada {{
    font-size: 0.95rem; font-weight: 600; color: #9E9E9E;
    margin-bottom: 0.4rem; line-height: 1.35; text-decoration: line-through;
  }}
  .opp-meta {{
    display: flex; flex-wrap: wrap; gap: 0.3rem 0.9rem;
    font-size: 0.77rem; color: {TEXT_BODY}; margin-bottom: 0.4rem;
  }}
  .opp-meta span {{ display: flex; align-items: center; gap: 0.22rem; }}
  .opp-meta .monto-meta {{ color: #0D47A1; font-weight: 600; }}
  .opp-chips {{ display: flex; flex-wrap: wrap; gap: 0.28rem; align-items: center; }}
  .chip {{
    display: inline-block; padding: 2px 9px; border-radius: 20px;
    font-size: 0.71rem; font-weight: 600; letter-spacing: 0.02em;
  }}
  .chip-dark  {{ background: {GREEN_DARK}; color: {WHITE}; }}
  .chip-mid   {{ background: {BG_SAGE}; color: {GREEN_DARK}; border: 1px solid {BORDER_LIGHT}; }}
  .chip-alta  {{ background: #FFE5E5; color: #B71C1C; }}
  .chip-media {{ background: #FFF8E1; color: #E65100; }}
  .chip-baja  {{ background: #E8F5E9; color: #1B5E20; }}
  .chip-monto {{ background: #E8F4FD; color: #0D47A1; border: 1px solid #BBDEFB; }}
  .chip-link  {{
    background: {GREEN_DARK}; color: {WHITE} !important;
    text-decoration: none; padding: 3px 11px; border-radius: 20px;
    font-size: 0.71rem; font-weight: 600;
  }}
  .chip-link:hover {{ background: {GREEN_MID}; }}

  /* Section headers */
  .section-header {{
    font-size: 0.77rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.08em; color: {GREEN_MID};
    padding: 0.55rem 0 0.35rem; border-bottom: 2px solid {BORDER_LIGHT}; margin-bottom: 0.75rem;
  }}

  /* Empty state */
  .empty-state {{ text-align: center; padding: 3rem 1rem; color: {GREEN_MID}; }}
  .empty-state .icon {{ font-size: 3rem; margin-bottom: 0.5rem; }}

  /* Cartera cards */
  .cartera-card {{
    background: {WHITE}; border-radius: 12px; border: 1px solid {BORDER_LIGHT};
    padding: 1rem 1.2rem; margin-bottom: 0.75rem;
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
    border: none !important; border-radius: 20px !important;
    font-weight: 600 !important; width: 100% !important;
    padding: 0.55rem !important; margin-top: 0.4rem !important;
    font-size: 0.85rem !important;
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
    .metric-num {{ font-size: 1.4rem; }} .metric-num-sm {{ font-size: 1.05rem; }}
    .metric-label {{ font-size: 0.64rem; }}
    .opp-card {{ padding: 0.75rem 0.85rem; border-radius: 10px; }}
    .opp-title {{ font-size: 0.88rem; }}
    .opp-meta {{ flex-direction: column; gap: 0.18rem; font-size: 0.74rem; }}
    .section-header {{ font-size: 0.7rem; }}
    div[data-testid="stVerticalBlock"] > div {{ padding-left: 0.8rem !important; padding-right: 0.8rem !important; }}
    .stale-banner {{ margin-left: -0.8rem; margin-right: -0.8rem; }}
  }}
  @media (max-width: 480px) {{
    .ceo-hero-text h1 {{ font-size: 0.93rem !important; }}
    .metric-pill {{ flex: 1 1 48%; }}
  }}

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
            f"<div style='padding:0.5rem 0 1.2rem'>"
            f"<img src='data:image/png;base64,{LOGO_B64}' "
            f"style='height:42px;filter:brightness(0) invert(1);'>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div style='font-size:0.68rem;font-weight:700;text-transform:uppercase;"
        "letter-spacing:0.1em;color:rgba(255,255,255,0.45);padding-bottom:0.4rem;'>"
        "Filtros</div>",
        unsafe_allow_html=True,
    )

    df_full = load_data()

    prioridad_sel = st.multiselect("Prioridad", ["Alta", "Media", "Baja"], default=["Alta", "Media"])
    afinidad_sel  = st.multiselect("Afinidad", ["Individual", "Empresarial", "Ambos"], default=["Individual", "Empresarial", "Ambos"])
    estado_sel    = st.multiselect("Estado", ESTADOS_ORDEN, default=[e for e in ESTADOS_ORDEN if e != "Descartada"])

    consultores_csv  = df_full["Consultor"].dropna().unique().tolist()
    consultores_opts = sorted(set(CONSULTORES + consultores_csv))
    consultor_sel    = st.multiselect("Consultor", consultores_opts, default=consultores_opts)

    # Regiones agrupadas (5 categorías fijas)
    region_sel = st.multiselect("Región", REGIONES_GRUPO, default=REGIONES_GRUPO)

    # País: todos los países del mundo; sin selección = sin filtro
    pais_sel = st.multiselect("País", TODOS_PAISES, default=[], placeholder="Todos los países…")

    texto = st.text_input("Buscar", placeholder="UNDP, cacao, agroecología…")

    st.divider()
    st.markdown(
        "<div style='font-size:0.68rem;font-weight:700;text-transform:uppercase;"
        "letter-spacing:0.1em;color:rgba(255,255,255,0.45);padding-bottom:0.4rem;'>"
        "Actualizar datos</div>",
        unsafe_allow_html=True,
    )

    _default_key = (
        st.secrets.get("TAVILY_API_KEY", "") if hasattr(st, "secrets") else ""
    ) or os.environ.get("TAVILY_API_KEY", "")

    tavily_key = st.text_input("Tavily API Key", type="password", value=_default_key)

    _is_cloud = not SCRIPT_PATH.exists()
    if _is_cloud:
        st.info(
            "**Actualización automática** vía GitHub Actions (lun/jue 8 AM).\n\n"
            "Manual: ejecutá `actualizar_y_publicar.sh` desde Terminal.",
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
                st.success("¡Completado!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Error:")
                st.code((result.stderr or result.stdout)[-1000:])

    st.divider()
    st.markdown(
        f"<div style='font-size:0.7rem;color:rgba(255,255,255,0.35);text-align:center;'>"
        f"grupo-ceo.com · {date.today().year}</div>",
        unsafe_allow_html=True,
    )

# ── Filtrar y ordenar ─────────────────────────────────────────────────────────

df = load_data()
if prioridad_sel:  df = df[df["Prioridad"].isin(prioridad_sel)]
if afinidad_sel:   df = df[df["Afinidad"].isin(afinidad_sel)]
if estado_sel:     df = df[df["Estado"].isin(estado_sel)]
if consultor_sel:  df = df[df["Consultor"].isin(consultor_sel)]
if region_sel:     df = df[df["_region_grupo"].isin(region_sel)]   # usa columna agrupada
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
  <span>Tocá el ícono de arriba a la izquierda para <strong>filtrar</strong></span>
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
        </div>""", unsafe_allow_html=True)
    else:
        grupo_actual      = None
        df_all_editable   = load_data()

        for orig_idx, row in df.iterrows():
            prio   = row.get("Prioridad", "Media")
            pconf  = PRIO_MAP.get(prio, PRIO_MAP["Media"])
            estado = row.get("Estado", "Identificada")
            econf  = ESTADO_CHIPS.get(estado, ESTADO_CHIPS["Identificada"])

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

            link_chip      = f'<a class="chip chip-link" href="{esc(enlace)}" target="_blank">🔗 Ver convocatoria</a>' if enlace.startswith("http") else ""
            pais_chip      = f'<span class="chip chip-mid">📍 {esc(pais)}</span>' if pais and pais != "—" else ""
            monto_chip     = f'<span class="chip chip-monto">💰 ${monto:,.0f} USD</span>' if monto > 0 else ""
            consultor_chip = f'<span class="chip chip-mid">👤 {esc(consultor)}</span>' if consultor and consultor != "—" else ""
            # Monto en meta (siempre visible)
            monto_meta = f'<span class="monto-meta">💵 ${monto:,.0f} USD</span>' if monto > 0 else '<span style="color:#aaa;">💵 Monto: —</span>'

            st.markdown(f"""
<div class="opp-card" style="border-left-color:{pconf['border']}; background:{pconf['bg']}08;">
  <div class="{title_cls}">{esc(titulo)}</div>
  <div class="opp-meta">
    <span>🏛 <strong>{esc(org)}</strong></span>
    <span>📍 {esc(region)}</span>
    <span>📅 <strong>{esc(fecha)}</strong></span>
    <span>{monto_meta}</span>
  </div>
  <div class="opp-chips">
    <span class="chip chip-dark">{esc(afin)}</span>
    <span class="chip {chip_prio}">{pconf['badge']} {esc(prio)}</span>
    <span class="chip" style="background:{econf['bg']};color:{econf['color']};">{esc(estado)}</span>
    {pais_chip}{monto_chip}{consultor_chip}{link_chip}
  </div>
</div>
""", unsafe_allow_html=True)

            # Edición inline
            ec1, ec2, ec3 = st.columns([3, 3, 2])
            with ec1:
                cur_est = ESTADOS_ORDEN.index(estado) if estado in ESTADOS_ORDEN else 0
                new_estado = st.selectbox("Estado", ESTADOS_ORDEN, index=cur_est,
                                          key=f"est_{orig_idx}", label_visibility="collapsed")
            with ec2:
                cur_con = CONSULTORES.index(consultor) if consultor in CONSULTORES else 0
                new_consultor = st.selectbox("Consultor", CONSULTORES, index=cur_con,
                                             key=f"con_{orig_idx}", label_visibility="collapsed")
            with ec3:
                if new_estado != estado or new_consultor != consultor:
                    if st.button("💾 Guardar", key=f"save_{orig_idx}", type="primary"):
                        df_all_editable.at[orig_idx, "Estado"]    = new_estado
                        df_all_editable.at[orig_idx, "Consultor"] = new_consultor
                        save_df(df_all_editable)
                        st.rerun()

        st.divider()
        export_cols = ["Título", "Organización", "Tipo", "Región", "País", "Fecha límite",
                       "Enlace", "Afinidad", "Prioridad", "Estado", "Monto estimado (USD)", "Consultor"]
        export_df = df[[c for c in export_cols if c in df.columns]]
        st.download_button(
            "⬇️ Descargar resultados filtrados (CSV)",
            data=export_df.to_csv(index=False).encode("utf-8"),
            file_name=f"ceo_consultorias_{date.today()}.csv",
            mime="text/csv",
        )

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — CARTERA
# ════════════════════════════════════════════════════════════════════════════

with tab2:
    df_c = load_data()

    total_c    = len(df_c)
    pipeline_c = df_c["Monto estimado (USD)"].sum()
    ganadas_c  = len(df_c[df_c["Estado"] == "Ganada"])
    en_proc_c  = len(df_c[df_c["Estado"].isin(["Identificada", "En análisis", "Postulada"])])

    st.markdown(f"""
<div style="background:{GREEN_DARK};border-radius:14px;padding:1.2rem 1.6rem;margin-bottom:1.2rem;display:flex;flex-wrap:wrap;gap:1.2rem 2.5rem;align-items:center;">
  <div><div style="color:rgba(255,255,255,0.55);font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em;">Total cartera CEO</div>
  <div style="color:{WHITE};font-size:2rem;font-weight:700;line-height:1.1;">{total_c}</div></div>
  <div><div style="color:rgba(255,255,255,0.55);font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em;">En proceso</div>
  <div style="color:#4CAF82;font-size:2rem;font-weight:700;line-height:1.1;">{en_proc_c}</div></div>
  <div><div style="color:rgba(255,255,255,0.55);font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em;">Ganadas</div>
  <div style="color:#A5D6A7;font-size:2rem;font-weight:700;line-height:1.1;">{ganadas_c}</div></div>
  <div><div style="color:rgba(255,255,255,0.55);font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em;">Pipeline estimado</div>
  <div style="color:#90CAF9;font-size:1.6rem;font-weight:700;line-height:1.1;">${pipeline_c:,.0f}</div></div>
</div>
""", unsafe_allow_html=True)

    ec = df_c["Estado"].value_counts()
    chips_ec = " ".join(
        f'<span class="chip" style="background:{ESTADO_CHIPS.get(e,{}).get("bg","#eee")};'
        f'color:{ESTADO_CHIPS.get(e,{}).get("color","#333")};">'
        f'{e}: <strong>{ec.get(e,0)}</strong></span>'
        for e in ESTADOS_ORDEN
    )
    st.markdown(f'<div style="margin-bottom:1.5rem;display:flex;flex-wrap:wrap;gap:0.4rem;">{chips_ec}</div>', unsafe_allow_html=True)

    # PDF report button
    st.markdown(f'<div class="section-header">Informe de Pipeline</div>', unsafe_allow_html=True)
    c_pdf1, c_pdf2 = st.columns([2, 3])
    with c_pdf1:
        if st.button("📄 Generar informe PDF", type="primary", use_container_width=True):
            with st.spinner("Generando informe PDF…"):
                try:
                    pdf_bytes = generar_pdf(df_c, hoy)
                    st.session_state["pdf_bytes"] = pdf_bytes
                    st.success("Informe generado. Hacé clic en Descargar.")
                except Exception as e:
                    st.error(f"Error al generar PDF: {e}")
    with c_pdf2:
        if "pdf_bytes" in st.session_state:
            st.download_button(
                "⬇️ Descargar informe PDF",
                data=st.session_state["pdf_bytes"],
                file_name=f"CEO_Pipeline_{hoy.strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.caption("Generá el informe primero para poder descargarlo.")

    # Por consultor
    st.markdown(f'<div class="section-header" style="margin-top:1rem;">Por Consultor</div>', unsafe_allow_html=True)
    df_asig = df_c[df_c["Consultor"] != "—"]
    sin_asig = df_c[df_c["Consultor"] == "—"]

    if df_asig.empty:
        st.info("Aún no hay oportunidades asignadas. Usá la pestaña **Editar datos** o los selectores bajo cada card en **Oportunidades**.")
    else:
        for nombre in [c for c in CONSULTORES if c != "—"]:
            sub = df_asig[df_asig["Consultor"] == nombre]
            if sub.empty:
                continue
            pipe_p  = sub["Monto estimado (USD)"].sum()
            n_alt_p = len(sub[sub["Prioridad"] == "Alta"])
            gan_p   = len(sub[sub["Estado"] == "Ganada"])
            est_h   = " ".join(
                f'<span class="chip" style="background:{ESTADO_CHIPS.get(e,{}).get("bg","#eee")};'
                f'color:{ESTADO_CHIPS.get(e,{}).get("color","#333")};">{e}: {len(sub[sub["Estado"]==e])}</span>'
                for e in ESTADOS_ORDEN if len(sub[sub["Estado"]==e]) > 0
            )
            st.markdown(f"""
<div class="cartera-card">
  <div class="cartera-name">👤 {esc(nombre)}</div>
  <div class="cartera-stats">
    <span>📋 {len(sub)} oportunidad{'es' if len(sub)!=1 else ''}</span>
    <span>🔴 {n_alt_p} Alta prioridad</span>
    <span>🏆 {gan_p} Ganada{'s' if gan_p!=1 else ''}</span>
    {'<span>💰 $' + f'{pipe_p:,.0f} USD</span>' if pipe_p > 0 else ''}
  </div>
  <div class="cartera-estados">{est_h}</div>
</div>
""", unsafe_allow_html=True)

            with st.expander(f"Ver oportunidades de {nombre} ({len(sub)})"):
                for idx2, r in sub.sort_values("Prioridad").iterrows():
                    pc2  = PRIO_MAP.get(r.get("Prioridad", "Media"), PRIO_MAP["Media"])
                    ec2  = ESTADO_CHIPS.get(r.get("Estado", "Identificada"), ESTADO_CHIPS["Identificada"])
                    en2  = str(r.get("Enlace", "") or "")
                    lk2  = f'<a class="chip chip-link" href="{esc(en2)}" target="_blank">🔗 Ver</a>' if en2.startswith("http") else ""
                    cp2  = {"Alta": "chip-alta", "Media": "chip-media", "Baja": "chip-baja"}.get(r.get("Prioridad", "Media"), "chip-mid")
                    mo2  = float(r.get("Monto estimado (USD)", 0) or 0)
                    mo2s = f'<span class="chip chip-monto">💰 ${mo2:,.0f} USD</span>' if mo2 > 0 else ""
                    st.markdown(f"""
<div class="opp-card" style="border-left-color:{pc2['border']};background:{pc2['bg']}08;margin-bottom:0.3rem;">
  <div class="opp-title">{esc(r.get('Título',''))}</div>
  <div class="opp-meta">
    <span>🏛 {esc(r.get('Organización','—'))}</span>
    <span>📅 {esc(r.get('Fecha límite','—'))}</span>
    {'<span class="monto-meta">💵 $' + f'{mo2:,.0f} USD</span>' if mo2 > 0 else ''}
  </div>
  <div class="opp-chips">
    <span class="chip {cp2}">{pc2['badge']} {esc(r.get('Prioridad',''))}</span>
    <span class="chip" style="background:{ec2['bg']};color:{ec2['color']};">{esc(r.get('Estado',''))}</span>
    {mo2s}{lk2}
  </div>
</div>
""", unsafe_allow_html=True)
                    # Observaciones por oportunidad (hasta 250 chars)
                    obs_val = str(r.get("Observaciones", "") or "")
                    col_obs, col_save_obs = st.columns([5, 1])
                    with col_obs:
                        obs_new = st.text_area(
                            "obs",
                            value=obs_val,
                            max_chars=250,
                            key=f"obs_{idx2}",
                            placeholder="Observaciones (máx. 250 caracteres)…",
                            label_visibility="collapsed",
                            height=68,
                        )
                    with col_save_obs:
                        st.write("")
                        if obs_new != obs_val:
                            if st.button("💾", key=f"sobs_{idx2}", help="Guardar observación"):
                                df_c.at[idx2, "Observaciones"] = obs_new
                                save_df(df_c)
                                st.rerun()
                    st.markdown("<hr style='margin:0.3rem 0;border-color:#E8F5E9;'>", unsafe_allow_html=True)

    if len(sin_asig) > 0:
        st.markdown(f'<div class="section-header" style="margin-top:1rem;">Sin asignar ({len(sin_asig)})</div>', unsafe_allow_html=True)
        with st.expander(f"Ver {len(sin_asig)} oportunidades sin consultor"):
            for _, r in sin_asig.head(30).iterrows():
                pc3  = PRIO_MAP.get(r.get("Prioridad", "Media"), PRIO_MAP["Media"])
                en3  = str(r.get("Enlace", "") or "")
                lk3  = f'<a class="chip chip-link" href="{esc(en3)}" target="_blank">🔗 Ver</a>' if en3.startswith("http") else ""
                cp3  = {"Alta": "chip-alta", "Media": "chip-media", "Baja": "chip-baja"}.get(r.get("Prioridad", "Media"), "chip-mid")
                mo3  = float(r.get("Monto estimado (USD)", 0) or 0)
                st.markdown(f"""
<div class="opp-card" style="border-left-color:{pc3['border']};background:{pc3['bg']}08;margin-bottom:0.45rem;">
  <div class="opp-title">{esc(r.get('Título',''))}</div>
  <div class="opp-meta">
    <span>🏛 {esc(r.get('Organización','—'))}</span>
    <span>📅 {esc(r.get('Fecha límite','—'))}</span>
    {'<span class="monto-meta">💵 $' + f'{mo3:,.0f} USD</span>' if mo3 > 0 else ''}
  </div>
  <div class="opp-chips">
    <span class="chip chip-dark">{esc(r.get('Afinidad','—'))}</span>
    <span class="chip {cp3}">{pc3['badge']} {esc(r.get('Prioridad',''))}</span>
    {lk3}
  </div>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — EDITAR DATOS
# ════════════════════════════════════════════════════════════════════════════

with tab3:
    st.markdown("**Editá Estado, Consultor, Monto y País directamente en la tabla.**")
    if _is_cloud:
        st.info("Versión en la nube: guardá los cambios y descargá el CSV para subirlo al repositorio.", icon="ℹ️")

    df_edit = load_data()
    EDIT_COLS = ["Título", "Organización", "Fecha límite", "Prioridad", "Estado", "Consultor", "Monto estimado (USD)", "País"]
    df_show   = df_edit[[c for c in EDIT_COLS if c in df_edit.columns]].copy()

    edited = st.data_editor(
        df_show,
        use_container_width=True,
        height=560,
        num_rows="fixed",
        key="data_editor_main",
        column_config={
            "Título":               st.column_config.TextColumn("Título", width="large", disabled=True),
            "Organización":         st.column_config.TextColumn("Organización", disabled=True),
            "Fecha límite":         st.column_config.TextColumn("Fecha límite", disabled=True),
            "Prioridad":            st.column_config.SelectboxColumn("Prioridad", options=["Alta", "Media", "Baja"]),
            "Estado":               st.column_config.SelectboxColumn("Estado", options=ESTADOS_ORDEN),
            "Consultor":            st.column_config.SelectboxColumn("Consultor", options=CONSULTORES),
            "Monto estimado (USD)": st.column_config.NumberColumn("Monto (USD)", min_value=0, format="$%d"),
            "País":                 st.column_config.SelectboxColumn("País", options=TODOS_PAISES),
        },
    )

    cs, cd = st.columns([1, 1])
    with cs:
        if st.button("💾 Guardar cambios en CSV", type="primary", use_container_width=True):
            for col in ["Estado", "Consultor", "Monto estimado (USD)", "País", "Prioridad"]:
                if col in edited.columns:
                    df_edit[col] = edited[col].values
            save_df(df_edit)
            st.success("¡Guardado!")
            st.rerun()
    with cd:
        st.download_button(
            "⬇️ Descargar CSV editado",
            data=edited.to_csv(index=False).encode("utf-8"),
            file_name=f"ceo_consultorias_editado_{date.today()}.csv",
            mime="text/csv",
            use_container_width=True,
        )
