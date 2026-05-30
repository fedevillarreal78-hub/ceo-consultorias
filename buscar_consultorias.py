#!/usr/bin/env python3
"""
buscar_consultorias.py
Busca oportunidades de consultoría en fuentes abiertas, las compara con
el CSV existente y reporta las que son nuevas.

Uso:
    python3 buscar_consultorias.py

Dependencias:
    pip3 install requests beautifulsoup4 lxml tavily-python

Variables de entorno opcionales:
    TAVILY_API_KEY  — API key de Tavily (app.tavily.com). Si se define,
                      Tavily se usa como fuente principal de búsqueda.
"""

import csv
import hashlib
import json
import os
import re
import time
import warnings
from datetime import datetime, date
from pathlib import Path

warnings.filterwarnings("ignore")  # suprime avisos SSL/urllib3

import requests
from bs4 import BeautifulSoup

# ── Configuración ────────────────────────────────────────────────────────────

BASE_DIR    = Path(__file__).parent
CSV_PATH    = BASE_DIR / "oportunidades_consultoria.csv"
REPORT_PATH = BASE_DIR / "nuevas_esta_semana.txt"

# Palabras del sector — el texto debe contener al menos una
KEYWORDS = [
    # Sector agro / alimentario
    "agriculture", "food", "rural", "agrifood", "agro", "bioeconomy",
    "food security", "nutrition", "value chain", "agribusiness",
    "agroforestry", "livestock", "crop", "farm", "harvest",
    "agricultura", "alimentaria", "agroalimentar", "bioeconomía",
    "cadenas de valor", "seguridad alimentaria", "desarrollo rural",
    # Política y comercio
    "policy", "institutional", "trade", "commerce", "innovation",
    "política", "institucional", "comercio", "innovación", "sostenibilidad",
    "trade policy", "agricultural policy", "política agrícola",
    "comercio internacional", "negociación", "negotiation",
    "política comercial", "mercados agropecuarios",
    # Econometría / estadística
    "econometrics", "econometría", "statistical analysis", "análisis estadístico",
    "impact evaluation", "evaluación de impacto", "value chains",
    # Bioeconomía / ciencia
    "bioeconomy", "biotechnology", "innovation system", "technology transfer",
    "sistema de innovación", "transferencia tecnológica", "agro-tech",
    # Organismos clave nuevos
    "CGIAR", "IFPRI", "FONTAGRO", "bioversity", "CIAT",
    "CAF", "BCIE", "GIZ", "AECID",
    # Geopolítica regional
    "cono sur", "argentina", "mercosur", "lac region",
]

# Señales que confirman que ES una convocatoria — debe haber al menos una
PROCUREMENT_SIGNALS = [
    "consultor", "consultora", "consultancy", "consultant", "consulting",
    "procurement", "rfp", "rfq", "solicitud de propuesta", "terms of reference",
    "tor ", "terms of ref", "individual contract", "ic -", "ic–", "ic —",
    "service contract", "licitación", "convocatoria", "call for",
    "roster", "vacancy", "vacante", "job opening", "position open",
    "request for proposal", "request for quotation", "oferta de servicios",
    "expert", "experto", "especialista", "asesor", "adviser", "advisor",
    "retainer", "short-term", "short term", "home-based", "home based",
    "fee", "honorario", "contrato de servicios",
    # Terminología adicional de procurement (aprendido 2026-05-30)
    "llamado a consultor", "llamado a consultores",
    "expresión de interés", "expresion de interes", "eoi",
    "manifestación de interés", "manifestacion de interes",
    "concurso de méritos", "concurso de meritos", "concurso",
    "postulación abierta", "postulacion abierta",
    "licitación pública", "licitacion publica",
    "notice of procurement", "procurement notice",
    "invitation to bid", "invitation for bids",
    "apply now", "deadline for applications", "closing date",
    "fecha límite de postulación", "fecha límite de presentación",
]

# Frases que indican que NO es una convocatoria — usar frases específicas,
# no palabras sueltas (evitar falsos negativos en TOR legítimas)
EXCLUSION_SIGNALS = [
    # Informes y publicaciones
    "press release", "comunicado de prensa", "nota de prensa",
    "news release", "newsletter", "boletín informativo", "boletin informativo",
    "research paper", "working paper", "policy brief", "policy paper",
    "discussion paper", "fact sheet", "issue brief",
    "informe anual", "annual report", "memoria anual",
    "publicación reciente", "nueva publicación",
    # Noticias y blog (frases, no la palabra sola)
    " news:", "blog post", "blog entry", "opinion piece",
    "artículo de opinión", "nota periodística",
    # Eventos sin convocatoria asociada
    "webinar registration", "register now for", "join our webinar",
    "save the date", "seminario internacional", "conferencia mundial",
    "training course registration", "curso en línea",
    # Anuncios de resultados / premios
    "grant announcement", "award announcement", "award winner",
    "resultado del concurso", "ganador del concurso",
    "donación aprobada", "grant awarded",
    # Lanzamientos de productos/iniciativas (no contratos)
    "launch of the", "lanzamiento del programa", "we are pleased to announce",
]

# Patrones en la URL que indican noticias o contenido editorial
EXCLUSION_URL_PATTERNS = [
    # Inglés genérico
    "/news/", "/blog/", "/press/", "/media/", "/stories/",
    "/opinion/", "/report/", "/publication/", "/document/",
    "/event/", "/training/", "/workshop/", "/webinar/",
    "/update/", "/article/", "/feature/", "/resource/",
    # Español genérico
    "/prensa/", "/noticias/", "/noticia/", "/newsletter/",
    "/publicacion/", "/publicaciones/", "/eventos/", "/evento/",
    "/capacitacion/", "/taller/", "/webinars/",
    # Redes sociales y anclas
    "twitter.com", "linkedin.com", "youtube.com", "facebook.com",
    "mailto:", "#",
    # IICA — páginas de noticias y notas de prensa (aprendido 2026-05-23)
    "iica.int/es/prensa/", "iica.int/en/press/",
    "iica.int/es/noticias/", "iica.int/en/news/",
    "iica.int/es/newsletter/",
    # FAO — páginas institucionales y publicaciones no-convocatorias
    "fao.org/americas/news/", "fao.org/americas/about",
    "fao.org/americas/partners", "fao.org/americas/interviews",
    "fao.org/newsroom/", "fao.org/media/docs/",
    "fao.org/cfs/plenary/", "fao.org/cfs/about/",
    "openknowledge.fao.org", "faolex.fao.org",
    "fao.org/4/", "fao.org/fileadmin/",
    "fao.org/in-action/", "fao.org/connect-private-sector/search/detail",
    "fao.org/rangelands", "fao.org/investment-centre/latest/news",
    "fao.org/social-protection/",
    "fao.org/americas/about-us/regional-representative",
    # IDB/BID — blog, noticias y páginas temáticas
    "iadb.org/en/blog/", "iadb.org/en/news-media/",
    "iadb.org/en/who-we-are/country-offices/",
    "iadb.org/en/who-we-are/topics/",
    # Banco Mundial — páginas temáticas e institucionales
    "worldbank.org/en/topic/", "worldbank.org/en/about/",
    "financesone.worldbank.org/project-procurement",
    # Otros organismos — páginas institucionales
    "wto.org/english/thewto_e/",
    "agriculture.ec.europa.eu",
]

