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
    "agriculture", "food", "rural", "agrifood", "agro", "bioeconomy",
    "food security", "nutrition", "value chain", "agribusiness",
    "agroforestry", "livestock", "crop", "farm", "harvest",
    "agricultura", "alimentaria", "agroalimentar", "bioeconomía",
    "cadenas de valor", "seguridad alimentaria", "desarrollo rural",
    "policy", "institutional", "trade", "commerce", "innovation",
    "política", "institucional", "comercio", "innovación", "sostenibilidad",
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
]

# Palabras que indican que NO es una convocatoria — descarta el resultado
EXCLUSION_SIGNALS = [
    "informe", "reporte", "report ", " report:", "boletín", "boletin",
    "newsletter", "press release", "comunicado", "nota de prensa",
    "news release", "noticias", " news:", "blog", "opinion", "opinión",
    "artículo", "articulo", "publicación", "publicacion", "publication",
    "estudio", "análisis", "analisis", "research paper", "working paper",
    "policy brief", "policy paper", "discussion paper", "fact sheet",
    "annual report", "informe anual", "memoria anual",
    "evento", "taller", "webinar", "seminario", "conferencia", "foro",
    "workshop", " forum", "capacitación", "training course",
    "lanzamiento", "launch of", "presenta ", "presentación",
    "donación", "donation", "grant announcement", "award announcement",
    "resultado", "resultado del", "ganador", "winner",
]

# Patrones en la URL que indican noticias o contenido editorial
EXCLUSION_URL_PATTERNS = [
    # Inglés
    "/news/", "/blog/", "/press/", "/media/", "/stories/",
    "/opinion/", "/report/", "/publication/", "/document/",
    "/event/", "/training/", "/workshop/", "/webinar/",
    "/update/", "/article/", "/feature/", "/resource/",
    # Español (faltan en muchos sitios de OI)
    "/prensa/", "/noticias/", "/noticia/", "/newsletter/",
    "/publicacion/", "/publicaciones/", "/eventos/", "/evento/",
    "/capacitacion/", "/taller/", "/webinars/",
    # Redes sociales y anclas
    "twitter.com", "linkedin.com", "youtube.com", "facebook.com",
    "mailto:", "#",
]

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


def is_relevant(text: str, url: str = "") -> bool:
    """
    Devuelve True solo si el texto corresponde a una convocatoria de consultoría
    relevante al sector agroalimentario/desarrollo rural.

    Criterios (los tres deben cumplirse):
    1. Contiene al menos una palabra del sector (KEYWORDS)
    2. Contiene al menos una señal de convocatoria (PROCUREMENT_SIGNALS)
    3. No contiene señales de noticias/informes (EXCLUSION_SIGNALS)
    4. La URL no apunta a secciones editoriales (EXCLUSION_URL_PATTERNS)
    """
    t = text.lower()
    u = url.lower()

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


