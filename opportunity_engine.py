#!/usr/bin/env python3
"""Motor determinístico de validación, puntuación y deduplicación.

Compatible con Python 3.9. No depende de Streamlit.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

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

ALC_COUNTRIES = {
    "argentina", "belize", "belice", "bolivia", "brazil", "brasil", "chile",
    "colombia", "costa rica", "cuba", "dominica", "dominican republic",
    "república dominicana", "republica dominicana", "ecuador", "el salvador",
    "grenada", "granada", "guatemala", "guyana", "haiti", "haití", "honduras",
    "jamaica", "méxico", "mexico", "nicaragua", "panama", "panamá", "paraguay",
    "peru", "perú", "saint lucia", "santa lucía", "suriname", "surinam",
    "trinidad and tobago", "trinidad y tobago", "uruguay", "venezuela",
    "antigua and barbuda", "antigua y barbuda", "bahamas", "barbados",
    "saint kitts and nevis", "saint vincent and the grenadines",
}

COUNTRY_ALIASES = {
    "argentina": "Argentina", "belize": "Belice", "belice": "Belice",
    "bolivia": "Bolivia", "brazil": "Brasil", "brasil": "Brasil",
    "chile": "Chile", "colombia": "Colombia", "costa rica": "Costa Rica",
    "cuba": "Cuba", "dominica": "Dominica", "dominican republic": "República Dominicana",
    "república dominicana": "República Dominicana", "republica dominicana": "República Dominicana",
    "ecuador": "Ecuador", "el salvador": "El Salvador", "grenada": "Granada",
    "granada": "Granada", "guatemala": "Guatemala", "guyana": "Guyana",
    "haiti": "Haití", "haití": "Haití", "honduras": "Honduras",
    "jamaica": "Jamaica", "mexico": "México", "méxico": "México",
    "nicaragua": "Nicaragua", "panama": "Panamá", "panamá": "Panamá",
    "paraguay": "Paraguay", "peru": "Perú", "perú": "Perú",
    "saint lucia": "Santa Lucía", "santa lucía": "Santa Lucía",
    "suriname": "Surinam", "surinam": "Surinam",
    "trinidad and tobago": "Trinidad y Tobago", "trinidad y tobago": "Trinidad y Tobago",
    "uruguay": "Uruguay", "venezuela": "Venezuela", "bahamas": "Bahamas",
    "barbados": "Barbados", "antigua and barbuda": "Antigua y Barbuda",
    "antigua y barbuda": "Antigua y Barbuda",
}

ALC_ISO3 = {
    "ARG", "BLZ", "BOL", "BRA", "CHL", "COL", "CRI", "CUB", "DMA", "DOM",
    "ECU", "SLV", "GRD", "GTM", "GUY", "HTI", "HND", "JAM", "MEX", "NIC",
    "PAN", "PRY", "PER", "LCA", "SUR", "TTO", "URY", "VEN", "ATG", "BHS",
    "BRB", "KNA", "VCT",
}

COUNTRY_TO_REGION = {
    "Argentina": "Cono Sur – Argentina", "Chile": "Cono Sur – Chile",
    "Paraguay": "Cono Sur – Paraguay", "Uruguay": "Cono Sur – Uruguay",
    "Brasil": "América del Sur – Brasil", "Bolivia": "América del Sur – Bolivia",
    "Colombia": "América del Sur – Colombia", "Ecuador": "América del Sur – Ecuador",
    "Guyana": "América del Sur – Guyana", "Perú": "América del Sur – Perú",
    "Surinam": "América del Sur – Surinam", "Venezuela": "América del Sur – Venezuela",
    "Belice": "Centroamérica – Belice", "Costa Rica": "Centroamérica – Costa Rica",
    "El Salvador": "Centroamérica – El Salvador", "Guatemala": "Centroamérica – Guatemala",
    "Honduras": "Centroamérica – Honduras", "Nicaragua": "Centroamérica – Nicaragua",
    "Panamá": "Centroamérica – Panamá", "México": "México",
    "Cuba": "Caribe – Cuba", "Dominica": "Caribe – Dominica",
    "República Dominicana": "Caribe – República Dominicana", "Granada": "Caribe – Granada",
    "Haití": "Caribe – Haití", "Jamaica": "Caribe – Jamaica", "Santa Lucía": "Caribe – Santa Lucía",
    "Trinidad y Tobago": "Caribe – Trinidad y Tobago", "Bahamas": "Caribe – Bahamas",
    "Barbados": "Caribe – Barbados", "Antigua y Barbuda": "Caribe – Antigua y Barbuda",
}

SECTOR_TERMS = [
    "agricultur", "agricola", "agricolo", "agropecu", "agro", "agrifood", "alimentari", "food system", "food security", "nutrition",
    "rural", "ganader", "pecuari", "livestock", "farming", "farmer", "productor", "crop", "fisher", "pesca", "acuicultur", "aquaculture",
    "bioeconom", "biotechnology", "climate-smart", "climate smart", "regenerative",
    "agroecolog", "value chain", "cadena de valor", "supply chain", "sustainable",
    "sostenib", "trade policy", "agricultural trade", "comercio agro", "market access",
    "policy evaluation", "impact evaluation", "monitoring and evaluation", "baseline",
    "linea de base", "línea de base", "econometric", "econometr", "innovation system",
    "technology transfer", "transferencia tecnol", "smallholder", "producer organization",
    "cooperativ", "land governance", "soil", "water management", "irrigation",
]

STRONG_PROCUREMENT_TERMS = [
    "request for proposal", "request for expressions of interest", "request for expression of interest",
    "expression of interest", "terms of reference", "consultancy", "consulting services",
    "individual consultant", "call for individual consultant", "consultoría", "consultoria",
    "solicitud de propuesta", "expresión de interés", "expresion de interes", "términos de referencia",
    "terminos de referencia", "concurso de méritos", "technical assistance services",
    "consultant services", "rfp", "eoi", "tor",
]

WEAK_PROCUREMENT_TERMS = [
    "consultant", "consultor", "specialist", "expert", "advisor", "adviser",
    "contract", "assignment", "deliverables", "deadline", "closing date", "apply",
]

HARD_EXCLUSION_TERMS = [
    "press release", "news release", "newsletter", "blog post", "policy brief",
    "research paper", "working paper", "annual report", "informe anual", "webinar",
    "training course", "curso en línea", "course registration", "curriculum vitae",
    "resume ", "profile", "wikipedia", "management plan", "meeting report",
    "procurement plan", "project appraisal document", "evaluation report",
    "supply of agricultural", "supply and delivery", "purchase of", "procurement of goods",
    "vehicles", "vehículos", "equipment", "construction works", "civil works",
    "catering", "canteen", "printing services", "graphic services", "translation services",
    "internship", "fellowship", "phd", "professor", "lecturer", "driver", "security guard",
]

EXCLUDED_URL_PARTS = [
    "/news/", "/blog/", "/press/", "/publication/", "/publications/", "/report/",
    "/reports/", "/event/", "/events/", "/webinar/", "wikipedia.org", "/profile/",
    "openknowledge.fao.org", "cgspace.cgiar.org/bitstreams/", "thedocs.worldbank.org",
]

GLOBAL_TERMS = [
    "global", "worldwide", "multiple countries", "latin america and the caribbean",
    "latin america & the caribbean", "lac region", "remote", "home-based", "home based",
    "regional", "headquarters", "roster",
]

TRUSTED_DIRECT_SOURCES = {"UNDP", "ReliefWeb", "FAO", "World Bank"}

@dataclass
class Opportunity:
    title: str
    organization: str
    url: str
    source: str
    country: str = ""
    country_code: str = ""
    region: str = ""
    deadline: str = ""
    publication_date: str = ""
    reference: str = ""
    notice_type: str = ""
    summary: str = ""
    raw_text: str = ""
    source_score: float = 0.0
    source_mode: str = "direct"  # direct | exploratory
    extra: Dict[str, str] = field(default_factory=dict)

@dataclass
class Assessment:
    decision: str  # accept | stage | reject
    score: int
    reasons: List[str]
    canonical_id: str
    country: str
    region: str
    deadline_iso: str
    opportunity_type: str
    affinity: str
    priority: str


def strip_accents(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value or "") if not unicodedata.combining(c))


def normalize_text(value: str) -> str:
    value = strip_accents(value).lower()
    value = re.sub(r"\([^)]*\b(?:undp|rfp|eoi|ic)[-_ /]?[a-z0-9-]+[^)]*\)", " ", value, flags=re.I)
    value = re.sub(r"[,;:|/\\]+", " ", value)
    value = re.sub(r"\bcopy\b|\bduplicate\b", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def canonical_url(url: str) -> str:
    if not url:
        return ""
    try:
        parts = urlsplit(url.strip())
        host = parts.netloc.lower().replace("www.", "")
        path = re.sub(r"/+", "/", parts.path).rstrip("/")
        keep_keys = {"id", "nego_id", "notice_id", "projectid", "project_id"}
        query_items = [(k.lower(), v) for k, v in parse_qsl(parts.query, keep_blank_values=False)
                       if k.lower() in keep_keys]
        query = urlencode(sorted(query_items))
        return urlunsplit((parts.scheme.lower() or "https", host, path, query, ""))
    except Exception:
        return url.strip().lower()


def canonical_id(opp: Opportunity) -> str:
    org = normalize_text(opp.organization)
    ref = normalize_text(opp.reference)
    if ref:
        raw = "ref|{}|{}".format(org, ref)
    else:
        curl = canonical_url(opp.url)
        if curl:
            raw = "url|{}".format(curl)
        else:
            raw = "title|{}|{}".format(org, normalize_text(opp.title))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def parse_date(value: str) -> Optional[date]:
    if not value:
        return None
    value = value.strip()
    if value.lower() in {"a verificar", "n/a", "—", "-", "none"}:
        return None
    value = re.sub(r"(?<=\d)(st|nd|rd|th)\b", "", value, flags=re.I)
    value = value.replace("Sept", "Sep")
    patterns = [
        "%Y-%m-%d", "%d-%b-%Y", "%d-%B-%Y", "%d %b %Y", "%d %B %Y",
        "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%b %d, %Y", "%B %d, %Y",
    ]
    for fmt in patterns:
        try:
            return datetime.strptime(value[:30].strip(), fmt).date()
        except ValueError:
            continue
    m = re.search(r"(20\d{2})-(\d{2})-(\d{2})", value)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def date_iso(value: str) -> str:
    parsed = parse_date(value)
    return parsed.isoformat() if parsed else "A verificar"


def _whole_phrase(text: str, phrase: str) -> bool:
    norm_text = " {} ".format(normalize_text(text))
    norm_phrase = normalize_text(phrase)
    return re.search(r"(?<![a-z0-9]){}(?![a-z0-9])".format(re.escape(norm_phrase)), norm_text) is not None


def identify_country(opp: Opportunity) -> str:
    if opp.country:
        key = normalize_text(opp.country)
        if key in COUNTRY_ALIASES:
            return COUNTRY_ALIASES[key]
        return opp.country.strip()
    code = (opp.country_code or "").upper().strip()
    if code in ALC_ISO3:
        for key, value in COUNTRY_ALIASES.items():
            if value and code == _country_iso3(value):
                return value
    text = "{} {} {}".format(opp.title, opp.summary, opp.raw_text[:800])
    # Frases más largas primero y con límites de palabra para impedir Chilengedwe -> Chile.
    for alias in sorted(COUNTRY_ALIASES.keys(), key=len, reverse=True):
        if _whole_phrase(text, alias):
            return COUNTRY_ALIASES[alias]
    if any(_whole_phrase(text, term) for term in GLOBAL_TERMS):
        return "Regional/Global"
    return "A verificar"


def _country_iso3(country: str) -> str:
    reverse = {
        "Argentina": "ARG", "Belice": "BLZ", "Bolivia": "BOL", "Brasil": "BRA",
        "Chile": "CHL", "Colombia": "COL", "Costa Rica": "CRI", "Cuba": "CUB",
        "Dominica": "DMA", "República Dominicana": "DOM", "Ecuador": "ECU",
        "El Salvador": "SLV", "Granada": "GRD", "Guatemala": "GTM", "Guyana": "GUY",
        "Haití": "HTI", "Honduras": "HND", "Jamaica": "JAM", "México": "MEX",
        "Nicaragua": "NIC", "Panamá": "PAN", "Paraguay": "PRY", "Perú": "PER",
        "Santa Lucía": "LCA", "Surinam": "SUR", "Trinidad y Tobago": "TTO",
        "Uruguay": "URY", "Venezuela": "VEN", "Antigua y Barbuda": "ATG",
        "Bahamas": "BHS", "Barbados": "BRB",
    }
    return reverse.get(country, "")


def infer_region(country: str, text: str = "") -> str:
    if country in COUNTRY_TO_REGION:
        return COUNTRY_TO_REGION[country]
    norm = normalize_text(text)
    if any(term in norm for term in ["latin america", "america latina", "caribbean", "caribe", "lac region"]):
        return "América Latina y Caribe"
    if country == "Regional/Global" or any(term in norm for term in ["global", "worldwide", "headquarters"]):
        return "Global"
    return "A verificar"


def is_alc_or_global(country: str, region: str, text: str = "") -> bool:
    if country in COUNTRY_TO_REGION:
        return True
    if country == "Regional/Global" or region in {"América Latina y Caribe", "Global"}:
        return True
    norm = normalize_text(text)
    return any(term in norm for term in ["latin america", "america latina", "caribbean", "caribe", "lac region", "global", "worldwide", "remote", "home based"])


def contains_sector(text: str) -> bool:
    norm = normalize_text(text)
    return any(term in norm for term in SECTOR_TERMS)


def contains_strong_procurement(text: str) -> bool:
    norm = normalize_text(text)
    return any(_whole_phrase(norm, term) for term in STRONG_PROCUREMENT_TERMS)


def contains_weak_procurement(text: str) -> bool:
    norm = normalize_text(text)
    return any(_whole_phrase(norm, term) for term in WEAK_PROCUREMENT_TERMS)


def exclusion_reason(text: str, url: str) -> Optional[str]:
    norm = normalize_text(text)
    for term in HARD_EXCLUSION_TERMS:
        if term in norm:
            return "Contenido excluido: {}".format(term)
    low_url = canonical_url(url)
    for part in EXCLUDED_URL_PARTS:
        if part in low_url:
            return "URL editorial/no contractual: {}".format(part)
    return None


def classify_type(text: str) -> str:
    norm = normalize_text(text)
    if any(term in norm for term in ["individual consultant", "consultor individual", "call for individual"]):
        return "Individual"
    if any(term in norm for term in ["firm", "firma", "company", "consortium", "request for proposal", "rfp"]):
        return "Firma"
    return "Ambos"


def classify_affinity(text: str, opportunity_type: str) -> str:
    norm = normalize_text(text)
    trade_terms = ["trade", "comercio", "market access", "negotiation", "negociacion", "tariff", "arancel", "geopolit", "wto", "omc"]
    enterprise_terms = ["business plan", "investment", "financial model", "feasibility", "private sector", "agribusiness"]
    if opportunity_type == "Firma" and any(term in norm for term in enterprise_terms):
        return "Empresarial"
    if any(term in norm for term in trade_terms):
        return "Comercio y Geopolítica"
    if any(term in norm for term in enterprise_terms):
        return "Empresarial"
    return "ICyT, Productividad y Desarrollo"


def assess(opp: Opportunity, today: Optional[date] = None) -> Assessment:
    today = today or date.today()
    full_text = "{} {} {} {} {}".format(
        opp.title, opp.organization, opp.notice_type, opp.summary, opp.raw_text[:2500]
    )
    reasons: List[str] = []
    score = 0

    exclusion = exclusion_reason(full_text, opp.url)
    if exclusion:
        return _assessment("reject", 0, [exclusion], opp, "A verificar", "A verificar")

    sector = contains_sector(full_text)
    if sector:
        score += 25
    else:
        reasons.append("Sin afinidad temática suficiente")

    strong = contains_strong_procurement(full_text)
    weak = contains_weak_procurement(full_text)
    if strong:
        score += 25
    elif weak:
        score += 10
        reasons.append("Señal contractual débil")
    else:
        reasons.append("No se confirmó una convocatoria/contratación")

    country = identify_country(opp)
    region = opp.region.strip() if opp.region else infer_region(country, full_text)
    if is_alc_or_global(country, region, full_text):
        score += 20
    elif country == "A verificar":
        score += 5
        reasons.append("País o alcance geográfico sin confirmar")
    else:
        reasons.append("Fuera del foco ALC/global: {}".format(country))

    deadline = parse_date(opp.deadline)
    if deadline:
        if deadline < today:
            return _assessment("reject", min(score, 30), reasons + ["Fecha límite vencida"], opp, country, region)
        score += 15
        days_left = (deadline - today).days
        if days_left < 5:
            reasons.append("Plazo de postulación muy corto")
    else:
        reasons.append("Fecha límite no verificada")

    if opp.source in TRUSTED_DIRECT_SOURCES and opp.source_mode == "direct":
        score += 10
    elif opp.source_mode == "exploratory":
        score += int(max(0.0, min(5.0, opp.source_score * 5.0)))
        reasons.append("Fuente exploratoria: requiere revisión humana")
    else:
        score += 5

    if opp.reference:
        score += 5
    else:
        reasons.append("Referencia oficial no identificada")

    # Reglas duras: no aceptar fuera de ALC/global ni sin señal sectorial/contractual.
    if not sector:
        decision = "reject" if not strong else "stage"
    elif not strong:
        decision = "stage" if weak else "reject"
    elif not is_alc_or_global(country, region, full_text):
        decision = "reject"
    elif opp.source_mode == "exploratory":
        decision = "stage"
    elif deadline is None:
        decision = "stage"
    elif score >= 75:
        decision = "accept"
    elif score >= 50:
        decision = "stage"
    else:
        decision = "reject"

    return _assessment(decision, score, reasons, opp, country, region)


def _assessment(decision: str, score: int, reasons: List[str], opp: Opportunity,
                country: str, region: str) -> Assessment:
    full_text = "{} {} {}".format(opp.title, opp.notice_type, opp.summary)
    opportunity_type = classify_type(full_text)
    affinity = classify_affinity(full_text, opportunity_type)
    priority = "Alta" if score >= 80 else "Media" if score >= 60 else "Baja"
    return Assessment(
        decision=decision,
        score=max(0, min(100, int(score))),
        reasons=reasons,
        canonical_id=canonical_id(opp),
        country=country,
        region=region,
        deadline_iso=date_iso(opp.deadline),
        opportunity_type=opportunity_type,
        affinity=affinity,
        priority=priority,
    )


def title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def likely_duplicate(opp: Opportunity, rows: Sequence[Dict[str, str]], threshold: float = 0.91) -> bool:
    cid = canonical_id(opp)
    curl = canonical_url(opp.url)
    ref = normalize_text(opp.reference)
    org = normalize_text(opp.organization)
    deadline = date_iso(opp.deadline)
    for row in rows:
        if row.get("ID canónico", "") == cid:
            return True
        row_url = canonical_url(row.get("Enlace", ""))
        if curl and row_url and curl == row_url:
            return True
        row_ref = normalize_text(row.get("Referencia", ""))
        row_org = normalize_text(row.get("Organización", ""))
        if ref and row_ref and ref == row_ref and (not org or not row_org or org == row_org):
            return True
        row_deadline = date_iso(row.get("Fecha límite", ""))
        if org and row_org and org == row_org and (deadline == row_deadline or "A verificar" in {deadline, row_deadline}):
            if title_similarity(opp.title, row.get("Título", "")) >= threshold:
                return True
    return False


def load_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def write_csv_rows(path: Path, rows: Sequence[Dict[str, str]], columns: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})
    temp.replace(path)


def append_unique(path: Path, new_rows: Sequence[Dict[str, str]], columns: Sequence[str],
                  key_columns: Sequence[str]) -> int:
    existing = load_csv_rows(path)
    keys: Set[Tuple[str, ...]] = set()
    for row in existing:
        keys.add(tuple(row.get(k, "") for k in key_columns))
    added = 0
    for row in new_rows:
        key = tuple(row.get(k, "") for k in key_columns)
        if key in keys:
            continue
        keys.add(key)
        existing.append(dict(row))
        added += 1
    write_csv_rows(path, existing, columns)
    return added


def to_main_row(opp: Opportunity, assessment: Assessment) -> Dict[str, str]:
    observations = "Fuente: {}. Puntaje automático: {}/100.".format(opp.source, assessment.score)
    if assessment.reasons:
        observations += " Alertas: {}.".format("; ".join(assessment.reasons))
    return {
        "Título": opp.title.strip(),
        "Organización": opp.organization.strip() or opp.source,
        "Tipo": assessment.opportunity_type,
        "Región": assessment.region,
        "País": assessment.country,
        "Fecha límite": assessment.deadline_iso,
        "Enlace": opp.url.strip(),
        "Afinidad": assessment.affinity,
        "Prioridad": assessment.priority,
        "Estado": "Identificada",
        "Monto estimado (USD)": "",
        "Consultor": "—",
        "Observaciones": observations,
        "Socio vinculado": "",
        "Votos descarte": "",
    }


def to_staging_row(opp: Opportunity, assessment: Assessment) -> Dict[str, str]:
    return {
        "ID canónico": assessment.canonical_id,
        "Título": opp.title.strip(),
        "Organización": opp.organization.strip() or opp.source,
        "Tipo": assessment.opportunity_type,
        "Región": assessment.region,
        "País": assessment.country,
        "Fecha límite": assessment.deadline_iso,
        "Enlace": opp.url.strip(),
        "Afinidad": assessment.affinity,
        "Prioridad": assessment.priority,
        "Fuente": opp.source,
        "Referencia": opp.reference,
        "Fecha publicación": date_iso(opp.publication_date),
        "Resumen": re.sub(r"\s+", " ", opp.summary).strip()[:1200],
        "Puntaje": str(assessment.score),
        "Motivos": "; ".join(assessment.reasons),
        "Estado revisión": "Pendiente",
        "Detectada": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def load_criteria(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