# Códigos de país UNDP fuera del foco ALC de CEO (aprendido 2026-05-23)
# Las oportunidades de estas oficinas tienen muy baja afinidad con el mandato CEO
UNDP_COUNTRY_EXCLUSIONS = {
    # África subsahariana
    "AFG", "PAK", "NPL", "BGD", "IND", "LKA", "MMR",
    "IDN", "PHL", "THA", "VNM", "KHM", "LAO", "MYS",
    "NGA", "SEN", "ETH", "UGA", "KEN", "TZA", "MOZ",
    "ZWE", "ZAF", "BWA", "LSO", "SWZ", "SLE", "LBR",
    "GHA", "CMR", "COD", "COG", "MDG", "MWI", "ZMB",
    # Europa del Este y Asia Central
    "UKR", "MDA", "ALB", "GEO", "ARM", "AZE",
    "TJK", "UZB", "KGZ", "TKM",
    # Norte de África y Medio Oriente
    "TUN", "MAR", "DZA", "EGY", "LBY", "SDN", "YEM",
    # Europa occidental (sedes OI, no operativas ALC)
    "DNK", "SWE", "NOR", "FIN", "BLR", "MNE", "MKD",
}

CSV_COLUMNS = [
    "Título", "Organización", "Tipo", "Región",
    "Fecha límite", "Enlace", "Afinidad", "Prioridad",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-419,es;q=0.9,en;q=0.8",
}

UNDP_BASE = "https://procurement-notices.undp.org"
RW_BASE   = "https://reliefweb.int"

# ── Utilidades ───────────────────────────────────────────────────────────────

def log(msg: str, prefix: str = "  ") -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {prefix}{msg}")


def make_id(title: str, org: str) -> str:
    """Hash estable para detectar duplicados, insensible a mayúsculas."""
    raw = f"{title.lower().strip()}|{org.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def clean_deadline(raw: str) -> str:
    """
    Normaliza fechas de cierre extraídas de UNDP u otras fuentes.
    UNDP usa el formato '25-May-2607:40 PM (New York time)' donde el año
    es de 2 dígitos ('26') pegado a la hora sin separador.
    Resultado esperado: '25-May-2026'.
    """
    if not raw or raw.strip() in ("A verificar", "A verificar en portal IDB",
                                  "A verificar en Devex", "Monitoreo continuo",
                                  "Abierto (Roster permanente)", "Referencia 2026"):
        return raw.strip() if raw else "A verificar"

    # Patrón ISO completo: 2026-05-25
    m = re.search(r"(\d{4}-\d{2}-\d{2})", raw)
    if m:
        return m.group(1)

    # UNDP: DD-Mmm-YY[HH:MM] — el año es exactamente 2 dígitos antes de la hora
    # Ej: "25-May-2607:40" → day=25, month=May, year=26
    m = re.search(r"(\d{1,2}-[A-Za-z]{3}-)(\d{2})(?:\d{2}:|$|\s)", raw)
    if m:
        return f"{m.group(1)}20{m.group(2)}"

    # DD-Mmm-YYYY (año de 4 dígitos ya correcto)
    m = re.search(r"(\d{1,2}-[A-Za-z]{3}-20\d{2})", raw)
    if m:
        return m.group(1)

    return raw.strip()[:20]


def is_undp_excluded_country(org: str) -> bool:
    """Retorna True si la organización UNDP corresponde a una oficina fuera del foco ALC.

    El nombre de org sigue el patrón: 'UNDP – UNDP-COD/COUNTRY_NAME'
    Extrae el código de 3 letras y lo cruza con UNDP_COUNTRY_EXCLUSIONS.
    """
    m = re.search(r"UNDP-([A-Z]{3})/", org)
    if m:
        return m.group(1) in UNDP_COUNTRY_EXCLUSIONS
    return False


def is_relevant(text: str, url: str = "", org: str = "") -> bool:
    """
    Devuelve True solo si el texto corresponde a una convocatoria de consultoría
    relevante al sector agroalimentario/desarrollo rural.

    Criterios (todos deben cumplirse):
    1. Contiene al menos una palabra del sector (KEYWORDS)
    2. Contiene al menos una señal de convocatoria (PROCUREMENT_SIGNALS)
    3. No contiene señales de noticias/informes (EXCLUSION_SIGNALS)
    4. La URL no apunta a secciones editoriales (EXCLUSION_URL_PATTERNS)
    5. Si es UNDP, la oficina de país debe estar en foco ALC (UNDP_COUNTRY_EXCLUSIONS)
    """
    t = text.lower()
    u = url.lower()

    # Criterio 5: filtro geográfico UNDP (aprendido 2026-05-23)
    if org and is_undp_excluded_country(org):
        return False

    # Criterio 4: URL excluida
    if u and any(p in u for p in EXCLUSION_URL_PATTERNS):
        return False

    # Criterio 3: señales de exclusión en el texto
    if any(sig in t for sig in EXCLUSION_SIGNALS):
        return False

    # Criterio 1: al menos una palabra del sector
    if not any(kw in t for kw in KEYWORDS):
        return False

    # Criterio 2: al menos una señal de convocatoria
    if not any(sig in t for sig in PROCUREMENT_SIGNALS):
        return False

    return True