def load_existing_ids() -> set:
    if not CSV_PATH.exists():
        return set()
    ids = set()
    with open(CSV_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ids.add(make_id(row.get("Título", ""), row.get("Organización", "")))
    return ids


def append_to_csv(opportunities: list) -> None:
    file_exists = CSV_PATH.exists()
    with open(CSV_PATH, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        for opp in opportunities:
            writer.writerow(opp)


def classify(title: str, org: str) -> tuple:
    t = (title + " " + org).lower()
    if any(w in t for w in ["firma", "empresa", "company", "firm", "consortium", "rfp"]):
        tipo = "Firma"
        afinidad = "Empresarial"
    elif any(w in t for w in ["individual", "ic -", "consultor individual"]):
        tipo = "Individual"
        afinidad = "Individual"
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
    # América Latina
    "consultancy opportunity agriculture Latin America 2025 2026",
    "consultoría agricultura desarrollo rural América Latina 2026",
    "food security consultant UNDP FAO LAC 2026",
    "agrifood policy advisor Latin America Caribbean 2026",
    # Caribe
    "consultancy Caribbean agriculture food security 2026",
    "consultor Caribe seguridad alimentaria desarrollo rural 2026",
    # Sedes internacionales en Europa (FAO Roma, FIDA, IFAD, OIT Ginebra, etc.)
    "consultant FAO Rome IFAD WFP headquarters 2026 agriculture",
    "consultancy UNDP Geneva ILO WTO food agriculture policy 2026",
    "consultant European Union Brussels agriculture rural development 2026",
    "consultoría organismos internacionales Europa Roma Ginebra 2026",
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
                    # Organismos globales
                    "procurement-notices.undp.org",
                    "jobs.undp.org",
                    "reliefweb.int",
                    "devex.com",
                    "jobs.fao.org",
                    "fao.org",
                    "ifad.org",
                    "wfp.org",
                    "worldbank.org",
                    "iadb.org",
                    "fontagro.org",
                    # Sedes europeas — OI con HQ en Europa
                    "ted.europa.eu",           # TED – licitaciones UE
                    "ec.europa.eu",            # Comisión Europea
                    "europeaid.ec.europa.eu",  # EuropeAid / INTPA
                    "ilo.org",                 # OIT – Ginebra
                    "who.int",                 # OMS – Ginebra
                    "wto.org",                 # OMC – Ginebra
                    "oecd.org",                # OCDE – París
                    "cabi.org",                # CABI – Londres
                    "cirad.fr",                # CIRAD – París / agrifood
                    "ebrd.com",                # BERD – Londres
                    "eib.org",                 # BEI – Luxemburgo
                    # USAID y otros
                    "grants.gov",
                    "usaid.gov",
                    "foreignassistance.gov",
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
        "undp.org":       "UNDP",
        "reliefweb.int":  "ReliefWeb",
        "devex.com":      "Devex",
        "fao.org":        "FAO",
        "iadb.org":       "IDB / BID",
        "ifad.org":       "IFAD / FIDA",
        "worldbank.org":  "Banco Mundial",
        "ted.europa.eu":  "UE / EuropeAid",
        "grants.gov":     "USAID / US Gov",
        "iica.int":       "IICA",
        "fontagro.org":   "FONTAGRO",
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
        ("ReliefWeb",    scrape_reliefweb),
        ("UNDP",         scrape_undp),
        ("FAO",          scrape_fao),
        ("IDB",          scrape_iadb),
        ("Devex",        scrape_devex),
    ]
    for name, fn in scrapers:
        try:
            found = fn(session)
            all_results.extend(found)
        except Exception as e:
            log(f"Error no controlado en {name}: {e}", "  ✗ ")
        time.sleep(1)

    return all_results


def filter_new(candidates: list, existing_ids: set) -> list:
    seen_this_run = set()
    new_ones = []
    for opp in candidates:
        oid = make_id(opp["Título"], opp["Organización"])
        if oid not in existing_ids and oid not in seen_this_run:
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
        "║   BUSCADOR DE CONSULTORÍAS — Agroalimentación / Desarrollo / ALC    ║",
        f"║   {datetime.now().strftime('%d %b %Y  %H:%M')}                                             ║",
        "╚══════════════════════════════════════════════════════════════════════╝",
    ]
    print("\n" + "\n".join(banner) + "\n")

    log("Cargando oportunidades previas del CSV...")
    existing_ids = load_existing_ids()
    log(f"{len(existing_ids)} oportunidades ya conocidas.")
    print()

    tavily_active = bool(os.environ.get("TAVILY_API_KEY", "").strip())
    n_sources = 6 if tavily_active else 5
    log(f"Iniciando búsqueda en {n_sources} fuentes{' (Tavily activo)' if tavily_active else ''}...")
    print()
    all_found = run_all_scrapers()
    print()

    log(f"Total bruto recuperado : {len(all_found)} registros.")
    new_opps = filter_new(all_found, existing_ids)
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
