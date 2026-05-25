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

CSV_PATH      = Path(__file__).parent / "oportunidades_consultoria.csv"
SOCIOS_CSV    = Path(__file__).parent / "socios_estrategicos.csv"
SCRIPT_PATH   = Path(__file__).parent / "buscar_consultorias.py"
LOGO_PATH     = Path(__file__).parent / "logo_ceo.png"
CRITERIOS_PATH = Path(__file__).parent / "criterios_aprendidos.json"

# ── GitHub auto-commit (persistencia desde Streamlit Cloud) ───────────────────
GITHUB_OWNER  = "fedevillarreal78-hub"
GITHUB_REPO   = "ceo-consultorias"
GITHUB_BRANCH = "main"

# ── Paleta CEO ─────────────────────────────────────────────────────────────────
GREEN_DARK   = "#0F2D1F"
GREEN_MID    = "#2D6A4F"
GREEN_ACCENT = "#40916C"
GREEN_LIGHT  = "#52B788"
BG_SAGE      = "#F0F7F2"
BG_HERO_FROM = "#D8EFE1"
BG_HERO_TO   = "#95C9B4"
WHITE        = "#FFFFFF"
TEXT_BODY    = "#2C3E35"
BORDER_LIGHT = "#C8E0CF"
SURFACE      = "#FAFCFB"

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
ESTADOS_SELECCIONABLES = [e for e in ESTADOS_ORDEN if e != "Descartada"]

# Perfiles de afinidad
AFINIDAD_OPCIONES = [
    "ICyT, Productividad y Desarrollo",
    "Comercio y Geopolítica",
    "Empresarial",
    "Ambos",
]

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

# Mapa región → países para auto-populate del filtro País
REGION_TO_PAISES: dict[str, list[str]] = {
    # Cono Sur estricto: Río de la Plata + Chile
    "Cono Sur": [
        "Argentina", "Chile", "Paraguay", "Uruguay",
    ],
    # América Latina amplia: Andina + Mesoamérica + Brasil + entradas regionales
    "América Latina": [
        "Belice", "Bolivia", "Brasil", "Colombia", "Costa Rica",
        "Cuba", "Ecuador", "El Salvador", "Guatemala", "Haití",
        "Honduras", "México", "Nicaragua", "Panamá", "Perú",
        "República Dominicana", "Venezuela",
        "América Central", "América del Sur", "América Latina",
        "Centroamérica", "Regional", "Global",
    ],
    "Caribe": [
        "Antigua y Barbuda", "Bahamas", "Barbados", "Cuba", "Dominica",
        "Granada", "Guyana", "Haití", "Jamaica", "República Dominicana",
        "San Cristóbal y Nieves", "San Vicente y las Granadinas",
        "Santa Lucía", "Surinam", "Trinidad y Tobago",
        "Caribe",
    ],
    "Europa": [
        "Albania", "Alemania", "Andorra", "Armenia", "Austria",
        "Azerbaiyán", "Bélgica", "Bosnia y Herzegovina", "Bulgaria",
        "Chipre", "Croacia", "Dinamarca", "Eslovaquia", "Eslovenia",
        "España", "Estonia", "Finlandia", "Francia", "Georgia",
        "Grecia", "Hungría", "Irlanda", "Islandia", "Italia",
        "Letonia", "Liechtenstein", "Lituania", "Luxemburgo", "Malta",
        "Moldavia", "Mónaco", "Montenegro", "Noruega", "Países Bajos",
        "Polonia", "Portugal", "Reino Unido", "República Checa",
        "Rumanía", "Rusia", "San Marino", "Serbia", "Suecia",
        "Suiza", "Ucrania",
    ],
}
_paises_asignados = {p for lst in REGION_TO_PAISES.values() for p in lst}
REGION_TO_PAISES["Otros"] = sorted(
    p for p in TODOS_PAISES if p != "—" and p not in _paises_asignados
)

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

    if "Socio vinculado" not in df.columns:
        df["Socio vinculado"] = ""
    else:
        df["Socio vinculado"] = df["Socio vinculado"].fillna("")

    if "Votos descarte" not in df.columns:
        df["Votos descarte"] = ""
    else:
        df["Votos descarte"] = df["Votos descarte"].fillna("")

    if "Monto estimado (USD)" not in df.columns:
        df["Monto estimado (USD)"] = 0.0
    else:
        df["Monto estimado (USD)"] = pd.to_numeric(
            df["Monto estimado (USD)"].astype(str)
                .str.replace(",", "").str.replace("$", "").str.strip(),
            errors="coerce",
        ).fillna(0.0)

    # Migrar afinidad legacy "Individual" al nuevo perfil
    df["Afinidad"] = df["Afinidad"].replace("Individual", "ICyT, Productividad y Desarrollo")

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

