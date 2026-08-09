"""Perfil de búsqueda y puntuación estratégica de Grupo CEO.

Derivado de la oferta institucional vigente: políticas y estrategia institucional;
mercados, comercio e inversiones; diseño y gestión de proyectos; con bioeconomía,
CTI, sostenibilidad y desarrollo rural como capacidades transversales.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Sequence, Tuple

CEO_PROFILE_VERSION = "2026.08"

PILLARS: Dict[str, Sequence[str]] = {
    "Políticas y estrategia institucional": (
        "agricultural policy", "agricultural policies", "agrifood policy", "food policy", "politica agricola", "politicas agricolas",
        "politica agropecuaria", "politica agroindustrial", "politicas publicas",
        "institutional strengthening", "strengthen institutions", "fortalecimiento institucional", "governance",
        "gobernanza", "institutional framework", "institutional strategy", "marco institucional", "public-private",
        "public private", "consensus building", "construccion de consensos", "foresight",
        "prospectiva", "strategic planning", "planificacion estrategica", "roadmap", "hoja de ruta", "food systems", "sistemas alimentarios", "food security",
        "seguridad alimentaria", "rural development", "desarrollo rural", "territorial development",
        "desarrollo territorial", "policy evaluation", "evaluacion de politicas",
    ),
    "Mercados, comercio e inversiones": (
        "agricultural trade", "agrifood trade", "comercio agricola", "comercio agroalimentario",
        "international trade", "comercio internacional", "trade negotiations", "negociaciones comerciales",
        "market intelligence", "inteligencia de mercados", "market access", "acceso a mercados",
        "value chain", "cadena de valor", "regulatory analysis", "analisis regulatorio",
        "geopolitics", "geopolitica", "geoeconomics", "geoeconomia", "tariff", "arancel",
        "wto", "omc", "mercosur", "econometric", "econometr", "modelling", "modeling",
        "investment structuring", "estructuracion de inversiones", "feasibility study",
        "estudio de factibilidad", "business case", "agribusiness", "agroindustria",
        "competitiveness", "competitividad", "price transmission", "transmision de precios",
    ),
    "Diseño y gestión de proyectos": (
        "project formulation", "formulacion de proyectos", "project design", "diseño de proyectos",
        "project preparation", "preparacion de proyectos", "project management", "gestion de proyectos",
        "technical assistance", "asistencia tecnica", "implementation support", "apoyo a la implementacion",
        "monitoring and evaluation", "monitoreo y evaluacion", "impact evaluation", "evaluacion de impacto",
        "baseline", "linea de base", "financing strategy", "estrategia de financiamiento",
        "resource mobilization", "movilizacion de recursos", "partnership development",
        "desarrollo de alianzas", "capacity building", "fortalecimiento de capacidades",
        "scaling", "escalamiento", "knowledge transfer", "transferencia de capacidades",
        "results framework", "marco de resultados",
    ),
    "Bioeconomía, CTI e innovación": (
        "bioeconomy", "bioeconomia", "biotechnology", "biotecnologia", "innovation system",
        "sistema de innovacion", "science technology and innovation", "ciencia tecnologia e innovacion",
        "technology transfer", "transferencia tecnologica", "digital agriculture", "agricultura digital",
        "artificial intelligence", "inteligencia artificial", "predictive analysis", "analisis predictivo",
        "climate-smart", "climate smart", "climaticamente inteligente", "sustainability", "sostenibilidad",
        "circular economy", "economia circular", "green finance", "finanzas verdes", "carbon market",
        "mercado de carbono", "biodiversity finance", "financiamiento de biodiversidad",
        "resilient food systems", "sistemas alimentarios resilientes",
    ),
}

DELIVERY_TERMS: Sequence[str] = (
    "consulting firm", "consultancy firm", "consultancy", "consulting services", "firma consultora", "consultoria",
    "advisory services", "servicios de asesoria", "request for proposal", "terms of reference", "technical proposal", "propuesta tecnica",
    "diagnostic", "diagnostico", "strategy", "estrategia", "roadmap", "hoja de ruta",
    "policy design", "diseño de politica", "analytical study", "estudio analitico",
    "evaluation", "evaluacion", "assessment", "estudio", "analysis", "analisis",
)

AGRIFOOD_TERMS: Sequence[str] = (
    "agricultur", "agrifood", "agroaliment", "agropecu", "agroindustr", "food system",
    "sistema alimentario", "rural", "farmer", "productor", "livestock", "ganader",
    "crop", "cadena de valor", "value chain", "bioeconom", "food security",
    "seguridad alimentaria", "fisher", "pesca", "forestry", "forestal",
)

CLIENT_CONTEXT_TERMS: Sequence[str] = (
    "government", "gobierno", "ministry", "ministerio", "public institution", "institucion publica",
    "development bank", "banco de desarrollo", "international organization", "organismo internacional",
    "development fund", "fondo de desarrollo", "private sector", "sector privado", "association",
    "asociacion", "foundation", "fundacion", "civil society", "sociedad civil",
)

REGIONAL_TERMS: Sequence[str] = (
    "latin america", "america latina", "caribbean", "caribe", "lac", "regional",
    "argentina", "mercosur", "south america", "central america", "centroamerica",
)

OUT_OF_SCOPE_TERMS: Sequence[str] = (
    "health system", "public health", "hospital", "epidemiolog", "medical", "clinical",
    "refugee", "humanitarian protection", "shelter", "camp management", "peacekeeping",
    "school curriculum", "primary education", "secondary education", "teacher training",
    "software developer", "cybersecurity", "telecommunications", "network engineer",
    "road construction", "building design", "architectural services", "civil engineering works",
    "translation services", "interpretation services", "graphic design", "event management",
    "human resources", "payroll", "recruitment services", "audit services", "accounting services",
)

CEO_TAVILY_SEARCH_GROUPS = [
    {
        "name": "Políticas y estrategia agroalimentaria",
        "domains": ["iadb.org", "caf.com", "bcie.org", "iica.int", "fontagro.org", "worldbank.org"],
        "queries": [
            "request for proposals consulting firm agricultural policy institutional strengthening bioeconomy Latin America Caribbean",
            "expression of interest agrifood strategy food security rural development governance Latin America consultancy",
        ],
    },
    {
        "name": "Mercados, comercio e inversiones",
        "domains": ["iadb.org", "caf.com", "worldbank.org", "ifpri.org", "cgiar.org", "iica.int"],
        "queries": [
            "consulting services agricultural trade market intelligence regulatory analysis investment value chains Latin America",
            "terms of reference agribusiness econometric modelling trade negotiations market access feasibility study",
        ],
    },
    {
        "name": "Diseño y gestión de proyectos",
        "domains": ["ungm.org", "ifad.org", "wfp.org", "undp.org", "fao.org", "iica.int"],
        "queries": [
            "consulting firm project formulation monitoring evaluation agrifood bioeconomy Latin America Caribbean",
            "technical assistance project design financing implementation capacity building food systems consultancy",
        ],
    },
    {
        "name": "Bioeconomía, CTI e innovación",
        "domains": ["cgiar.org", "ifpri.org", "alliancebioversityciat.org", "cimmyt.org", "catie.ac.cr", "fontagro.org"],
        "queries": [
            "consultancy bioeconomy science technology innovation agriculture Latin America terms of reference",
            "request for proposal digital agriculture technology transfer climate smart food systems Latin America",
        ],
    },
    {
        "name": "Cooperación bilateral y Unión Europea",
        "domains": ["giz.de", "aecid.es", "expertisefrance.fr", "afd.fr", "ted.europa.eu"],
        "queries": [
            "consulting services agrifood policy rural development trade investment Latin America tender",
            "technical assistance bioeconomy innovation value chains project preparation Latin America Caribbean",
        ],
    },
]


def _strip_accents(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", value or "")
        if not unicodedata.combining(char)
    )


def normalize(value: str) -> str:
    value = _strip_accents(value).lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _matches(text: str, terms: Sequence[str]) -> List[str]:
    norm = normalize(text)
    found: List[str] = []
    for term in terms:
        term_norm = normalize(term)
        if term_norm and term_norm in norm:
            found.append(term)
    return found


def dominant_ceo_pillar(text: str) -> str:
    scores = {name: len(_matches(text, terms)) for name, terms in PILLARS.items()}
    if not scores or max(scores.values()) == 0:
        return "Alineación general con Grupo CEO"
    return max(scores, key=scores.get)


def evaluate_ceo_fit(text: str) -> Tuple[int, List[str], Dict[str, List[str]]]:
    """Devuelve puntaje 0-25, alertas y coincidencias por pilar."""
    pillar_hits = {name: _matches(text, terms) for name, terms in PILLARS.items()}
    active = [name for name, hits in pillar_hits.items() if hits]
    delivery_hits = _matches(text, DELIVERY_TERMS)
    agrifood_hits = _matches(text, AGRIFOOD_TERMS)
    client_hits = _matches(text, CLIENT_CONTEXT_TERMS)
    regional_hits = _matches(text, REGIONAL_TERMS)
    negative_hits = _matches(text, OUT_OF_SCOPE_TERMS)

    score = 0
    for hits in pillar_hits.values():
        if hits:
            score += min(6, 2 + len(set(hits)))
    score = min(score, 17)
    score += min(4, len(set(delivery_hits)))
    if agrifood_hits:
        score += 2
    if client_hits:
        score += 1
    if regional_hits:
        score += 1

    # Penaliza señales claramente ajenas cuando dominan el aviso.
    if negative_hits:
        penalty = 3 if agrifood_hits and active else min(10, 3 * len(set(negative_hits)))
        score -= penalty

    score = max(0, min(25, score))
    reasons: List[str] = []
    if not active:
        reasons.append("Sin coincidencia clara con las líneas de servicio de Grupo CEO")
    elif len(active) == 1:
        reasons.append("Alineación concentrada en: {}".format(active[0]))
    if not delivery_hits:
        reasons.append("No se identifica con claridad un producto de consultoría")
    if negative_hits:
        reasons.append("Señales potencialmente fuera de alcance: {}".format(", ".join(sorted(set(negative_hits))[:3])))
    if score < 8:
        reasons.append("Alineación estratégica baja con la oferta de Grupo CEO")

    return score, reasons, pillar_hits