def load_criterios_aprendidos() -> dict:
    """Carga criterios de descarte aprendidos desde el archivo JSON compartido con la app."""
    criterios_path = BASE_DIR / "criterios_aprendidos.json"
    if not criterios_path.exists():
        return {}
    try:
        with open(criterios_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def load_existing_ids() -> tuple[set, set]:
    """Retorna (todos_los_ids, ids_descartadas).

    - todos_los_ids: evita duplicados en general.
    - ids_descartadas: oportunidades marcadas como Descartadas; jamás deben re-agregarse.
    """
    if not CSV_PATH.exists():
        return set(), set()
    all_ids = set()
    discarded_ids = set()
    with open(CSV_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            oid = make_id(row.get("Título", ""), row.get("Organización", ""))
            all_ids.add(oid)
            if row.get("Estado", "").strip() == "Descartada":
                discarded_ids.add(oid)
    return all_ids, discarded_ids


def append_to_csv(opportunities: list) -> None:
    """Agrega nuevas oportunidades al CSV preservando TODAS las columnas existentes.

    Si el CSV ya existe, se leen sus columnas actuales (que pueden incluir Estado,
    Consultor, Observaciones, Votos descarte, etc.) y se usan como fieldnames para
    que las filas nuevas no corrompan el archivo ni pierdan datos previos.
    """
    file_exists = CSV_PATH.exists()

    if file_exists:
        # Leer el encabezado actual del CSV para preservar todas sus columnas
        with open(CSV_PATH, encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            try:
                fieldnames = next(reader)
            except StopIteration:
                fieldnames = list(CSV_COLUMNS)
    else:
        fieldnames = list(CSV_COLUMNS)

    # Valores por defecto para columnas que buscar_consultorias.py no genera
    defaults = {
        "Estado": "Identificada",
        "Monto estimado (USD)": "",
        "Consultor": "—",
        "Observaciones": "",
        "Socio vinculado": "",
        "Votos descarte": "",
        "País": "—",
    }

    with open(CSV_PATH, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        for opp in opportunities:
            row = {**defaults, **opp}
            writer.writerow(row)


def classify(title: str, org: str) -> tuple:
    t = (title + " " + org).lower()

    # Tipo firma / empresarial
    if any(w in t for w in ["firma", "empresa", "company", "firm", "consortium", "rfp", "licitación"]):
        tipo = "Firma"
        afinidad = "Empresarial"

    # Consultor individual explícito
    elif any(w in t for w in ["individual", "ic -", "ic–", "consultor individual", "individual consultant"]):
        # Determinar cuál perfil individual
        if any(w in t for w in [
            "trade", "comercio", "negociaci", "geopolit", "mercado",
            "política comercial", "econometr", "arancel", "tariff",
            "market access", "acceso a mercados", "wto", "omc",
            "bilateral", "multilateral", "acuerdo comercial",
        ]):
            tipo = "Individual"
            afinidad = "Comercio y Geopolítica"
        else:
            tipo = "Individual"
            afinidad = "ICyT, Productividad y Desarrollo"

    # Sin indicación de tipo → clasificar por contenido temático
    else:
        if any(w in t for w in [
            "trade policy", "política comercial", "comercio internacional",
            "negociacion", "negociación", "econometri", "market analysis",
            "geopolit", "mercados agropecuarios", "acceso mercados",
            "wto", "omc", "arancel", "tariff", "export", "import",
        ]):
            tipo = "Ambos"
            afinidad = "Comercio y Geopolítica"
        else:
            tipo = "Ambos"
            afinidad = "Ambos"

    return tipo, afinidad, "Alta"


def infer_region(text: str) -> str:
    t = text.lower()

    # Frases compuestas primero — evitan que "caribbean" solo se active antes
    if any(w in t for w in [
        "latin america and the caribbean", "latin america & caribbean",
        "latin america & the caribbean", "lac region", "latinoamérica y el caribe",
        "america latina y el caribe", "lac countries",
    ]):
        return "América Latina y Caribe"

    countries = {
        # ── Centroamérica ──────────────────────────────────────────────────
        "guatemala":    "Centroamérica – Guatemala",
        "el salvador":  "Centroamérica – El Salvador",
        "honduras":     "Centroamérica – Honduras",
        "costa rica":   "Centroamérica – Costa Rica",
        "nicaragua":    "Centroamérica – Nicaragua",
        "panamá":       "Centroamérica – Panamá",
        "panama":       "Centroamérica – Panamá",
        "belize":       "Centroamérica – Belice",
        "belice":       "Centroamérica – Belice",
        # ── México ────────────────────────────────────────────────────────
        "mexico":       "México",
        "méxico":       "México",
        # ── Caribe ────────────────────────────────────────────────────────
        "caribbean":    "Caribe",
        "caribe":       "Caribe",
        "haiti":        "Caribe – Haití",
        "haití":        "Caribe – Haití",
        "cuba":         "Caribe – Cuba",
        "jamaica":      "Caribe – Jamaica",
        "dominican":    "Caribe – República Dominicana",
        "dominicana":   "Caribe – República Dominicana",
        "trinidad":     "Caribe – Trinidad y Tobago",
        "barbados":     "Caribe – Barbados",
        "bahamas":      "Caribe – Bahamas",
        "guyana":       "Caribe / América del Sur – Guyana",
        "suriname":     "Caribe / América del Sur – Surinam",
        "surinam":      "Caribe / América del Sur – Surinam",
        "puerto rico":  "Caribe – Puerto Rico",
        "martinique":   "Caribe – Martinica",
        "guadeloupe":   "Caribe – Guadalupe",
        "saint lucia":  "Caribe – Santa Lucía",
        "grenada":      "Caribe – Granada",
        "antigua":      "Caribe – Antigua y Barbuda",
        "saint kitts":  "Caribe – Saint Kitts y Nevis",
        "saint vincent": "Caribe – San Vicente",
        "dominica":     "Caribe – Dominica",
        # ── América del Sur ────────────────────────────────────────────────
        "colombia":     "América del Sur – Colombia",
        "venezuela":    "América del Sur – Venezuela",
        "perú":         "América del Sur – Perú",
        "peru":         "América del Sur – Perú",
        "bolivia":      "América del Sur – Bolivia",
        "ecuador":      "América del Sur – Ecuador",
        "paraguay":     "Cono Sur – Paraguay",
        "argentina":    "Cono Sur – Argentina",
        "chile":        "Cono Sur – Chile",
        "uruguay":      "Cono Sur – Uruguay",
        "brasil":       "América del Sur – Brasil",
        "brazil":       "América del Sur – Brasil",
        # ── Europa — Sedes OI ──────────────────────────────────────────────
        "rome":         "Europa – Roma (Sede OI)",
        "roma":         "Europa – Roma (Sede OI)",
        "geneva":       "Europa – Ginebra (Sede OI)",
        "ginebra":      "Europa – Ginebra (Sede OI)",
        "brussels":     "Europa – Bruselas (Sede OI / UE)",
        "bruxelles":    "Europa – Bruselas (Sede OI / UE)",
        "bruselas":     "Europa – Bruselas (Sede OI / UE)",
        "paris":        "Europa – París (Sede OI)",
        "parís":        "Europa – París (Sede OI)",
        "vienna":       "Europa – Viena (Sede OI)",
        "wien":         "Europa – Viena (Sede OI)",
        "viena":        "Europa – Viena (Sede OI)",
        "london":       "Europa – Londres (Sede OI)",
        "londres":      "Europa – Londres (Sede OI)",
        "madrid":       "Europa – Madrid (Sede OI / FAO ALC)",
        "hague":        "Europa – La Haya (Sede OI)",
        "haya":         "Europa – La Haya (Sede OI)",
        "luxembourg":   "Europa – Luxemburgo (Sede UE)",
        "luxemburgo":   "Europa – Luxemburgo (Sede UE)",
        "strasbourg":   "Europa – Estrasburgo (Sede UE)",
        "estrasburgo":  "Europa – Estrasburgo (Sede UE)",
        "bonn":         "Europa – Bonn (Sede ONU)",
        "nairobi":      "África – Nairobi (Sede OI)",  # UNEP/ONU-Habitat
    }
    for key, region in countries.items():
        if key in t:
            return region
    if any(w in t for w in [
        "latin america", "lac", "america latina", "américas",
        "latinoamerica", "latinoamérica", "latin american",
        "latin america and the caribbean", "latin america & caribbean",
    ]):
        return "América Latina y Caribe"
    if any(w in t for w in ["europe", "europa", "european union", "unión europea"]):
        return "Europa – Sede OI"
    return "Global"


def get_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


# ── Scrapers ─────────────────────────────────────────────────────────────────

TAVILY_QUERIES = [
    # ── ICyT, Productividad y Desarrollo — ancladas a procurement ────────
    "terms of reference agriculture food systems consultant Latin America Caribbean 2026",
    "individual contractor food security agricultural policy LAC apply deadline 2026",
    "call for consultancy rural development food Latin America closing date 2026",
    "consultoría términos de referencia agricultura desarrollo rural ALC 2026",
    "llamado a consultor individual agropecuario innovación Argentina Cono Sur 2026",
    "expresión de interés consultoría seguridad alimentaria sistemas agroalimentarios 2026",
    "CGIAR IFPRI consultant agricultural research terms of reference 2026",
    "FONTAGRO convocatoria consultoría innovación agropecuaria términos referencia 2026",
    "bioeconomy individual consultant terms of reference Latin America UNDP FAO 2026",
    "CIAT Alliance Bioversity consultant terms of reference food agriculture 2026",
    "IICA convocatoria consultoría política agropecuaria términos de referencia 2026",
    "consultoría innovación tecnológica transferencia agropecuaria Cono Sur TOR 2026",
    "RIMISP consultoría desarrollo rural territorial América Latina 2026",
    "PROCASUR consultoría formación rural capacidades ALC términos referencia 2026",
    # ── Sedes organismos internacionales en Europa ────────────────────────
    "individual contractor FAO Rome headquarters food agriculture systems apply 2026",
    "ILO Geneva consultant rural employment agriculture decent work deadline 2026",
    "IFAD Rome consultant rural development food security terms of reference 2026",
    "WFP consultant food supply chain procurement notice 2026",
    "European Commission consultant agriculture rural development LAC TOR 2026",
    "consultancy UNDP headquarters Geneva food agriculture policy notice 2026",
    # ── Comercio y Geopolítica — ancladas a procurement ──────────────────
    "terms of reference trade policy agriculture consultant BID CEPAL 2026",
    "individual consultant agricultural trade negotiations LAC apply closing date 2026",
    "agricultural trade policy advisor Argentina LAC terms of reference 2026",
    "request for proposal agricultural policy evaluation impact LAC 2026 RFP",
    "consultoría econometría evaluación de impacto políticas agrícolas TOR 2026",
    "expresión de interés comercio internacional agropecuario BID CAF CEPAL 2026",
    "consultor negociaciones agropecuarias internacionales Cono Sur TOR 2026",
    "World Bank agriculture trade policy consultant terms of reference LAC 2026",
    "USAID agriculture trade policy consultant terms of reference Latin America 2026",
    "consultoría mercados agropecuarios cadenas de valor Mercosur convocatoria 2026",
    # ── Centroamérica (BCIE, SICA, USAID, BID activos en la región) ──────
    "individual consultant agriculture food security Central America Guatemala Honduras 2026",
    "consultoría BCIE SICA agricultura Centroamérica términos de referencia 2026",
    "terms of reference food systems Central America USAID 2026 apply",
    "consultant agriculture rural development El Salvador Costa Rica Nicaragua 2026",
    # ── Caribe ────────────────────────────────────────────────────────────
    "consultancy CARICOM Caribbean food agriculture security terms of reference 2026",
    "consultant Eastern Caribbean OECS food nutrition agriculture deadline 2026",
    "terms of reference Caribbean agriculture rural development consultant 2026",
    # ── Cooperación bilateral ─────────────────────────────────────────────
    "GIZ consultant agriculture rural development Latin America tender TOR 2026",
    "AECID convocatoria consultoría agricultura desarrollo rural ALC 2026",
    "AFD Expertise France consultant agriculture food Latin America terms of reference 2026",
    "CAF convocatoria consultoría agroindustria comercio América Latina 2026",
    "SNV consultant agriculture food systems Latin America 2026",
    "Helvetas consultant rural agriculture Latin America terms of reference 2026",
    # ── Fondaciones privadas ──────────────────────────────────────────────
    "Gates Foundation request for proposal agriculture food systems Latin America 2026",
    "GAFSP consultant agriculture food security request for proposal 2026",
    "McKnight Foundation Rockefeller consultant agriculture food deadline 2026",
    "IKEA Foundation WK Kellogg consultant rural food systems apply 2026",
    "Howard Buffett Foundation consultant agriculture terms of reference 2026",
    # ── Sostenibilidad y medioambiente ────────────────────────────────────
    "Nature Conservancy WWF consultant agriculture sustainability LAC terms of reference 2026",
    "Rainforest Alliance consultant sustainable supply chain agriculture 2026",
    "Tropical Forest Alliance consultant deforestation agriculture LAC 2026",
    "ALInvest Verde consultoría agricultura sostenible América Latina convocatoria 2026",
    # ── Investigación agropecuaria ────────────────────────────────────────
    "ILRI consultant livestock agriculture developing countries terms of reference 2026",
    "IDRC consultant agriculture food systems Latin America apply 2026",
    "Syngenta Foundation consultant agriculture innovation terms of reference 2026",
    "CIMMYT consultant maize wheat agriculture Latin America 2026",
    # ── Portales agregadores ──────────────────────────────────────────────
    "reliefweb consultancy agriculture food Latin America closing date 2026",
    "devex consultancy agriculture food policy LAC deadline 2026",
    "UNGM procurement notice agriculture food systems consultant Latin America 2026",
]


def scrape_tavily(api_key: str) -> list:
    """
    Usa la API de Tavily para buscar oportunidades de consultoría.
    Requiere TAVILY_API_KEY en el entorno (app.tavily.com — 1 000 req/mes gratis).
    Cada resultado tiene: title, url, content, score.
    """
    log("Tavily Search API...", "→ ")
    results = []
    seen_links: set = set()

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
    except ImportError:
        log("tavily-python no instalado. Ejecuta: pip3 install tavily-python", "  ✗ ")
        return results

    for query in TAVILY_QUERIES:
        try:
            resp = client.search(
                query=query,
                max_results=20,
                search_depth="advanced",
                include_domains=[
                    # ── Portales ONU — procurement y vacantes ────────────────
                    "procurement-notices.undp.org",
                    "jobs.undp.org",
                    "ungm.org",               # UN Global Marketplace (multi-agencia)
                    "jobs.fao.org",
                    "fao.org",
                    "ifad.org",
                    "wfp.org",
                    "ilo.org",
                    "jobs.ilo.org",
                    "who.int",
                    "wto.org",
                    "oecd.org",
                    # ── Agregadores de desarrollo ────────────────────────────
                    "reliefweb.int",
                    "devex.com",
                    # ── Bancos de desarrollo ─────────────────────────────────
                    "worldbank.org",
                    "iadb.org",
                    "idbinvest.org",
                    "caf.com",
                    "bcie.org",
                    "ebrd.com",
                    "eib.org",
                    # ── Organismos regionales ALC ────────────────────────────
                    "cepal.org",
                    "eclac.org",
                    "iica.int",
                    "fontagro.org",
                    "sica.int",               # Sistema Integración Centroamericana
                    "caricom.org",
                    # ── CGIAR e investigación agropecuaria ───────────────────
                    "cgiar.org",
                    "ifpri.org",
                    "bioversityinternational.org",
                    "alliancebioversityciat.org",
                    "cimmyt.org",
                    "ilri.org",
                    "catie.ac.cr",            # CATIE — agropecuario tropical
                    # ── Centros de desarrollo rural ALC ─────────────────────
                    "rimisp.org",             # Centro Latinoamericano Desarrollo Rural
                    "procasur.org",           # Formación y capacidades rurales ALC
                    # ── Cooperación bilateral ────────────────────────────────
                    "giz.de",
                    "aecid.es",
                    "afd.fr",
                    "expertisefrance.fr",
                    "usaid.gov",
                    "grants.gov",
                    "foreignassistance.gov",
                    "snv.org",                # SNV desarrollo rural
                    "helvetas.org",           # Cooperación suiza
                    # ── Europa ───────────────────────────────────────────────
                    "ted.europa.eu",          # Tenders electrónicos UE
                    "ec.europa.eu",
                    # ── Fondaciones privadas y filantrópicas ─────────────────
                    "gafspfund.org",
                    "gatesfoundation.org",
                    "rockefellerfoundation.org",
                    "ikeafoundation.org",
                    "wkkf.org",
                    "foundationfar.org",
                    "thehowardgbuffettfoundation.org",
                    "mcknight.org",
                    # ── Sostenibilidad, medioambiente y cadenas de valor ─────
                    "alinvest-verde.eu",
                    "nature.org",
                    "worldwildlife.org",
                    "rainforest-alliance.org",
                    "solidaridadlatam.org",
                    "tropicalforestalliance.org",
                    "croplifela.org",
                    # ── Investigación adicional ──────────────────────────────
                    "syngentagroup.com",
                    "idrc-crdi.ca",
                ],
            )

            for item in resp.get("results", []):
                title   = item.get("title", "").strip()
                url     = item.get("url", "").strip()
                content = item.get("content", "")

                if not title or not url or url in seen_links:
                    continue
                if not is_relevant(title + " " + content[:300], url):
                    continue

                seen_links.add(url)

                # Inferir organización desde el dominio
                org = _org_from_url(url)
                tipo, afinidad, _ = classify(title, org)
                deadline = _extract_deadline_from_text(content)

                results.append({
                    "Título":       title,
                    "Organización": org,
                    "Tipo":         tipo,
                    "Región":       infer_region(title + " " + content[:300]),
                    "Fecha límite": deadline,
                    "Enlace":       url,
                    "Afinidad":     afinidad,
                    "Prioridad":    "Alta" if deadline != "A verificar" else "Media",
                })

            time.sleep(1)

        except Exception as e:
            log(f"Error Tavily (query='{query[:40]}'): {e}", "  ✗ ")

    log(f"{len(results)} oportunidades relevantes encontradas.", "  ✓ ")
    return results


def _org_from_url(url: str) -> str:
    """Infiere el nombre de la organización a partir del dominio."""
    mapping = {
        "undp.org":              "UNDP",
        "reliefweb.int":         "ReliefWeb",
        "devex.com":             "Devex",
        "fao.org":               "FAO",
        "iadb.org":              "IDB / BID",
        "ifad.org":              "IFAD / FIDA",
        "worldbank.org":         "Banco Mundial",
        "ted.europa.eu":         "UE / EuropeAid",
        "grants.gov":            "USAID / US Gov",
        "usaid.gov":             "USAID",
        "iica.int":              "IICA",
        "fontagro.org":          "FONTAGRO",
        "cgiar.org":             "CGIAR",
        "ifpri.org":             "IFPRI",
        "bioversityinternational.org": "Alliance Bioversity-CIAT",
        "cimmyt.org":            "CIMMYT / CGIAR",
        "caf.com":               "CAF",
        "bcie.org":              "BCIE",
        "cepal.org":             "CEPAL",
        "eclac.org":             "CEPAL",
        "giz.de":                "GIZ",
        "aecid.es":              "AECID",
        "afd.fr":                "AFD / Expertise France",
        "expertisefrance.fr":    "Expertise France",
        "ilo.org":               "OIT / ILO",
        "who.int":               "OMS / WHO",
        "wto.org":               "OMC / WTO",
        "oecd.org":              "OCDE / OECD",
        "ebrd.com":              "BERD / EBRD",
        "ec.europa.eu":          "Comisión Europea",
        "wfp.org":               "PMA / WFP",
        # Fondaciones privadas y filantrópicas
        "gafspfund.org":                   "GAFSP",
        "gatesfoundation.org":             "Gates Foundation",
        "rockefellerfoundation.org":       "Rockefeller Foundation",
        "ikeafoundation.org":              "IKEA Foundation",
        "wkkf.org":                        "WK Kellogg Foundation",
        "foundationfar.org":               "FFAR",
        "thehowardgbuffettfoundation.org": "Howard G. Buffett Foundation",
        "mcknight.org":                    "McKnight Foundation",
        # Sostenibilidad, medioambiente y cadenas de valor
        "alinvest-verde.eu":               "ALInvest Verde (UE)",
        "sustainable-supplychains.org":    "SASI / Sustainable Supply Chains",
        "nature.org":                      "The Nature Conservancy",
        "worldwildlife.org":               "WWF",
        "rainforest-alliance.org":         "Rainforest Alliance",
        "solidaridadlatam.org":            "Solidaridad",
        "tropicalforestalliance.org":      "Tropical Forest Alliance",
        "croplifela.org":                  "CropLife Latinoamérica",
        # Investigación agropecuaria adicional
        "alliancebioversityciat.org":      "Alliance Bioversity-CIAT",
        "ilri.org":                        "ILRI",
        "syngentagroup.com":               "Syngenta Foundation",
        "idrc-crdi.ca":                    "IDRC",
        "aic.ca":                          "AIC / Agri-Food Innovation Council",
        "cimmyt.org":                      "CIMMYT / CGIAR",
        "catie.ac.cr":                     "CATIE",
        # Centros de desarrollo rural ALC
        "rimisp.org":                      "RIMISP",
        "procasur.org":                    "PROCASUR",
        # ONU — marketplace y otros portales
        "ungm.org":                        "UNGM / ONU",
        "jobs.ilo.org":                    "OIT / ILO",
        # Organismos regionales ALC
        "sica.int":                        "SICA",
        "caricom.org":                     "CARICOM",
        # Cooperación bilateral adicional
        "snv.org":                         "SNV",
        "helvetas.org":                    "Helvetas",
        "aecid.es":                        "AECID",
        # Otros bancos
        "idbinvest.org":                   "IDB Invest / BID Invest",
    }
    for domain, name in mapping.items():
        if domain in url:
            return name
    return "A verificar"


def _extract_deadline_from_text(text: str) -> str:
    """Intenta extraer una fecha de cierre del texto del resultado Tavily."""
    # Buscar patrones comunes: "deadline: May 25", "closing date: 2026-05-25", etc.
    m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if m:
        return m.group(1)
    m = re.search(r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+20\d{2})", text, re.I)
    if m:
        return m.group(1)
    m = re.search(r"(\d{1,2}-[A-Za-z]{3}-20\d{2})", text)
    if m:
        return m.group(1)
    return "A verificar"


def scrape_reliefweb(session: requests.Session) -> list:
    """
    Scraping HTML de ReliefWeb /jobs filtrado por Consultancy.
    Selectores confirmados en la estructura real del sitio.
    """
    log("ReliefWeb...", "→ ")
    results = []

    # Páginas de consultoría con filtro de categoría
    urls = [
        f"{RW_BASE}/jobs?advanced-search=%28TY264%29&list=Consultancy+Jobs",
        f"{RW_BASE}/jobs?advanced-search=%28TY264%29_%28S1268%29&list=Consultancy+Jobs",  # + Food/Agriculture
    ]

    seen_links = set()
    for url in urls:
        try:
            r = session.get(url, timeout=20)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")

            for article in soup.select("article.rw-river-article--job"):
                # Título y enlace
                h3 = article.select_one("h3.rw-river-article__title a")
                if not h3:
                    continue
                title = h3.get_text(strip=True)
                link  = h3.get("href", "").strip()
                if not link.startswith("http"):
                    link = RW_BASE + link
                if link in seen_links:
                    continue
                seen_links.add(link)

                # Organización
                org_el = article.select_one(
                    "dd.rw-entity-meta__tag-value--source a, "
                    "dd.rw-entity-meta__tag-value--source span"
                )
                org = org_el.get_text(strip=True) if org_el else "Sin especificar"

                # Fecha de cierre (el segundo <time> es closing date)
                times = article.select("time")
                deadline = "A verificar"
                if len(times) >= 2:
                    # El segundo time corresponde a Closing date
                    dt = times[1].get("datetime", "")
                    deadline = dt[:10] if dt else times[1].get_text(strip=True)
                elif times:
                    dt = times[0].get("datetime", "")
                    deadline = dt[:10] if dt else times[0].get_text(strip=True)

                if not is_relevant(title + " " + org, link):
                    continue

                tipo, afinidad, prioridad = classify(title, org)
                results.append({
                    "Título":       title,
                    "Organización": org,
                    "Tipo":         tipo,
                    "Región":       infer_region(title + " " + org),
                    "Fecha límite": deadline,
                    "Enlace":       link,
                    "Afinidad":     afinidad,
                    "Prioridad":    prioridad,
                })

            time.sleep(1)

        except Exception as e:
            log(f"Error ReliefWeb ({url}): {e}", "  ✗ ")

    log(f"{len(results)} oportunidades relevantes encontradas.", "  ✓ ")
    return results


def scrape_undp(session: requests.Session) -> list:
    """
    UNDP Procurement Notices. Los datos están en el DOM como
    <a class='vacanciesTableLink' data-region='...'> con celdas internas.
    568+ avisos disponibles; filtramos por palabras clave y tipo IC/RFP.
    """
    log("UNDP Procurement Notices...", "→ ")
    results = []

    try:
        r = session.get(UNDP_BASE, timeout=25)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")

        rows = soup.select("a.vacanciesTableLink[data-region]")
        log(f"  {len(rows)} avisos en el DOM, filtrando...", "  ")

        for row in rows:
            cells = {
                div.select_one(".vacanciesTable__cell__label"): div.select_one("span")
                for div in row.select(".vacanciesTable__cell")
            }
            # Extraer por label
            data = {}
            for label_el, value_el in cells.items():
                if label_el and value_el:
                    key   = label_el.get_text(strip=True).lower()
                    value = value_el.get_text(strip=True)
                    data[key] = value

            title    = data.get("title", "").strip()
            ref_no   = data.get("ref no", "")
            country  = data.get("undp office/country", "")
            deadline = clean_deadline(data.get("deadline", "A verificar"))
            process  = data.get("procurement process", "")

            href = row.get("href", "")
            link = href if href.startswith("http") else f"{UNDP_BASE}/{href.lstrip('/')}"

            if not title or not is_relevant(title, link):
                continue

            tipo, afinidad, prioridad = classify(title + " " + process, "UNDP")
            region = infer_region(country + " " + title) if country else infer_region(title)

            results.append({
                "Título":       f"{title} ({ref_no})" if ref_no else title,
                "Organización": f"UNDP – {country}" if country else "UNDP",
                "Tipo":         tipo,
                "Región":       region,
                "Fecha límite": deadline,
                "Enlace":       link,
                "Afinidad":     afinidad,
                "Prioridad":    prioridad,
            })

    except Exception as e:
        log(f"Error UNDP: {e}", "  ✗ ")

    log(f"{len(results)} oportunidades relevantes encontradas.", "  ✓ ")
    return results


def scrape_fao(session: requests.Session) -> list:
    """
    FAO: el portal jobs.fao.org tiene SSL antiguo.
    Alternativas funcionales: FSN Forum (vacantes en HTML plano)
    y la página de empleos de la Oficina Regional para ALC.
    """
    log("FAO Jobs...", "→ ")
    results = []

    fao_urls = [
        # Página de empleos de la Oficina Regional ALC (HTML estático)
        "https://www.fao.org/americas/jobs/en",
        # Portal de vacantes FAO en New York
        "https://www.fao.org/new-york/careers/en",
        # Portal evaluaciones FAO (publica vacantes de consultores evaluadores)
        "https://www.fao.org/evaluation/about-us/vacancies/en",
        # jobs.fao.org — SSL antiguo, forzar verify=False
        "https://jobs.fao.org/careersection/fao_external/jobsearch.ftl?lang=en",
    ]

    for url in fao_urls:
        try:
            r = session.get(url, timeout=20, verify=False)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")

            # 1. jobs.fao.org (Taleo): filas con clase odd/even
            for row in soup.select("tr.listrow, tr.odd, tr.even"):
                a = row.find("a")
                if not a:
                    continue
                title = a.get_text(strip=True)
                href  = a.get("href", "")
                link  = href if href.startswith("http") else "https://jobs.fao.org" + href
                date_cell = row.find(class_=re.compile(r"date|closing", re.I))
                deadline  = date_cell.get_text(strip=True) if date_cell else "A verificar"
                if not is_relevant(title, link):
                    continue
                tipo, afinidad, _ = classify(title, "FAO")
                results.append({
                    "Título":       title,
                    "Organización": "FAO",
                    "Tipo":         tipo,
                    "Región":       infer_region(title),
                    "Fecha límite": deadline,
                    "Enlace":       link,
                    "Afinidad":     afinidad,
                    "Prioridad":    "Alta",
                })

            # 2. FSN Forum / Página ALC: encabezados de artículo con enlace
            for a in soup.select("h3 a, h2 a, .views-field-title a, .field-title a"):
                title = a.get_text(strip=True)
                href  = a.get("href", "")
                if not title or len(title) < 10:
                    continue
                link = href if href.startswith("http") else "https://www.fao.org" + href
                if not is_relevant(title, link):
                    continue
                tipo, afinidad, _ = classify(title, "FAO")
                results.append({
                    "Título":       title,
                    "Organización": "FAO",
                    "Tipo":         tipo,
                    "Región":       infer_region(title),
                    "Fecha límite": "A verificar",
                    "Enlace":       link,
                    "Afinidad":     afinidad,
                    "Prioridad":    "Media",
                })

        except Exception as e:
            log(f"Error FAO ({url}): {e}", "  ✗ ")

        time.sleep(1)

    # Deduplicar por título
    seen, unique = set(), []
    for item in results:
        key = make_id(item["Título"], item["Organización"])
        if key not in seen:
            seen.add(key)
            unique.append(item)

    log(f"{len(unique)} oportunidades relevantes encontradas.", "  ✓ ")
    return unique


def scrape_iadb(session: requests.Session) -> list:
    """
    IDB: la página de consultores bloquea scraping (403).
    Usamos el buscador público de proyectos y convocatorias abiertas
    accesibles sin autenticación.
    """
    log("IDB / IADB...", "→ ")
    results = []

    # Páginas que sí responden sin 403
    urls = [
        "https://www.iadb.org/en/sector/agriculture/projects",
        "https://idbinvest.org/en/sectors/agribusiness",
    ]

    for url in urls:
        try:
            r = session.get(url, timeout=20)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")

            # Buscar artículos, cards o secciones con títulos de proyectos
            for el in soup.select("article a, .card a, .project-title a, h3 a, h2 a"):
                title = el.get_text(strip=True)
                href  = el.get("href", "")
                if not title or len(title) < 15:
                    continue
                link = href if href.startswith("http") else "https://www.iadb.org" + href
                if not is_relevant(title, link):
                    continue
                tipo, afinidad, _ = classify(title, "IDB")
                results.append({
                    "Título":       title,
                    "Organización": "IDB / BID",
                    "Tipo":         tipo,
                    "Región":       infer_region(title),
                    "Fecha límite": "A verificar en portal IDB",
                    "Enlace":       link,
                    "Afinidad":     afinidad,
                    "Prioridad":    "Media",
                })

        except Exception as e:
            log(f"Error IDB ({url}): {e}", "  ✗ ")

        time.sleep(1)

    # Deduplicar por enlace
    seen, unique = set(), []
    for item in results:
        if item["Enlace"] not in seen:
            seen.add(item["Enlace"])
            unique.append(item)

    log(f"{len(unique)} oportunidades relevantes encontradas.", "  ✓ ")
    return unique


def scrape_devex(session: requests.Session) -> list:
    """
    Devex: scraping de resultados de búsqueda pública.
    La mayoría de detalles requieren suscripción, pero los títulos
    y slugs son accesibles en el HTML del listado.
    """
    log("Devex...", "→ ")
    results = []

    queries = [
        "agriculture food security consultant Latin America",
        "rural development food policy consultant 2026",
        "bioeconomy agrifood systems consultant",
        "agriculture consultant Caribbean 2026",
        "consultant FAO IFAD WFP Rome Geneva headquarters agriculture",
        "agrifood consultant European Commission Brussels 2026",
    ]
    base_search = "https://www.devex.com/jobs/q"

    seen_links = set()
    for query in queries:
        try:
            r = session.get(base_search, params={"q": query}, timeout=20)
            soup = BeautifulSoup(r.text, "lxml")

            # Intentar selectores del listado de Devex
            for a in soup.select(
                "h2.title a, h3.title a, .job-title a, "
                "a[data-automation='job-title'], a[href*='/jobs/']"
            ):
                title = a.get_text(strip=True)
                href  = a.get("href", "")
                if not title or len(title) < 8:
                    continue
                link = href if href.startswith("http") else "https://www.devex.com" + href
                if link in seen_links or not is_relevant(title, link):
                    continue
                seen_links.add(link)

                tipo, afinidad, _ = classify(title, "Devex")
                results.append({
                    "Título":       title,
                    "Organización": "A verificar (Devex)",
                    "Tipo":         tipo,
                    "Región":       infer_region(title),
                    "Fecha límite": "A verificar en Devex",
                    "Enlace":       link,
                    "Afinidad":     afinidad,
                    "Prioridad":    "Media",
                })

            # JSON embebido (React/Next.js)
            for script in soup.find_all("script", type="application/json"):
                try:
                    _dig_json(json.loads(script.string or ""), results, seen_links)
                except Exception:
                    pass

            time.sleep(1.5)

        except Exception as e:
            log(f"Error Devex: {e}", "  ✗ ")

    log(f"{len(results)} oportunidades relevantes encontradas.", "  ✓ ")
    return results


def _dig_json(obj, results: list, seen: set, depth: int = 0) -> None:
    """Extrae jobs de JSON embebido en páginas React/Next, recursivamente."""
    if depth > 8:
        return
    if isinstance(obj, dict):
        title = obj.get("title") or obj.get("name") or ""
        url   = obj.get("url") or obj.get("href") or obj.get("link") or ""
        if title and url and isinstance(url, str) and url.startswith("http"):
            if url not in seen and is_relevant(str(title), str(url)):
                seen.add(url)
                tipo, afinidad, _ = classify(str(title), "Devex")
                results.append({
                    "Título":       str(title),
                    "Organización": "A verificar (Devex)",
                    "Tipo":         tipo,
                    "Región":       infer_region(str(title)),
                    "Fecha límite": "A verificar en Devex",
                    "Enlace":       url,
                    "Afinidad":     afinidad,
                    "Prioridad":    "Media",
                })
        for v in obj.values():
            _dig_json(v, results, seen, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _dig_json(item, results, seen, depth + 1)


def scrape_ungm(session: requests.Session) -> list:
    """
    UNGM — UN Global Marketplace (ungm.org).
    Portal unificado de compras del sistema ONU: UNDP, FAO, IFAD, PMA, OIT,
    OMS y más publican aquí sus contratos antes que en sus portales propios.
    Scrapeamos la lista pública de licitaciones abiertas con filtros de texto.
    """
    log("UNGM — UN Global Marketplace...", "→ ")
    results = []

    # Endpoint público de búsqueda de avisos de procurement
    urls = [
        "https://www.ungm.org/Public/Notice?NoticeType=0&UNSPSCs=&deadline=&title=agriculture",
        "https://www.ungm.org/Public/Notice?NoticeType=0&UNSPSCs=&deadline=&title=food+security",
        "https://www.ungm.org/Public/Notice?NoticeType=0&UNSPSCs=&deadline=&title=rural+development",
        "https://www.ungm.org/Public/Notice?NoticeType=0&UNSPSCs=&deadline=&title=consultant",
        "https://www.ungm.org/Public/Notice?NoticeType=0&UNSPSCs=&deadline=&title=agricultura",
    ]

    seen_links: set = set()
    for url in urls:
        try:
            r = session.get(url, timeout=25)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")

            # Filas de la tabla de avisos
            for row in soup.select("table tbody tr, tr.notice-row, .notice-item"):
                # Título y enlace
                a = row.find("a", href=True)
                if not a:
                    continue
                title = a.get_text(strip=True)
                href  = a.get("href", "").strip()
                if not title or len(title) < 10:
                    continue
                link = href if href.startswith("http") else f"https://www.ungm.org{href}"
                if link in seen_links:
                    continue

                # Organización (segunda columna típicamente)
                cells = row.find_all(["td", "span", "div"])
                org   = "UNGM / ONU"
                for cell in cells:
                    txt = cell.get_text(strip=True)
                    if any(x in txt for x in ["UNDP", "FAO", "WFP", "IFAD", "ILO", "WHO", "UNOPS"]):
                        org = txt[:80]
                        break

                # Fecha límite
                deadline = "A verificar"
                for cell in cells:
                    txt = cell.get_text(strip=True)
                    m = re.search(r"(\d{4}-\d{2}-\d{2}|\d{1,2}\s+\w+\s+20\d{2})", txt)
                    if m:
                        deadline = m.group(1)
                        break

                if not is_relevant(title + " " + org, link, org):
                    continue

                seen_links.add(link)
                tipo, afinidad, prioridad = classify(title, org)
                results.append({
                    "Título":       title,
                    "Organización": org,
                    "Tipo":         tipo,
                    "Región":       infer_region(title + " " + org),
                    "Fecha límite": deadline,
                    "Enlace":       link,
                    "Afinidad":     afinidad,
                    "Prioridad":    prioridad,
                })

            time.sleep(1)

        except Exception as e:
            log(f"Error UNGM ({url}): {e}", "  ✗ ")

    log(f"{len(results)} oportunidades relevantes encontradas.", "  ✓ ")
    return results


def scrape_cepal(session: requests.Session) -> list:
    """
    CEPAL/ECLAC — scraping de sección de vacantes y convocatorias.
    CEPAL publica consultorías vinculadas a política económica, comercio y
    desarrollo productivo en ALC, muy alineadas con el perfil CEO.
    """
    log("CEPAL / ECLAC...", "→ ")
    results = []

    urls = [
        "https://www.cepal.org/es/careers",
        "https://www.cepal.org/es/convocatorias",
        "https://www.eclac.org/en/careers",
    ]

    seen_links: set = set()
    for url in urls:
        try:
            r = session.get(url, timeout=20)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")

            for a in soup.select(
                "h2 a, h3 a, h4 a, "
                ".views-field-title a, .field-content a, "
                ".vacancy a, .consultancy a, article a"
            ):
                title = a.get_text(strip=True)
                href  = a.get("href", "").strip()
                if not title or len(title) < 10:
                    continue
                link = href if href.startswith("http") else f"https://www.cepal.org{href}"
                if link in seen_links:
                    continue
                if not is_relevant(title, link, "CEPAL"):
                    continue

                seen_links.add(link)
                tipo, afinidad, _ = classify(title, "CEPAL")
                results.append({
                    "Título":       title,
                    "Organización": "CEPAL",
                    "Tipo":         tipo,
                    "Región":       infer_region(title),
                    "Fecha límite": "A verificar en CEPAL",
                    "Enlace":       link,
                    "Afinidad":     afinidad,
                    "Prioridad":    "Alta",
                })

            time.sleep(1)

        except Exception as e:
            log(f"Error CEPAL ({url}): {e}", "  ✗ ")

    log(f"{len(results)} oportunidades relevantes encontradas.", "  ✓ ")
    return results


def scrape_rimisp_procasur(session: requests.Session) -> list:
    """
    RIMISP y PROCASUR — centros especializados en desarrollo rural ALC.
    Muy alineados con el foco temático de Grupo CEO.
    """
    log("RIMISP / PROCASUR...", "→ ")
    results = []

    sources = [
        ("https://www.rimisp.org/convocatorias/", "RIMISP"),
        ("https://www.rimisp.org/jobs/", "RIMISP"),
        ("https://www.procasur.org/convocatorias", "PROCASUR"),
        ("https://www.procasur.org/oportunidades", "PROCASUR"),
    ]

    seen_links: set = set()
    for url, org_name in sources:
        try:
            r = session.get(url, timeout=20)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")

            for a in soup.select("h2 a, h3 a, h4 a, article a, .entry-title a, .post-title a"):
                title = a.get_text(strip=True)
                href  = a.get("href", "").strip()
                if not title or len(title) < 8:
                    continue
                link = href if href.startswith("http") else f"https://www.{org_name.lower()}.org{href}"
                if link in seen_links:
                    continue
                if not is_relevant(title, link, org_name):
                    continue

                seen_links.add(link)
                tipo, afinidad, _ = classify(title, org_name)
                results.append({
                    "Título":       title,
                    "Organización": org_name,
                    "Tipo":         tipo,
                    "Región":       infer_region(title),
                    "Fecha límite": "A verificar en portal",
                    "Enlace":       link,
                    "Afinidad":     afinidad,
                    "Prioridad":    "Alta",
                })

            time.sleep(1)

        except Exception as e:
            log(f"Error {org_name} ({url}): {e}", "  ✗ ")

    log(f"{len(results)} oportunidades relevantes encontradas.", "  ✓ ")
    return results


# ── Motor principal ──────────────────────────────────────────────────────────

def run_all_scrapers() -> list:
    session = get_session()
    all_results = []

    # ── Tavily (fuente principal si la API key está disponible) ──────────────
    tavily_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if tavily_key:
        try:
            found = scrape_tavily(tavily_key)
            all_results.extend(found)
        except Exception as e:
            log(f"Error no controlado en Tavily: {e}", "  ✗ ")
        time.sleep(1)
    else:
        log("TAVILY_API_KEY no configurada — omitiendo Tavily.", "  ⚠ ")
        log("Para activarlo: export TAVILY_API_KEY='tvly-xxxx'  (app.tavily.com)", "    ")

    # ── Scrapers HTML clásicos ───────────────────────────────────────────────
    scrapers = [
        ("ReliefWeb",       scrape_reliefweb),
        ("UNDP",            scrape_undp),
        ("UNGM",            scrape_ungm),
        ("FAO",             scrape_fao),
        ("CEPAL",           scrape_cepal),
        ("IDB",             scrape_iadb),
        ("RIMISP/PROCASUR", scrape_rimisp_procasur),
        ("Devex",           scrape_devex),
    ]
    for name, fn in scrapers:
        try:
            found = fn(session)
            all_results.extend(found)
        except Exception as e:
            log(f"Error no controlado en {name}: {e}", "  ✗ ")
        time.sleep(1)

    return all_results


def filter_new(candidates: list, existing_ids: set, discarded_ids: set | None = None) -> list:
    """Filtra candidatos para quedarse solo con los realmente nuevos.

    - existing_ids: todos los IDs ya en el CSV (evita duplicados).
    - discarded_ids: IDs marcados como Descartada; NUNCA se re-agregan.
    - Aplica además criterios aprendidos desde la app (criterios_aprendidos.json).
    """
    if discarded_ids is None:
        discarded_ids = set()

    # Cargar criterios aprendidos de descarte
    criterios = load_criterios_aprendidos()
    señales_extra    = [s.lower() for s in criterios.get("señales_exclusion", [])]
    orgs_excluidas   = [o.lower() for o in criterios.get("organizaciones_excluidas", [])]
    patrones_titulo  = [p.lower() for p in criterios.get("patrones_titulo", [])]

    seen_this_run = set()
    new_ones = []
    for opp in candidates:
        oid = make_id(opp["Título"], opp["Organización"])

        # Exclusiones duras
        if oid in existing_ids or oid in discarded_ids or oid in seen_this_run:
            continue

        # Criterios aprendidos: señales en título+org
        texto = (opp.get("Título", "") + " " + opp.get("Organización", "")).lower()
        if any(s in texto for s in señales_extra):
            log(f"  [criterio aprendido] Señal de exclusión en: {opp['Título'][:60]}", "  ⛔ ")
            continue
        if any(o in opp.get("Organización", "").lower() for o in orgs_excluidas):
            log(f"  [criterio aprendido] Org excluida: {opp.get('Organización','')[:50]}", "  ⛔ ")
            continue
        if any(p in opp.get("Título", "").lower() for p in patrones_titulo):
            log(f"  [criterio aprendido] Patrón en título: {opp['Título'][:60]}", "  ⛔ ")
            continue

        seen_this_run.add(oid)
        new_ones.append(opp)
    return new_ones


def write_report(new_opps: list) -> None:
    today = date.today().strftime("%d/%m/%Y")
    sep   = "=" * 72
    lines = [sep, f"  NUEVAS OPORTUNIDADES DE CONSULTORÍA — {today}", sep, ""]

    if not new_opps:
        lines += [
            "  No se encontraron oportunidades nuevas esta semana.",
            "  El archivo oportunidades_consultoria.csv está actualizado.",
            "",
        ]
    else:
        grupos = {"Alta": [], "Media": [], "Baja": []}
        for o in new_opps:
            grupos.get(o.get("Prioridad", "Baja"), grupos["Baja"]).append(o)

        for nivel, badge in [("Alta", "🔴"), ("Media", "🟡"), ("Baja", "🟢")]:
            if not grupos[nivel]:
                continue
            lines += [
                f"{badge}  PRIORIDAD {nivel.upper()} — {len(grupos[nivel])} oportunidad(es)",
                "-" * 72,
            ]
            for i, o in enumerate(grupos[nivel], 1):
                lines += [
                    f"  {i}. {o['Título']}",
                    f"     Organización : {o['Organización']}",
                    f"     Tipo / Afinidad : {o['Tipo']} / {o['Afinidad']}",
                    f"     Región       : {o['Región']}",
                    f"     Fecha límite : {o['Fecha límite']}",
                    f"     Enlace       : {o['Enlace']}",
                    "",
                ]
            lines.append("")

    lines += [
        "-" * 72,
        f"  Total nuevas esta ejecución : {len(new_opps)}",
        f"  CSV actualizado             : {CSV_PATH.name}",
        f"  Reporte generado            : {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        sep,
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def print_summary(new_opps: list) -> None:
    sep = "=" * 72
    print()
    print(sep)
    print("  RESUMEN DE EJECUCIÓN")
    print(sep)
    if not new_opps:
        print("  Sin oportunidades nuevas esta semana.")
    else:
        badge_map = {"Alta": "🔴", "Media": "🟡", "Baja": "🟢"}
        for o in new_opps:
            b = badge_map.get(o["Prioridad"], "  ")
            t = o["Título"][:56]
            d = o["Fecha límite"][:16]
            print(f"  {b}  {t:<56}  {d}")
    print()
    print(f"  Nuevas encontradas : {len(new_opps)}")
    print(f"  CSV                : {CSV_PATH}")
    print(f"  Reporte            : {REPORT_PATH}")
    print(sep)
    print()


# ── Entrada ──────────────────────────────────────────────────────────────────

def main() -> None:
    banner = [
        "╔══════════════════════════════════════════════════════════════════════╗",
        "║   BUSCADOR — ICyT+Productividad / Comercio+Geopolítica / ALC        ║",
        f"║   {datetime.now().strftime('%d %b %Y  %H:%M')}                                             ║",
        "╚══════════════════════════════════════════════════════════════════════╝",
    ]
    print("\n" + "\n".join(banner) + "\n")

    log("Cargando oportunidades previas del CSV...")
    existing_ids, discarded_ids = load_existing_ids()
    log(f"{len(existing_ids)} oportunidades ya conocidas ({len(discarded_ids)} descartadas — bloqueadas permanentemente).")
    print()

    tavily_active = bool(os.environ.get("TAVILY_API_KEY", "").strip())
    n_sources = 9 if tavily_active else 8  # 8 scrapers HTML + Tavily opcional
    log(f"Iniciando búsqueda en {n_sources} fuentes{' (Tavily activo)' if tavily_active else ''}...")
    print()
    all_found = run_all_scrapers()
    print()

    log(f"Total bruto recuperado : {len(all_found)} registros.")
    new_opps = filter_new(all_found, existing_ids, discarded_ids)
    log(f"Oportunidades nuevas   : {len(new_opps)}")
    print()

    if new_opps:
        log("Escribiendo en CSV...")
        append_to_csv(new_opps)

    log("Generando nuevas_esta_semana.txt...")
    write_report(new_opps)

    print_summary(new_opps)


if __name__ == "__main__":
    main()