def _push_file_to_github(local_path: Path, github_path: str, commit_msg: str) -> bool:
    """Sube un archivo local al repositorio de GitHub via API REST.

    Requiere GITHUB_TOKEN en variables de entorno o en st.secrets.
    Silencioso ante errores para no interrumpir la UX.
    Retorna True si el commit tuvo éxito.
    """
    try:
        token = os.environ.get("GITHUB_TOKEN", "")
        if not token:
            try:
                token = st.secrets.get("GITHUB_TOKEN", "")
            except Exception:
                pass
        if not token:
            return False

        import requests as _req

        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        api_url = (
            f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"
            f"/contents/{github_path}"
        )

        # Leer contenido del archivo
        with open(local_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")

        # Obtener SHA actual del archivo en GitHub (necesario para update)
        r = _req.get(api_url, headers=headers,
                     params={"ref": GITHUB_BRANCH}, timeout=10)
        sha = r.json().get("sha") if r.status_code == 200 else None

        payload: dict = {
            "message": commit_msg,
            "content": encoded,
            "branch": GITHUB_BRANCH,
        }
        if sha:
            payload["sha"] = sha

        resp = _req.put(api_url, json=payload, headers=headers, timeout=20)
        return resp.status_code in (200, 201)
    except Exception:
        return False


def save_df(df: pd.DataFrame) -> None:
    export_cols = [
        "Título", "Organización", "Tipo", "Región", "País",
        "Fecha límite", "Enlace", "Afinidad", "Prioridad",
        "Estado", "Monto estimado (USD)", "Consultor", "Observaciones",
        "Socio vinculado", "Votos descarte",
    ]
    df[[c for c in export_cols if c in df.columns]].to_csv(CSV_PATH, index=False)
    st.cache_data.clear()
    # Sincronizar con GitHub para persistir cambios desde Streamlit Cloud
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    _push_file_to_github(CSV_PATH, "oportunidades_consultoria.csv",
                         f"Auto-save: cambios en oportunidades ({ts})")

# ── Socios estratégicos ────────────────────────────────────────────────────────

SOCIOS_COLS = ["Nombre", "Categoría", "Experiencia", "Responsable", "Actividades", "Resultados"]
SOCIOS_CATEGORIAS = ["Estratégico", "Profesional Asociado"]

@st.cache_data(ttl=60)
def load_socios() -> pd.DataFrame:
    if not SOCIOS_CSV.exists():
        return pd.DataFrame(columns=SOCIOS_COLS)
    df = pd.read_csv(SOCIOS_CSV)
    df.columns = df.columns.str.strip()
    for col in SOCIOS_COLS:
        if col not in df.columns:
            # Migración: socios existentes sin Categoría → Estratégico por defecto
            df[col] = "Estratégico" if col == "Categoría" else ""
        else:
            df[col] = df[col].fillna("Estratégico" if col == "Categoría" else "")
    return df

def save_socios(df: pd.DataFrame) -> None:
    df[SOCIOS_COLS].to_csv(SOCIOS_CSV, index=False)
    st.cache_data.clear()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    _push_file_to_github(SOCIOS_CSV, "socios_estrategicos.csv",
                         f"Auto-save: cambios en socios estratégicos ({ts})")


# ── Criterios aprendidos de descarte ─────────────────────────────────────────

import json as _json

def load_criterios() -> dict:
    """Carga criterios aprendidos de descarte desde archivo JSON."""
    if not CRITERIOS_PATH.exists():
        return {"señales_exclusion": [], "organizaciones_excluidas": [],
                "tipos_excluidos": [], "patrones_titulo": []}
    try:
        with open(CRITERIOS_PATH, encoding="utf-8") as f:
            return _json.load(f)
    except Exception:
        return {"señales_exclusion": [], "organizaciones_excluidas": [],
                "tipos_excluidos": [], "patrones_titulo": []}

def save_criterios(criterios: dict) -> None:
    """Guarda criterios aprendidos y sincroniza con GitHub."""
    with open(CRITERIOS_PATH, "w", encoding="utf-8") as f:
        _json.dump(criterios, f, ensure_ascii=False, indent=2)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    _push_file_to_github(CRITERIOS_PATH, "criterios_aprendidos.json",
                         f"Auto-save: criterios de descarte actualizados ({ts})")

# ── PDF ───────────────────────────────────────────────────────────────────────

def generar_pdf(df_all: pd.DataFrame, df_socios_pdf: pd.DataFrame, hoy: date) -> bytes:
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
    orden_estado_pdf = {e: i for i, e in enumerate(ESTADOS_ORDEN)}
    df_active["_op"] = df_active["Estado"].map(orden_estado_pdf).fillna(len(ESTADOS_ORDEN))
    df_active["_of"] = df_active["Fecha límite"].apply(parse_deadline)
    df_active = df_active.sort_values(["_op", "_of"])

    total_act  = len(df_active)
    pipeline_t = df_active["Monto estimado (USD)"].sum()
    n_proc_t   = len(df_active[df_active["Estado"].isin(["En análisis", "Postulada"])])

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
                # Suma = 277mm (ancho útil A4 landscape con márgenes 10mm c/lado)
                col_w = [5, 60, 33, 20, 20, 25, 22, 32, 60]
            headers = ["#", "Título", "Organización", "País", "Fecha", "Monto USD", "Estado", "Consultor", "Observaciones"]

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
                obs_s = safe(str(row.get("Observaciones", "") or ""), 38)
                vals = [
                    str(i),
                    safe(row.get("Título", "—"), 38),
                    safe(row.get("Organización", "—"), 20),
                    safe(row.get("País", "—"), 12),
                    safe(row.get("Fecha límite", "—"), 12),
                    monto_s,
                    safe(row.get("Estado", "—"), 14),
                    safe(row.get("Consultor", "—"), 20),
                    obs_s,
                ]
                self.set_fill_color(RS, GS, BS) if alt else self.set_fill_color(255, 255, 255)
                self.set_text_color(30, 30, 30)
                self.set_font("Helvetica", "", 7)
                row_h = 6
                for v, w in zip(vals, col_w):
                    self.cell(w, row_h, v, border=1, fill=True)
                self.ln()
                alt = not alt

        def socios_table(self, df_s):
            if df_s.empty:
                self.set_font("Helvetica", "I", 8)
                self.set_text_color(140, 140, 140)
                self.cell(0, 7, "  Sin socios estrategicos registrados.", ln=True)
                return
            headers = ["Nombre", "Area de experiencia", "Responsable", "Actividades", "Resultados"]
            col_w   = [40, 65, 33, 65, 74]
            self.set_fill_color(RD, GD, BD)
            self.set_text_color(255, 255, 255)
            self.set_font("Helvetica", "B", 7)
            for h, w in zip(headers, col_w):
                self.cell(w, 7, h, border=1, fill=True)
            self.ln()
            alt = True
            for _, row in df_s.iterrows():
                self.set_fill_color(RS, GS, BS) if alt else self.set_fill_color(255, 255, 255)
                self.set_text_color(30, 30, 30)
                self.set_font("Helvetica", "", 7)
                vals = [
                    safe(row.get("Nombre", "-"), 28),
                    safe(row.get("Experiencia", "-"), 48),
                    safe(row.get("Responsable", "-"), 24),
                    safe(row.get("Actividades", "-"), 45),
                    safe(row.get("Resultados", "-"), 50),
                ]
                # Calcular altura de fila según texto más largo (simple wrap a 2 líneas max)
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
    for h, w in [("Consultor", 65), ("Asignadas", 28), ("En proceso", 35), ("Pipeline USD", 50)]:
        pdf.cell(w, 7, h, border=1, fill=True)
    pdf.ln()

    df_asig = df_active[df_active["Consultor"] != "—"]
    sin_asig_n = len(df_active[df_active["Consultor"] == "—"])
    alt = True
    for nombre in CONSULTORES[1:]:
        sub = df_asig[df_asig["Consultor"] == nombre]
        if sub.empty:
            continue
        n_pro_c = len(sub[sub["Estado"].isin(["En análisis", "Postulada", "Ganada"])])
        pipe_c  = sub["Monto estimado (USD)"].sum()
        pdf.set_fill_color(RS, GS, BS) if alt else pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(30, 30, 30)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(65, 6, safe(nombre), border=1, fill=True)
        pdf.cell(28, 6, str(len(sub)), border=1, fill=True)
        pdf.cell(35, 6, str(n_pro_c), border=1, fill=True)
        pdf.cell(50, 6, f"${pipe_c:,.0f}" if pipe_c > 0 else "-", border=1, fill=True)
        pdf.ln()
        alt = not alt

    if sin_asig_n > 0:
        pdf.set_fill_color(255, 248, 225)
        pdf.set_text_color(100, 60, 0)
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(65, 6, "Sin asignar", border=1, fill=True)
        pdf.cell(28, 6, str(sin_asig_n), border=1, fill=True)
        pdf.cell(35, 6, "-", border=1, fill=True)
        pdf.cell(50, 6, "-", border=1, fill=True)
        pdf.ln()

    # ── SOCIOS ESTRATÉGICOS (en resumen ejecutivo) ────────────────────────────
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(RD, GD, BD)
    pdf.cell(0, 7, "Socios Estrategicos de Grupo CEO", ln=True)
    pdf.socios_table(df_socios_pdf)

    # ── GESTIÓN POR CONSULTOR (en resumen ejecutivo) ──────────────────────────
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(RD, GD, BD)
    pdf.cell(0, 7, safe("Gestión por Consultor — Detalle y Observaciones"), ln=True)
    df_asig_pdf = df_active[df_active["Consultor"] != "—"]
    for nombre_c in CONSULTORES[1:]:
        sub_c = df_asig_pdf[df_asig_pdf["Consultor"] == nombre_c]
        if sub_c.empty:
            continue
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(RD, GD, BD)
        pipe_c = sub_c["Monto estimado (USD)"].sum()
        pipe_s = f" | Pipeline: ${pipe_c:,.0f}" if pipe_c > 0 else ""
        pdf.cell(0, 7, safe(f"  {nombre_c}  ({len(sub_c)} oportunidades{pipe_s})"), ln=True)
        col_wo = [90, 30, 157]
        heads  = ["Titulo", "Estado", "Observaciones"]
        pdf.set_fill_color(RD, GD, BD)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 6)
        for h, w in zip(heads, col_wo):
            pdf.cell(w, 6, h, border=1, fill=True)
        pdf.ln()
        alt2 = True
        for _, rc in sub_c.iterrows():
            obs_val = safe(str(rc.get("Observaciones", "") or ""), 100)
            pdf.set_fill_color(RS, GS, BS) if alt2 else pdf.set_fill_color(255, 255, 255)
            pdf.set_text_color(30, 30, 30)
            pdf.set_font("Helvetica", "", 6)
            pdf.cell(col_wo[0], 6, safe(rc.get("Titulo", rc.get("Título", "-")), 62), border=1, fill=True)
            pdf.cell(col_wo[1], 6, safe(rc.get("Estado", "-"), 18), border=1, fill=True)
            pdf.cell(col_wo[2], 6, obs_val, border=1, fill=True)
            pdf.ln()
            alt2 = not alt2

    # ── EN PROCESO ────────────────────────────────────────────────────────────
    df_proc = df_active[df_active["Estado"].isin(["En análisis", "Postulada"])]
    pdf.add_page()
    pdf.section_title(safe("EN PROCESO — EN ANÁLISIS Y POSTULADAS"), r=RM, g=GM, b=BM)
    pdf.opps_table(df_proc)

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

  /* ── Navegación lateral ── */
  section[data-testid="stSidebar"] .stRadio > label {{
    display: none;
  }}
  section[data-testid="stSidebar"] [role="radiogroup"] [data-baseweb="radio"]:nth-child(2) {{
    display: none !important;
  }}
  section[data-testid="stSidebar"] .stRadio [role="radiogroup"] {{
    display: flex; flex-direction: column; gap: 3px;
    padding: 0.3rem 0;
  }}
  section[data-testid="stSidebar"] .stRadio > div > div[data-testid="stMarkdownContainer"] {{
    display: none;
  }}
  section[data-testid="stSidebar"] [data-baseweb="radio"] {{
    background: rgba(255,255,255,0.05);
    border-radius: 10px; padding: 7px 12px !important;
    transition: background 0.15s ease; cursor: pointer;
    margin: 1px 0 !important;
  }}
  section[data-testid="stSidebar"] [data-baseweb="radio"]:hover {{
    background: rgba(255,255,255,0.12) !important;
  }}
  section[data-testid="stSidebar"] [data-baseweb="radio"] [aria-checked="true"],
  section[data-testid="stSidebar"] [data-baseweb="radio"]:has([aria-checked="true"]) {{
    background: rgba(76,175,130,0.28) !important;
    border-left: 3px solid {GREEN_ACCENT} !important;
  }}
  section[data-testid="stSidebar"] [data-baseweb="radio"] label {{
    font-size: 0.88rem !important; font-weight: 500 !important;
    letter-spacing: 0.01em; cursor: pointer;
    color: {WHITE} !important;
  }}

  /* Inputs y multiselects — fondo claro, texto negro legible */
  section[data-testid="stSidebar"] .stTextInput input,
  section[data-testid="stSidebar"] .stMultiSelect div[data-baseweb="select"] {{
    background: rgba(255,255,255,0.97) !important;
    border-color: rgba(255,255,255,0.4) !important;
    border-radius: 8px !important;
    font-size: 0.83rem !important;
    color: #1A3D2E !important;
  }}
  section[data-testid="stSidebar"] .stMultiSelect div[data-baseweb="select"] * {{
    color: #1A3D2E !important;
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

  /* Dropdown opciones — global (el popover se renderiza fuera del sidebar DOM) */
  [data-baseweb="popover"] [role="option"],
  [data-baseweb="popover"] li {{
    background: #FFFFFF !important;
    color: #1A3D2E !important;
    font-size: 0.82rem !important;
  }}
  [data-baseweb="popover"] [role="option"]:hover {{
    background: #EEF6EE !important;
    color: #1A3D2E !important;
  }}
  [data-baseweb="popover"] [aria-selected="true"] {{
    background: #C8E8CA !important;
    color: #1A3D2E !important;
  }}

  /* Expanders en sidebar — fondo oscuro siempre */
  section[data-testid="stSidebar"] details {{
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
    margin-bottom: 4px !important;
  }}
  section[data-testid="stSidebar"] details summary {{
    color: {WHITE} !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    padding: 6px 10px !important;
    background: transparent !important;
  }}
  section[data-testid="stSidebar"] details > div,
  section[data-testid="stSidebar"] .streamlit-expanderContent {{
    background: rgba(255,255,255,0.03) !important;
    border-top: 1px solid rgba(255,255,255,0.08) !important;
    padding: 8px 6px !important;
  }}

  /* Pipeline CEO — bloque destacado en sidebar */
  .pipeline-btn {{
    display: block; width: 100%;
    background: linear-gradient(135deg, #1B6B3A 0%, #2E8B57 100%);
    border: 1px solid rgba(76,175,130,0.5);
    border-radius: 12px;
    padding: 10px 14px;
    margin-bottom: 12px;
    cursor: pointer;
    transition: all 0.18s ease;
    text-decoration: none !important;
  }}
  .pipeline-btn:hover {{
    background: linear-gradient(135deg, #2E8B57 0%, #3DAA6E 100%);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(76,175,130,0.35);
  }}
  .pipeline-btn-label {{
    font-size: 0.65rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.1em; color: rgba(255,255,255,0.55) !important;
    margin-bottom: 3px;
  }}
  .pipeline-btn-title {{
    font-size: 0.95rem; font-weight: 700;
    color: #FFFFFF !important;
    letter-spacing: 0.01em;
  }}

  /* Divider */
  section[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.12) !important; }}

  /* Botones sidebar — general */
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
  /* Pipeline CEO — primer botón del sidebar, estilo destacado */
  section[data-testid="stSidebar"] .stButton:first-of-type button {{
    background: linear-gradient(135deg,#1B6B3A 0%,#2E8B57 100%) !important;
    border: 1px solid rgba(76,175,130,0.55) !important;
    border-radius: 14px !important;
    font-size: 0.97rem !important; font-weight: 700 !important;
    padding: 0.7rem 1rem !important;
    letter-spacing: 0.015em;
    box-shadow: 0 3px 10px rgba(0,0,0,0.25);
  }}
  section[data-testid="stSidebar"] .stButton:first-of-type button:hover {{
    background: linear-gradient(135deg,#2E8B57 0%,#3DAA6E 100%) !important;
    box-shadow: 0 5px 15px rgba(0,0,0,0.35);
    transform: translateY(-1px);
  }}

  /* Text input buscar */
  section[data-testid="stSidebar"] .stTextInput input {{
    color: #1A3D2E !important;
    font-size: 0.85rem !important;
  }}
  section[data-testid="stSidebar"] .stTextInput input::placeholder {{
    color: rgba(26,61,46,0.5) !important;
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
    font-size: 9rem; font-weight: 800; color: rgba(15,45,31,0.05);
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
    background: {SURFACE};
    border: 1px solid {BORDER_LIGHT};
    border-left: 4px solid {GREEN_ACCENT};
    border-radius: 0 12px 12px 0;
    padding: 1rem 1.2rem 0.75rem;
    margin-bottom: 0.7rem;
    transition: box-shadow 0.2s ease, transform 0.15s ease;
    box-shadow: 0 1px 3px rgba(15,45,31,0.06);
  }}
  .opp-card:hover {{
    box-shadow: 0 6px 20px rgba(15,45,31,0.1);
    transform: translateY(-2px);
  }}
  .opp-title {{
    font-size: 0.97rem; font-weight: 700; color: {GREEN_DARK};
    margin-bottom: 0.35rem; line-height: 1.4; letter-spacing: -0.01em;
  }}
  .opp-title-descartada {{
    font-size: 0.97rem; font-weight: 500; color: #9E9E9E;
    margin-bottom: 0.35rem; line-height: 1.4; text-decoration: line-through;
    opacity: 0.7;
  }}
  .opp-meta {{
    display: flex; flex-wrap: wrap; gap: 0.25rem 1rem;
    font-size: 0.76rem; color: #5A7A65; margin-bottom: 0.45rem;
  }}
  .opp-meta span {{ display: flex; align-items: center; gap: 0.2rem; }}
  .opp-meta .monto-meta {{ color: #1A56A0; font-weight: 700; }}
  .opp-chips {{ display: flex; flex-wrap: wrap; gap: 0.25rem; align-items: center; }}
  .opp-obs {{
    margin-top: 0.5rem; padding: 0.35rem 0.7rem;
    background: linear-gradient(90deg, rgba(64,145,108,0.08) 0%, transparent 100%);
    border-left: 3px solid {GREEN_ACCENT};
    border-radius: 0 6px 6px 0; font-size: 0.75rem; color: {TEXT_BODY};
    line-height: 1.45; font-style: italic;
  }}
  .chip {{
    display: inline-block; padding: 2px 10px; border-radius: 20px;
    font-size: 0.70rem; font-weight: 600; letter-spacing: 0.025em;
    transition: opacity 0.15s;
  }}
  .chip-dark  {{ background: {GREEN_DARK}; color: {WHITE}; }}
  .chip-mid   {{ background: {BG_SAGE}; color: {GREEN_DARK}; border: 1px solid {BORDER_LIGHT}; }}
  .chip-alta  {{ background: #FEE2E2; color: #991B1B; border: 1px solid #FECACA; }}
  .chip-media {{ background: #FEF3C7; color: #92400E; border: 1px solid #FDE68A; }}
  .chip-baja  {{ background: #DCFCE7; color: #166534; border: 1px solid #BBF7D0; }}
  .chip-monto {{ background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; font-weight: 700; }}
  .chip-discard {{ background: #FFF3E0; color: #BF360C; border: 1px solid #FFCC80; }}
  .chip-link  {{
    background: {GREEN_DARK}; color: {WHITE} !important;
    text-decoration: none; padding: 3px 12px; border-radius: 20px;
    font-size: 0.70rem; font-weight: 600; letter-spacing: 0.02em;
    transition: background 0.15s ease;
  }}
  .chip-link:hover {{ background: {GREEN_MID} !important; }}

  /* Section headers */
  .section-header {{
    font-size: 0.72rem; font-weight: 800; text-transform: uppercase;
    letter-spacing: 0.1em; color: {GREEN_MID};
    padding: 0.6rem 0 0.35rem;
    border-bottom: 2px solid {BORDER_LIGHT};
    margin-bottom: 0.8rem; margin-top: 0.6rem;
  }}

  /* Empty state */
  .empty-state {{ text-align: center; padding: 3rem 1rem; color: {GREEN_MID}; }}
  .empty-state .icon {{ font-size: 3rem; margin-bottom: 0.5rem; }}

  /* Cartera cards */
  .cartera-card {{
    background: {SURFACE};
    border: 1px solid {BORDER_LIGHT};
    border-radius: 14px;
    padding: 1.1rem 1.3rem;
    margin-bottom: 0.8rem;
    box-shadow: 0 2px 8px rgba(15,45,31,0.07);
    transition: box-shadow 0.2s ease;
  }}
  .cartera-card:hover {{ box-shadow: 0 6px 20px rgba(15,45,31,0.12); }}
  .cartera-name {{
    font-size: 1rem; font-weight: 700; color: {GREEN_DARK};
    margin-bottom: 0.45rem; letter-spacing: -0.01em;
  }}
  .cartera-stats {{
    display: flex; flex-wrap: wrap; gap: 0.5rem 1.5rem;
    font-size: 0.78rem; color: {TEXT_BODY}; margin-bottom: 0.5rem;
  }}
  .cartera-estados {{ display: flex; flex-wrap: wrap; gap: 0.3rem; }}

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

  /* ── Socios Estratégicos ── */
  .socio-card {{
    background: {WHITE}; border-radius: 14px;
    border: 1px solid {BORDER_LIGHT}; border-left: 5px solid {GREEN_MID};
    padding: 1rem 1.3rem 0.85rem; margin-bottom: 0.55rem;
    box-shadow: 0 1px 5px rgba(26,61,46,0.07);
    transition: box-shadow 0.2s ease;
  }}
  .socio-card:hover {{ box-shadow: 0 4px 14px rgba(26,61,46,0.12); }}
  .socio-name {{
    font-size: 1.05rem; font-weight: 700; color: {GREEN_DARK};
    margin-bottom: 0.3rem;
  }}
  .socio-tag {{
    display: inline-block; background: {BG_SAGE}; color: {GREEN_DARK};
    border: 1px solid {BORDER_LIGHT}; border-radius: 20px;
    font-size: 0.72rem; font-weight: 600; padding: 2px 10px;
    margin-right: 0.4rem; margin-bottom: 0.25rem;
  }}
  .socio-field-label {{
    font-size: 0.69rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.06em; color: {GREEN_MID}; margin-top: 0.5rem;
    margin-bottom: 0.15rem;
  }}
  .socio-field-val {{
    font-size: 0.83rem; color: {TEXT_BODY}; line-height: 1.45;
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

  /* Botón primario global */
  .stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {GREEN_DARK} 0%, {GREEN_MID} 100%) !important;
    color: {WHITE} !important; border: none !important;
    border-radius: 8px !important; font-weight: 600 !important;
    font-size: 0.84rem !important; letter-spacing: 0.02em !important;
    padding: 0.45rem 1rem !important;
    box-shadow: 0 2px 6px rgba(15,45,31,0.2) !important;
    transition: all 0.2s ease !important;
  }}
  .stButton > button[kind="primary"]:hover {{
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(15,45,31,0.3) !important;
  }}
  /* Botón secundario global */
  .stButton > button[kind="secondary"] {{
    background: {SURFACE} !important; color: {GREEN_DARK} !important;
    border: 1.5px solid {BORDER_LIGHT} !important;
    border-radius: 8px !important; font-weight: 600 !important;
    font-size: 0.84rem !important;
  }}
  .stButton > button[kind="secondary"]:hover {{
    border-color: {GREEN_ACCENT} !important;
    color: {GREEN_MID} !important;
  }}
</style>
""", unsafe_allow_html=True)

# ── Autenticación ─────────────────────────────────────────────────────────────

def _check_login() -> bool:
    """Verifica credenciales contra st.secrets['usuarios'].
    Retorna True si el usuario está autenticado (o si no hay secrets configurados).
    """
    try:
        usuarios = dict(st.secrets.get("usuarios", {}))
    except Exception:
        usuarios = {}

    if not usuarios:
        # Sin secrets configurados (desarrollo local): sin restricción
        st.session_state.setdefault("usuario_activo", "Federico Villareal")
        return True

    if st.session_state.get("autenticado"):
        return True

    # Pantalla de login
    col_l, col_c, col_r = st.columns([1, 1.2, 1])
    with col_c:
        if LOGO_B64:
            st.markdown(
                f"<div style='text-align:center;padding:2rem 0 1rem'>"
                f"<img src='data:image/png;base64,{LOGO_B64}' style='height:52px;'>"
                f"</div>",
                unsafe_allow_html=True,
            )
        st.markdown(
            "<h3 style='text-align:center;color:#0F2D1F;margin-bottom:1.5rem;'>"
            "Acceso · Grupo CEO</h3>",
            unsafe_allow_html=True,
        )
        with st.form("login_form"):
            usuario_input = st.text_input("Usuario", placeholder="tu nombre de usuario")
            clave_input   = st.text_input("Contraseña", type="password", placeholder="••••••••")
            submitted     = st.form_submit_button("Ingresar", use_container_width=True, type="primary")

        if submitted:
            clave_correcta = usuarios.get(usuario_input.strip(), "")
            if clave_correcta and clave_input == clave_correcta:
                # Buscar el nombre completo del consultor según el usuario
                nombre_mapa = {k.lower(): k for k in CONSULTORES}
                nombre_display = nombre_mapa.get(usuario_input.strip().lower(), usuario_input.strip().title())
                st.session_state["autenticado"]    = True
                st.session_state["usuario_activo"] = nombre_display
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

    return False

if not _check_login():
    st.stop()

usuario_activo = st.session_state.get("usuario_activo", "—")

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    if LOGO_B64:
        st.markdown(
            f"<div style='padding:0.5rem 0 0.8rem'>"
            f"<img src='data:image/png;base64,{LOGO_B64}' "
            f"style='height:42px;filter:brightness(0) invert(1);'>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── Usuario activo + logout ────────────────────────────────────────────
    st.markdown(
        f"<div style='font-size:0.72rem;color:rgba(255,255,255,0.5);text-align:center;"
        f"padding-bottom:0.4rem;'>👤 {usuario_activo}</div>",
        unsafe_allow_html=True,
    )
    if st.button("Cerrar sesión", key="logout_btn", use_container_width=True):
        st.session_state["autenticado"]    = False
        st.session_state["usuario_activo"] = None
        st.rerun()

    st.divider()

    # ── Pipeline CEO — sección destacada ──────────────────────────────────
    if st.button(
        "📊  Pipeline CEO",
        key="btn_pipeline",
        use_container_width=True,
        help="Ver el pipeline de oportunidades gestionadas",
    ):
        st.session_state["nav_page"] = "📊  Pipeline CEO"
        st.rerun()

    st.divider()

    # ── Navegación principal ───────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:0.68rem;font-weight:700;text-transform:uppercase;"
        "letter-spacing:0.1em;color:rgba(255,255,255,0.45);padding-bottom:0.3rem;'>"
        "Navegación</div>",
        unsafe_allow_html=True,
    )
    _radio_val = st.radio(
        "nav",
        options=[
            "📋  Oportunidades",
            "📊  Pipeline CEO",
            "📥  Carga manual de oportunidades",
            "🤝  Socios",
        ],
        label_visibility="collapsed",
        key="nav_page",
    )

    nav_page = _radio_val

    st.divider()

    # ── Filtros (solo visibles en Oportunidades) ───────────────────────────
    if nav_page == "📋  Oportunidades":
        st.markdown(
            "<div style='font-size:0.68rem;font-weight:700;text-transform:uppercase;"
            "letter-spacing:0.1em;color:rgba(255,255,255,0.45);padding-bottom:0.3rem;'>"
            "Filtros</div>",
            unsafe_allow_html=True,
        )

        df_full = load_data()

        # Prioridad y Afinidad: siempre todos (sin filtro visible)
        prioridad_sel = ["Alta", "Media", "Baja"]
        afinidad_sel  = AFINIDAD_OPCIONES + ["Ambos"]

        with st.expander("🔄 Estado", expanded=False):
            estado_sel = st.multiselect(
                "Estado", ESTADOS_ORDEN,
                default=[e for e in ESTADOS_ORDEN if e != "Descartada"],
                label_visibility="collapsed",
            )

        with st.expander("👤 Consultor", expanded=False):
            consultores_csv  = df_full["Consultor"].dropna().unique().tolist()
            consultores_opts = sorted(set(CONSULTORES + consultores_csv))
            consultor_sel    = st.multiselect(
                "Consultor", consultores_opts,
                default=consultores_opts,
                label_visibility="collapsed",
            )

        with st.expander("🌎 Región y País", expanded=False):
            if "_prev_region" not in st.session_state:
                st.session_state["_prev_region"] = list(REGIONES_GRUPO)

            region_sel = st.multiselect(
                "Región", REGIONES_GRUPO,
                default=REGIONES_GRUPO,
                label_visibility="collapsed",
            )

            if sorted(region_sel) != sorted(st.session_state["_prev_region"]):
                st.session_state["_prev_region"] = list(region_sel)
                if set(region_sel) == set(REGIONES_GRUPO):
                    st.session_state["sb_pais"] = []
                else:
                    auto_p: list[str] = []
                    for rg in region_sel:
                        auto_p.extend(REGION_TO_PAISES.get(rg, []))
                    st.session_state["sb_pais"] = sorted(
                        p for p in set(auto_p) if p in TODOS_PAISES
                    )

            pais_sel = st.multiselect(
                "País", TODOS_PAISES,
                key="sb_pais",
                placeholder="Todos los países…",
                label_visibility="collapsed",
            )

        texto = st.text_input("🔍 Buscar", placeholder="UNDP, cacao, agroecología…")

        st.divider()
    else:
        # Valores por defecto cuando no está en la página Oportunidades
        df_full = load_data()
        prioridad_sel = ["Alta", "Media", "Baja"]
        estado_sel    = [e for e in ESTADOS_ORDEN if e != "Descartada"]
        afinidad_sel  = AFINIDAD_OPCIONES + ["Ambos"]
        consultores_csv  = df_full["Consultor"].dropna().unique().tolist()
        consultores_opts = sorted(set(CONSULTORES + consultores_csv))
        consultor_sel    = consultores_opts
        region_sel       = list(REGIONES_GRUPO)
        pais_sel         = []
        texto            = ""

    # ── Actualizar datos ───────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:0.68rem;font-weight:700;text-transform:uppercase;"
        "letter-spacing:0.1em;color:rgba(255,255,255,0.45);padding-bottom:0.3rem;'>"
        "Actualizar datos</div>",
        unsafe_allow_html=True,
    )

    try:
        _default_key = st.secrets.get("TAVILY_API_KEY", "") or os.environ.get("TAVILY_API_KEY", "")
    except Exception:
        _default_key = os.environ.get("TAVILY_API_KEY", "")

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
                result = subprocess.run(
                    [sys.executable, str(SCRIPT_PATH)],
                    capture_output=True, text=True, env=env,
                )
            if result.returncode == 0:
                st.success("¡Completado!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Error:")
                st.code((result.stderr or result.stdout)[-1000:])

    st.markdown(
        f"<div style='font-size:0.7rem;color:rgba(255,255,255,0.25);text-align:center;"
        f"margin-top:0.4rem;'>grupo-ceo.com · {date.today().year}</div>",
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

orden_estado = {e: i for i, e in enumerate(ESTADOS_ORDEN)}
df = df.copy()
df["_ord_estado"] = df["Estado"].map(orden_estado).fillna(len(ESTADOS_ORDEN))
df["_ord_fecha"]  = df["Fecha límite"].apply(parse_deadline)
df = df.sort_values(["_ord_estado", "_ord_fecha"]).drop(columns=["_ord_estado", "_ord_fecha"])

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
    <p>Monitoreo de convocatorias · Perfiles ICyT, Comercio &amp; CEO · ALC &amp; Global</p>
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
n_proceso    = len(df[df["Estado"].isin(["En análisis", "Postulada"])])
n_asignadas  = len(df[df["Consultor"] != "—"])
pipeline     = df["Monto estimado (USD)"].sum()
pipeline_fmt = f"${pipeline:,.0f}" if pipeline > 0 else "—"

st.markdown(f"""
<div class="metrics-bar">
  <div class="metric-pill">
    <div class="metric-num">{total}</div>
    <div class="metric-label">Total filtradas</div>
  </div>
  <div class="metric-pill">
    <div class="metric-num" style="color:#1565C0">{n_proceso}</div>
    <div class="metric-label">🔬 En proceso</div>
  </div>
  <div class="metric-pill">
    <div class="metric-num">{n_asignadas}</div>
    <div class="metric-label">👤 Para CEO</div>
  </div>
  <div class="metric-pill">
    <div class="metric-num-sm" style="color:#0D47A1">{pipeline_fmt}</div>
    <div class="metric-label">💰 Pipeline USD</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────

# ── Contenido por página ──────────────────────────────────────────────────────

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — OPORTUNIDADES
# ════════════════════════════════════════════════════════════════════════════

if nav_page == "📋  Oportunidades":
    if df.empty:
        st.markdown("""
        <div class="empty-state">
          <div class="icon">🌿</div>
          <p>No hay oportunidades con los filtros actuales.</p>
        </div>""", unsafe_allow_html=True)
    else:
        grupo_actual      = None
        df_all_editable   = load_data()

        estado_labels = {
            "Identificada": "🔵 Identificadas",
            "En análisis":  "🔬 En análisis",
            "Postulada":    "📤 Postuladas",
            "Ganada":       "🏆 Ganadas",
            "Descartada":   "🗑 Descartadas",
        }

        for orig_idx, row in df.iterrows():
            estado = row.get("Estado", "Identificada")
            econf  = ESTADO_CHIPS.get(estado, ESTADO_CHIPS["Identificada"])

            if estado != grupo_actual:
                grupo_actual = estado
                st.markdown(f'<div class="section-header">{estado_labels.get(estado, estado)}</div>', unsafe_allow_html=True)

            titulo    = row.get("Título", "Sin título")
            org       = row.get("Organización", "—")
            region    = row.get("Región", "—")
            pais      = row.get("País", "—")
            fecha     = row.get("Fecha límite", "—")
            enlace    = str(row.get("Enlace", "") or "")
            consultor  = row.get("Consultor", "—")
            monto      = float(row.get("Monto estimado (USD)", 0) or 0)
            obs_val    = str(row.get("Observaciones", "") or "")
            votos_raw  = str(row.get("Votos descarte", "") or "")
            votos_list = [v.strip() for v in votos_raw.split("|") if v.strip()]
            n_votos    = len(votos_list)
            VOTOS_NECESARIOS = 2

            descartada = (estado == "Descartada")
            title_cls  = "opp-title-descartada" if descartada else "opp-title"

            link_chip      = f'<a class="chip chip-link" href="{esc(enlace)}" target="_blank">🔗 Ver convocatoria</a>' if enlace.startswith("http") else ""
            pais_chip      = f'<span class="chip chip-mid">📍 {esc(pais)}</span>' if pais and pais != "—" else ""
            monto_chip     = f'<span class="chip chip-monto">💰 ${monto:,.0f} USD</span>' if monto > 0 else ""
            consultor_chip = f'<span class="chip chip-mid">👤 {esc(consultor)}</span>' if consultor and consultor != "—" else ""
            monto_meta     = f'<span class="monto-meta">💵 ${monto:,.0f} USD</span>' if monto > 0 else '<span style="color:#aaa;">💵 Monto: —</span>'
            obs_html       = f'<div class="opp-obs">📝 {esc(obs_val)}</div>' if obs_val else ""
            votos_chip     = f'<span class="chip chip-discard">⛔ {n_votos}/{VOTOS_NECESARIOS} propuestas de descarte</span>' if n_votos > 0 and not descartada else ""

            votos_html = ""
            if n_votos > 0 and estado != "Descartada":
                votos_html = (
                    f'<div style="margin-top:0.4rem;font-size:0.74rem;color:#B71C1C;font-weight:600;">'
                    f'⛔ {n_votos}/{VOTOS_NECESARIOS} votos para descarte'
                    f' — {esc(", ".join(votos_list))}</div>'
                )
            elif estado == "Descartada" and votos_list:
                votos_html = (
                    f'<div style="margin-top:0.4rem;font-size:0.74rem;color:#B71C1C;">'
                    f'⛔ Descartada por consenso — {esc(", ".join(votos_list))}</div>'
                )

            st.markdown(f"""
<div class="opp-card" style="border-left-color:{'#B71C1C' if descartada else GREEN_ACCENT}; background:{'#FFF5F5' if descartada else SURFACE};">
  <div class="{title_cls}">{esc(titulo)}</div>
  <div class="opp-meta">
    <span>🏛 <strong>{esc(org)}</strong></span>
    <span>📍 {esc(region)}</span>
    <span>📅 <strong>{esc(fecha)}</strong></span>
    <span>{monto_meta}</span>
  </div>
  <div class="opp-chips">
    <span class="chip" style="background:{econf['bg']};color:{econf['color']};">{esc(estado)}</span>
    {pais_chip}{monto_chip}{consultor_chip}{votos_chip}{link_chip}
  </div>
  {obs_html}
  {votos_html}
</div>
""", unsafe_allow_html=True)

            # Edición inline — un solo guardado (sin opción "Descartada" en el selector)
            if not descartada:
                ec1, ec2 = st.columns([1, 1])
                with ec1:
                    opciones_estado = ESTADOS_ORDEN if estado == "Descartada" else ESTADOS_SELECCIONABLES
                    cur_est = opciones_estado.index(estado) if estado in opciones_estado else 0
                    new_estado = st.selectbox("Estado", opciones_estado, index=cur_est,
                                              key=f"est_{orig_idx}", label_visibility="collapsed")
                with ec2:
                    cur_con = CONSULTORES.index(consultor) if consultor in CONSULTORES else 0
                    new_consultor = st.selectbox("Consultor", CONSULTORES, index=cur_con,
                                                 key=f"con_{orig_idx}", label_visibility="collapsed")
                obs_new = st.text_area(
                    "Observaciones",
                    value=obs_val, max_chars=200, key=f"obs_{orig_idx}",
                    placeholder="Observación interna (máx. 200 caracteres)…",
                    label_visibility="collapsed", height=58,
                )
                if st.button("💾 Guardar", key=f"save_{orig_idx}", use_container_width=True):
                    df_all_editable.at[orig_idx, "Estado"]        = new_estado
                    df_all_editable.at[orig_idx, "Consultor"]     = new_consultor
                    df_all_editable.at[orig_idx, "Observaciones"] = obs_new
                    save_df(df_all_editable)
                    st.rerun()

                # ── Descarte: lógica diferenciada según estado ─────────────────
                consultores_votantes = [c for c in CONSULTORES if c != "—"]

                if estado == "En análisis":
                    # Descarte directo: el analista ya investigó, puede descartar solo
                    with st.expander("⛔ Descartar esta oportunidad", expanded=False):
                        st.caption("Al estar en análisis, quien investiga puede descartarla directamente.")
                        ya_votaron = set(votos_list)
                        disponibles_d = [c for c in consultores_votantes if c not in ya_votaron]
                        if not disponibles_d:
                            st.info("Ya se registró un descarte.")
                        else:
                            quien_descarta = st.selectbox(
                                "¿Quién descarta?", disponibles_d,
                                key=f"quien_d_{orig_idx}", label_visibility="collapsed",
                            )
                            if st.button("⛔ Descartar definitivamente", key=f"bdes_{orig_idx}",
                                         use_container_width=True, type="primary"):
                                df_all_editable.at[orig_idx, "Estado"] = "Descartada"
                                df_all_editable.at[orig_idx, "Votos descarte"] = quien_descarta
                                save_df(df_all_editable)
                                st.rerun()
                else:
                    # Identificada / Postulada / Ganada → sistema de 2 votos
                    ya_votaron = set(votos_list)
                    disponibles = [c for c in consultores_votantes if c not in ya_votaron]
                    with st.expander(f"⛔ Proponer descarte ({n_votos}/{VOTOS_NECESARIOS} votos)", expanded=False):
                        if not disponibles:
                            st.info("Ya todos los votos disponibles han sido emitidos.")
                        else:
                            voto_nuevo = st.selectbox(
                                "¿Quién propone descartar?", disponibles,
                                key=f"voto_{orig_idx}", label_visibility="collapsed",
                            )
                            if st.button("✋ Registrar voto de descarte", key=f"bvoto_{orig_idx}"):
                                nuevos_votos = votos_list + [voto_nuevo]
                                df_all_editable.at[orig_idx, "Votos descarte"] = "|".join(nuevos_votos)
                                if len(nuevos_votos) >= VOTOS_NECESARIOS:
                                    df_all_editable.at[orig_idx, "Estado"] = "Descartada"
                                save_df(df_all_editable)
                                st.rerun()
            else:
                # Card definitivamente descartada — mostrar quiénes votaron + opción de restaurar
                st.markdown(
                    f"<div style='font-size:0.78rem;color:#B71C1C;padding:4px 0;'>"
                    f"✗ Descartada por consenso · {', '.join(votos_list)}</div>",
                    unsafe_allow_html=True,
                )
                if st.button("↩ Restaurar oportunidad", key=f"restore_{orig_idx}"):
                    df_all_editable.at[orig_idx, "Estado"]        = "Identificada"
                    df_all_editable.at[orig_idx, "Votos descarte"] = ""
                    save_df(df_all_editable)
                    st.rerun()

        st.divider()
        export_cols = ["Título", "Organización", "Tipo", "Región", "País", "Fecha límite",
                       "Enlace", "Estado", "Monto estimado (USD)",
                       "Consultor", "Socio vinculado", "Observaciones", "Votos descarte"]
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

elif nav_page == "📊  Pipeline CEO":
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
            st.session_state.pop("pdf_bytes", None)  # limpiar PDF previo
            with st.spinner("Generando informe PDF…"):
                try:
                    pdf_bytes = generar_pdf(df_c, load_socios(), hoy)
                    st.session_state["pdf_bytes"] = pdf_bytes
                    st.success("✅ Informe generado. Hacé clic en Descargar.")
                except Exception as e:
                    import traceback
                    st.error(f"Error al generar PDF: {e}\n\n{traceback.format_exc()}")
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

    # ── Resumen ejecutivo en pantalla ─────────────────────────────────────────
    st.markdown('<div class="section-header" style="margin-top:1rem;">Resumen Ejecutivo</div>', unsafe_allow_html=True)

    df_act = df_c[df_c["Estado"] != "Descartada"].copy()
    total_act = len(df_act)

    # Tabla distribución por Estado
    th_style = f"background:{GREEN_DARK};color:#fff;padding:6px 12px;text-align:left;font-size:0.78rem;font-weight:700;letter-spacing:0.04em;"
    td_style = "padding:6px 12px;font-size:0.82rem;border-bottom:1px solid #E8F5E9;"
    td_r_style = "padding:6px 12px;font-size:0.82rem;border-bottom:1px solid #E8F5E9;text-align:right;"

    rows_estado = ""
    for e in ESTADOS_ORDEN:
        cnt = int((df_act["Estado"] == e).sum())
        if cnt == 0:
            continue
        pct = f"{cnt / total_act * 100:.1f}%" if total_act > 0 else "-"
        mont = df_act[df_act["Estado"] == e]["Monto estimado (USD)"].sum()
        mont_s = f"${mont:,.0f}" if mont > 0 else "-"
        chip_bg  = ESTADO_CHIPS.get(e, {}).get("bg", "#eee")
        chip_col = ESTADO_CHIPS.get(e, {}).get("color", "#333")
        rows_estado += (
            f'<tr><td style="{td_style}">'
            f'<span style="background:{chip_bg};color:{chip_col};padding:2px 9px;border-radius:12px;font-size:0.75rem;font-weight:600;">{esc(e)}</span>'
            f'</td><td style="{td_r_style}">{cnt}</td>'
            f'<td style="{td_r_style}">{pct}</td>'
            f'<td style="{td_r_style}">{mont_s}</td></tr>'
        )

    st.markdown(f"""
<div style="margin-bottom:1.4rem;">
<div style="font-size:0.8rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:{GREEN_MID};margin-bottom:0.4rem;">Distribución por Estado</div>
<table style="width:100%;border-collapse:collapse;border-radius:10px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
  <thead><tr>
    <th style="{th_style}">Estado</th>
    <th style="{th_style}text-align:right;">N°</th>
    <th style="{th_style}text-align:right;">% del total</th>
    <th style="{th_style}text-align:right;">Pipeline estimado USD</th>
  </tr></thead>
  <tbody>{rows_estado}</tbody>
</table>
</div>
""", unsafe_allow_html=True)

    # Tabla distribución por Consultor
    df_asig = df_act[df_act["Consultor"] != "—"]
    rows_con = ""
    for nombre in [c for c in CONSULTORES if c != "—"]:
        sub = df_asig[df_asig["Consultor"] == nombre]
        if sub.empty:
            continue
        n_pro = int(sub["Estado"].isin(["En análisis", "Postulada", "Ganada"]).sum())
        pipe  = sub["Monto estimado (USD)"].sum()
        pipe_s = f"${pipe:,.0f}" if pipe > 0 else "-"
        rows_con += (
            f'<tr><td style="{td_style}font-weight:600;">👤 {esc(nombre)}</td>'
            f'<td style="{td_r_style}">{len(sub)}</td>'
            f'<td style="{td_r_style}">{n_pro}</td>'
            f'<td style="{td_r_style}">{pipe_s}</td></tr>'
        )

    st.markdown(f"""
<div style="margin-bottom:1.6rem;">
<div style="font-size:0.8rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:{GREEN_MID};margin-bottom:0.4rem;">Distribución por Consultor</div>
<table style="width:100%;border-collapse:collapse;border-radius:10px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
  <thead><tr>
    <th style="{th_style}">Consultor</th>
    <th style="{th_style}text-align:right;">Asignadas</th>
    <th style="{th_style}text-align:right;">En proceso</th>
    <th style="{th_style}text-align:right;">Pipeline USD</th>
  </tr></thead>
  <tbody>{rows_con}</tbody>
</table>
</div>
""", unsafe_allow_html=True)

    # Observaciones por consultor (expandibles)
    st.markdown('<div class="section-header" style="margin-top:0.5rem;font-size:0.95rem;">Observaciones por oportunidad</div>', unsafe_allow_html=True)
    if df_asig.empty:
        st.info("Aún no hay oportunidades asignadas a consultores.")
    else:
        for nombre in [c for c in CONSULTORES if c != "—"]:
            sub = df_asig[df_asig["Consultor"] == nombre]
            if sub.empty:
                continue
            with st.expander(f"👤 {nombre} — {len(sub)} oportunidad{'es' if len(sub)!=1 else ''}"):
                for idx2, r in sub.sort_values("Estado").iterrows():
                    ec2  = ESTADO_CHIPS.get(r.get("Estado", "Identificada"), ESTADO_CHIPS["Identificada"])
                    en2  = str(r.get("Enlace", "") or "")
                    lk2  = f'<a class="chip chip-link" href="{esc(en2)}" target="_blank">🔗 Ver</a>' if en2.startswith("http") else ""
                    mo2  = float(r.get("Monto estimado (USD)", 0) or 0)
                    mo2s = f'<span class="chip chip-monto">💰 ${mo2:,.0f} USD</span>' if mo2 > 0 else ""
                    sv_val = str(r.get("Socio vinculado", "") or "")
                    _sv_lista_chip = [s.strip() for s in sv_val.split("|") if s.strip() and s.strip() != "—"]
                    sv_chip = " ".join(f'<span class="chip chip-mid">🤝 {esc(s)}</span>' for s in _sv_lista_chip)
                    st.markdown(f"""
<div class="opp-card" style="border-left-color:{GREEN_ACCENT};background:#FAFAFA;margin-bottom:0.3rem;">
  <div class="opp-title">{esc(r.get('Título',''))}</div>
  <div class="opp-meta">
    <span>🏛 {esc(r.get('Organización','—'))}</span>
    <span>📅 {esc(r.get('Fecha límite','—'))}</span>
  </div>
  <div class="opp-chips">
    <span class="chip" style="background:{ec2['bg']};color:{ec2['color']};">{esc(r.get('Estado',''))}</span>
    {mo2s}{sv_chip}{lk2}
  </div>
</div>
""", unsafe_allow_html=True)
                    # Socios vinculados — múltiples (separados por " | ")
                    _sv_raw   = str(r.get("Socio vinculado", "") or "")
                    _sv_lista = [s.strip() for s in _sv_raw.split("|") if s.strip() and s.strip() != "—"]
                    _todos_socios = load_socios()["Nombre"].tolist()
                    st.caption("🤝 Socios vinculados")
                    if _sv_lista:
                        for _sv_nombre in _sv_lista:
                            col_sn, col_sr = st.columns([6, 1])
                            with col_sn:
                                st.markdown(
                                    f'<span class="chip chip-mid" style="display:inline-block;margin:2px 0;">🤝 {esc(_sv_nombre)}</span>',
                                    unsafe_allow_html=True,
                                )
                            with col_sr:
                                if st.button("✕", key=f"rm_sv_{idx2}_{_sv_nombre}",
                                             help=f"Quitar a {_sv_nombre}"):
                                    nueva = [s for s in _sv_lista if s != _sv_nombre]
                                    df_c.at[idx2, "Socio vinculado"] = " | ".join(nueva)
                                    save_df(df_c)
                                    st.rerun()
                    else:
                        st.markdown("<span style='color:#888;font-size:0.85rem;font-style:italic;'>Sin socios asignados</span>", unsafe_allow_html=True)
                    _disponibles = ["— Agregar socio —"] + [s for s in _todos_socios if s not in _sv_lista]
                    if len(_disponibles) > 1:
                        col_add, col_add_btn = st.columns([5, 1])
                        with col_add:
                            _sv_agregar = st.selectbox(
                                "Agregar socio",
                                _disponibles,
                                index=0,
                                key=f"add_sv_{idx2}",
                                label_visibility="collapsed",
                            )
                        with col_add_btn:
                            if _sv_agregar != "— Agregar socio —":
                                if st.button("➕", key=f"btn_add_sv_{idx2}",
                                             help=f"Vincular a {_sv_agregar}"):
                                    nueva = _sv_lista + [_sv_agregar]
                                    df_c.at[idx2, "Socio vinculado"] = " | ".join(nueva)
                                    save_df(df_c)
                                    st.rerun()
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

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — EDITAR DATOS
# ════════════════════════════════════════════════════════════════════════════

elif nav_page == "📥  Carga manual de oportunidades":
    st.markdown("**Editá Estado, Consultor, Monto y País directamente en la tabla.**")
    if _is_cloud:
        st.info("Versión en la nube: guardá los cambios y descargá el CSV para subirlo al repositorio.", icon="ℹ️")

    # ── Formulario de carga manual ────────────────────────────────────────────
    st.markdown(f'<div class="section-header" style="margin-bottom:0.8rem;">➕ Agregar consultoría manualmente</div>', unsafe_allow_html=True)
    with st.form("form_nueva_opp", clear_on_submit=True):
        fc1, fc2 = st.columns([3, 2])
        with fc1:
            f_titulo  = st.text_input("Título *", placeholder="Nombre de la consultoría o convocatoria")
            f_org     = st.text_input("Organización *", placeholder="UNDP, FAO, BID, IICA…")
            f_enlace  = st.text_input("Enlace / URL", placeholder="https://…")
            f_obs     = st.text_area("Observaciones", placeholder="Notas internas (máx. 250 caracteres)…", max_chars=250, height=80)
        with fc2:
            f_pais    = st.selectbox("País", TODOS_PAISES, index=TODOS_PAISES.index("—") if "—" in TODOS_PAISES else 0)
            f_region  = st.text_input("Región", placeholder="ALC, Global, Cono Sur…")
            f_fecha   = st.text_input("Fecha límite", placeholder="YYYY-MM-DD")
            f_monto   = st.number_input("Monto estimado (USD)", min_value=0, value=0, step=1000)

        ff1, ff2, ff3 = st.columns(3)
        with ff1:
            f_tipo    = st.selectbox("Tipo", ["Individual", "Servicios", "Licitación", "Otro"])
        with ff2:
            f_estado  = st.selectbox("Estado", ESTADOS_ORDEN, index=0)
        with ff3:
            f_consul  = st.selectbox("Consultor", CONSULTORES, index=0)

        submitted = st.form_submit_button("✅ Agregar a la base de datos", type="primary", use_container_width=True)

    if submitted:
        if not f_titulo.strip():
            st.error("El campo **Título** es obligatorio.")
        elif not f_org.strip():
            st.error("El campo **Organización** es obligatorio.")
        else:
            nueva_fila = {
                "Título":               f_titulo.strip(),
                "Organización":         f_org.strip(),
                "Tipo":                 f_tipo,
                "Región":               f_region.strip() if f_region.strip() else "—",
                "País":                 f_pais,
                "Fecha límite":         f_fecha.strip() if f_fecha.strip() else "—",
                "Enlace":               f_enlace.strip(),
                "Afinidad":             "ICyT, Productividad y Desarrollo",
                "Prioridad":            "Media",
                "Estado":               f_estado,
                "Monto estimado (USD)": float(f_monto) if f_monto else 0.0,
                "Consultor":            f_consul,
                "Observaciones":        f_obs.strip(),
            }
            df_base = load_data()
            nueva_df = pd.DataFrame([nueva_fila])
            df_updated = pd.concat([df_base, nueva_df], ignore_index=True)
            save_df(df_updated)
            st.success(f"✅ **{f_titulo.strip()}** agregada correctamente a la base de datos.")
            st.rerun()

    st.divider()

    df_edit = load_data()
    EDIT_COLS = ["Título", "Organización", "Fecha límite", "Estado", "Consultor", "Monto estimado (USD)", "País"]
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
            "Estado":               st.column_config.SelectboxColumn("Estado", options=ESTADOS_ORDEN),
            "Consultor":            st.column_config.SelectboxColumn("Consultor", options=CONSULTORES),
            "Monto estimado (USD)": st.column_config.NumberColumn("Monto (USD)", min_value=0, format="$%d"),
            "País":                 st.column_config.SelectboxColumn("País", options=TODOS_PAISES),
        },
    )

    cs, cd = st.columns([1, 1])
    with cs:
        if st.button("💾 Guardar cambios en CSV", type="primary", use_container_width=True):
            for col in ["Estado", "Consultor", "Monto estimado (USD)", "País"]:
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

# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — SOCIOS
# ════════════════════════════════════════════════════════════════════════════

elif nav_page == "🤝  Socios":
    df_socios = load_socios()

    # ── Header ───────────────────────────────────────────────────────────────
    n_estrat = len(df_socios[df_socios["Categoría"] == "Estratégico"])
    n_asoc   = len(df_socios[df_socios["Categoría"] == "Profesional Asociado"])
    sc_responsables = df_socios["Responsable"].nunique() if len(df_socios) > 0 else 0

    st.markdown(f"""
<div style="background:{GREEN_DARK};border-radius:14px;padding:1.1rem 1.6rem;margin-bottom:1.2rem;
     display:flex;flex-wrap:wrap;gap:1.2rem 2.5rem;align-items:center;">
  <div>
    <div style="color:rgba(255,255,255,0.55);font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em;">Socios estratégicos</div>
    <div style="color:{WHITE};font-size:2rem;font-weight:700;line-height:1.1;">{n_estrat}</div>
  </div>
  <div>
    <div style="color:rgba(255,255,255,0.55);font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em;">Profesionales asociados</div>
    <div style="color:#4CAF82;font-size:2rem;font-weight:700;line-height:1.1;">{n_asoc}</div>
  </div>
  <div>
    <div style="color:rgba(255,255,255,0.55);font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em;">Responsables activos</div>
    <div style="color:#95C9B4;font-size:2rem;font-weight:700;line-height:1.1;">{sc_responsables}</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Pestañas por categoría ────────────────────────────────────────────────
    tab_estrat, tab_asoc = st.tabs(["🤝 Socios Estratégicos", "👥 Profesionales Asociados"])

    def _render_socios_lista(df_cat: pd.DataFrame, prefix: str) -> None:
        """Renderiza el listado y edición de socios de una categoría."""
        if df_cat.empty:
            st.markdown("""
<div class="empty-state">
  <div class="icon">🤝</div>
  <p>Aún no hay registros en esta categoría. Usá el formulario de abajo para agregar el primero.</p>
</div>""", unsafe_allow_html=True)
            return
        for idx, row in df_cat.iterrows():
            nombre      = str(row.get("Nombre",      "") or "Sin nombre")
            experiencia = str(row.get("Experiencia", "") or "")
            responsable = str(row.get("Responsable", "—") or "—")
            actividades = str(row.get("Actividades", "") or "")
            resultados  = str(row.get("Resultados",  "") or "")
            exp_preview = (experiencia[:120] + "…") if len(experiencia) > 120 else experiencia
            st.markdown(f"""
<div class="socio-card">
  <div class="socio-name">🤝 {esc(nombre)}</div>
  <span class="socio-tag">👤 {esc(responsable)}</span>
  <div class="socio-field-label">Área de experiencia y aporte a CEO</div>
  <div class="socio-field-val">{esc(exp_preview)}</div>
</div>""", unsafe_allow_html=True)
            with st.expander(f"Ver detalle completo y editar — {nombre}"):
                ef1, ef2 = st.columns([3, 1])
                with ef1:
                    e_nombre = st.text_input("Nombre", value=nombre, key=f"{prefix}sn_{idx}")
                    e_exp = st.text_area("Área de experiencia y aporte a CEO",
                                        value=experiencia, key=f"{prefix}se_{idx}", height=90)
                    e_act = st.text_area("Actividades desarrolladas",
                                        value=actividades, key=f"{prefix}sa_{idx}", height=90)
                    e_res = st.text_area("Resultados esperados",
                                        value=resultados, key=f"{prefix}sr_{idx}", height=90)
                with ef2:
                    resp_idx = CONSULTORES.index(responsable) if responsable in CONSULTORES else 0
                    e_resp = st.selectbox("Responsable", CONSULTORES,
                                         index=resp_idx, key=f"{prefix}srp_{idx}")
                    st.write("")
                    if st.button("💾 Guardar", key=f"{prefix}ssave_{idx}",
                                 type="primary", use_container_width=True):
                        df_socios.at[idx, "Nombre"]      = e_nombre.strip()
                        df_socios.at[idx, "Experiencia"] = e_exp.strip()
                        df_socios.at[idx, "Actividades"] = e_act.strip()
                        df_socios.at[idx, "Resultados"]  = e_res.strip()
                        df_socios.at[idx, "Responsable"] = e_resp
                        save_socios(df_socios)
                        st.success("¡Cambios guardados!")
                        st.rerun()
                    st.write("")
                    if st.button("🗑 Eliminar", key=f"{prefix}sdel_{idx}",
                                 use_container_width=True):
                        df_socios.drop(index=idx, inplace=True)
                        df_socios.reset_index(drop=True, inplace=True)
                        save_socios(df_socios)
                        st.rerun()

    with tab_estrat:
        _render_socios_lista(
            df_socios[df_socios["Categoría"] == "Estratégico"], "e_")

    with tab_asoc:
        _render_socios_lista(
            df_socios[df_socios["Categoría"] == "Profesional Asociado"], "a_")

    # ── Formulario de alta ────────────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="section-header">➕ Agregar nuevo socio</div>',
                unsafe_allow_html=True)

    with st.form("form_nuevo_socio", clear_on_submit=True):
        nf1, nf2 = st.columns([3, 1])
        with nf1:
            ns_nombre = st.text_input(
                "Nombre *",
                placeholder="Nombre completo de la persona u organización")
            ns_exp = st.text_area(
                "Área de experiencia y aporte a CEO *",
                placeholder="Describe la especialización y cómo agrega valor al equipo CEO…",
                height=95)
            ns_act = st.text_area(
                "Actividades desarrolladas",
                placeholder="Reuniones realizadas, presentaciones, proyectos colaborados…",
                height=85)
            ns_res = st.text_area(
                "Resultados esperados",
                placeholder="Contratos posibles, alianzas estratégicas, conocimiento compartido…",
                height=85)
        with nf2:
            ns_cat  = st.selectbox("Categoría *", SOCIOS_CATEGORIAS, index=0)
            ns_resp = st.selectbox("Responsable del contacto", CONSULTORES, index=0)
            st.write("")
            st.markdown(
                "<div style='font-size:0.75rem;color:#666;'>* Campos obligatorios</div>",
                unsafe_allow_html=True)

        ns_submitted = st.form_submit_button(
            "✅ Agregar", type="primary", use_container_width=True)

    if ns_submitted:
        if not ns_nombre.strip():
            st.error("El campo **Nombre** es obligatorio.")
        elif not ns_exp.strip():
            st.error("El campo **Área de experiencia** es obligatorio.")
        else:
            nuevo_socio = {
                "Nombre":      ns_nombre.strip(),
                "Categoría":   ns_cat,
                "Experiencia": ns_exp.strip(),
                "Responsable": ns_resp,
                "Actividades": ns_act.strip(),
                "Resultados":  ns_res.strip(),
            }
            df_socios_upd = pd.concat(
                [df_socios, pd.DataFrame([nuevo_socio])], ignore_index=True)
            save_socios(df_socios_upd)
            st.success(f"✅ **{ns_nombre.strip()}** agregado como {ns_cat}.")
            st.rerun()
