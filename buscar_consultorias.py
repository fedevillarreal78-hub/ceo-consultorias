#!/usr/bin/env python3
"""Buscador de oportunidades de Grupo CEO, versión 2.

Arquitectura:
- Fuentes directas confiables -> validación estricta -> pipeline o staging.
- Fuentes exploratorias (Tavily) -> siempre staging.
- Deduplicación por referencia, URL canónica y similitud.
- Métricas por fuente y motivos de rechazo.

Compatible con Python 3.9.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from opportunity_engine import (
    MAIN_COLUMNS, STAGING_COLUMNS, Opportunity, append_unique, assess,
    load_csv_rows, likely_duplicate, to_main_row, to_staging_row, write_csv_rows,
)
from ceo_profile import CEO_TAVILY_SEARCH_GROUPS

BASE_DIR = Path(__file__).parent
MAIN_PATH = BASE_DIR / "oportunidades_consultoria.csv"
STAGING_PATH = BASE_DIR / "candidatos_revision.csv"
STATS_PATH = BASE_DIR / "ultima_busqueda_stats.json"
REPORT_PATH = BASE_DIR / "nuevas_esta_semana.txt"
AUDIT_PATH = BASE_DIR / "auditoria_oportunidades.csv"

LOOKBACK_DAYS = max(7, int(os.environ.get("SEARCH_LOOKBACK_DAYS", "21")))
REQUEST_TIMEOUT = 30

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; GrupoCEO-OpportunityMonitor/2.0; +https://grupo-ceo.com/)",
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-419,es;q=0.9,en;q=0.8",
}

ALC_WB_COUNTRIES = [
    "Argentina", "Belize", "Bolivia", "Brazil", "Chile", "Colombia", "Costa Rica",
    "Dominica", "Dominican Republic", "Ecuador", "El Salvador", "Grenada", "Guatemala",
    "Guyana", "Haiti", "Honduras", "Jamaica", "Mexico", "Nicaragua", "Panama",
    "Paraguay", "Peru", "Saint Lucia", "Suriname", "Trinidad and Tobago", "Uruguay",
    "Venezuela", "Latin America and Caribbean",
]

TAVILY_SEARCH_GROUPS = [
    {
        "name": "Bancos y organismos ALC",
        "domains": ["iadb.org", "caf.com", "bcie.org", "iica.int", "fontagro.org"],
        "queries": [
            "consultancy OR consultoría agriculture rural food systems request for proposal Latin America deadline",
            "expression of interest consultant agricultural policy trade bioeconomy Latin America Caribbean",
        ],
    },
    {
        "name": "Investigación y desarrollo rural",
        "domains": ["cgiar.org", "ifpri.org", "alliancebioversityciat.org", "cimmyt.org", "catie.ac.cr"],
        "queries": [
            "consultancy terms of reference agriculture food systems Latin America deadline",
            "request for proposal evaluation policy rural development consultant",
        ],
    },
    {
        "name": "Cooperación bilateral y UE",
        "domains": ["giz.de", "aecid.es", "expertisefrance.fr", "afd.fr", "ted.europa.eu"],
        "queries": [
            "consulting services agriculture rural development Latin America tender deadline",
            "terms of reference food systems bioeconomy Latin America Caribbean consultant",
        ],
    },
    {
        "name": "Sistema ONU y agregadores",
        "domains": ["ungm.org", "ifad.org", "wfp.org", "ilo.org", "devex.com"],
        "queries": [
            "individual consultant agriculture food rural Latin America Caribbean deadline",
            "request for proposal agrifood policy evaluation Latin America Caribbean",
        ],
    },
]


# Perfil institucional vigente de Grupo CEO.
TAVILY_SEARCH_GROUPS = CEO_TAVILY_SEARCH_GROUPS


def log(message: str, marker: str = "•") -> None:
    print("[{}] {} {}".format(datetime.now().strftime("%H:%M:%S"), marker, message), flush=True)


def get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def safe_get(session: requests.Session, url: str, **kwargs) -> requests.Response:
    kwargs.setdefault("timeout", REQUEST_TIMEOUT)
    response = session.get(url, **kwargs)
    response.raise_for_status()
    return response


def extract_reference(text: str) -> str:
    patterns = [
        r"\b(?:UNDP|UNCDF|UNOPS|FAO|WFP|ILO|IADB|IDB|WB|RFP|EOI|IC)[-_ /][A-Z0-9][A-Z0-9._/-]{3,}\b",
        r"\bOP\d{6,}\b", r"\bP\d{6}\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text or "", flags=re.I)
        if match:
            return match.group(0).strip(" ,.;")
    return ""


def scrape_undp(session: requests.Session) -> List[Opportunity]:
    url = "https://procurement-notices.undp.org"
    response = safe_get(session, url)
    soup = BeautifulSoup(response.text, "lxml")
    rows = soup.select("a.vacanciesTableLink[data-region]")
    results: List[Opportunity] = []
    for row in rows:
        data: Dict[str, str] = {}
        for cell in row.select(".vacanciesTable__cell"):
            label = cell.select_one(".vacanciesTable__cell__label")
            value = cell.select_one("span")
            if label and value:
                data[label.get_text(" ", strip=True).lower()] = value.get_text(" ", strip=True)
        title = data.get("title", "").strip()
        if not title:
            continue
        country_raw = data.get("undp office/country", "").strip()
        reference = data.get("ref no", "").strip() or extract_reference(title)
        process = data.get("procurement process", "").strip()
        href = row.get("href", "")
        link = urljoin(url + "/", href)
        country_code = ""
        match = re.search(r"(?:UNDP|UNCDF)-([A-Z]{3})/", country_raw.upper())
        if match:
            country_code = match.group(1)
        country_name = country_raw.split("/", 1)[-1].strip() if "/" in country_raw else country_raw
        raw = "{} {} {}".format(title, process, country_raw)
        results.append(Opportunity(
            title=title,
            organization="UNDP – {}".format(country_raw) if country_raw else "UNDP",
            url=link,
            source="UNDP",
            source_mode="direct",
            country=country_name,
            country_code=country_code,
            deadline=data.get("deadline", ""),
            reference=reference,
            notice_type=process,
            summary=process,
            raw_text=raw,
        ))
    return results


def scrape_reliefweb(session: requests.Session) -> List[Opportunity]:
    base = "https://reliefweb.int"
    urls = [
        base + "/jobs?advanced-search=%28TY264%29&list=Consultancy+Jobs",
        base + "/jobs?advanced-search=%28TY264%29_%28S1268%29&list=Consultancy+Jobs",
    ]
    seen = set()
    results: List[Opportunity] = []
    for url in urls:
        soup = BeautifulSoup(safe_get(session, url).text, "lxml")
        for article in soup.select("article.rw-river-article--job"):
            anchor = article.select_one("h3.rw-river-article__title a")
            if not anchor:
                continue
            title = anchor.get_text(" ", strip=True)
            link = urljoin(base, anchor.get("href", ""))
            if link in seen:
                continue
            seen.add(link)
            org_el = article.select_one("dd.rw-entity-meta__tag-value--source a, dd.rw-entity-meta__tag-value--source span")
            org = org_el.get_text(" ", strip=True) if org_el else "ReliefWeb"
            country_el = article.select_one("dd.rw-entity-meta__tag-value--country a, dd.rw-entity-meta__tag-value--country span")
            country = country_el.get_text(" ", strip=True) if country_el else ""
            times = article.select("time")
            deadline = ""
            if len(times) >= 2:
                deadline = times[1].get("datetime", "")[:10] or times[1].get_text(" ", strip=True)
            results.append(Opportunity(
                title=title, organization=org, url=link, source="ReliefWeb",
                source_mode="direct", country=country, deadline=deadline,
                reference=extract_reference(title), notice_type="Consultancy",
                summary=article.get_text(" ", strip=True)[:1200], raw_text=article.get_text(" ", strip=True),
            ))
    return results


def scrape_fao(session: requests.Session) -> List[Opportunity]:
    urls = [
        "https://www.fao.org/americas/jobs/en",
        "https://www.fao.org/americas/jobs/es",
        "https://www.fao.org/evaluation/about-us/vacancies/en",
    ]
    results: List[Opportunity] = []
    seen = set()
    for url in urls:
        try:
            soup = BeautifulSoup(safe_get(session, url).text, "lxml")
        except Exception as exc:
            log("FAO {}: {}".format(url, exc), "!")
            continue
        for anchor in soup.select("h2 a, h3 a, .views-field-title a, tr.listrow a"):
            title = anchor.get_text(" ", strip=True)
            if len(title) < 12:
                continue
            link = urljoin("https://www.fao.org", anchor.get("href", ""))
            if link in seen:
                continue
            seen.add(link)
            context = anchor.parent.parent.get_text(" ", strip=True) if anchor.parent and anchor.parent.parent else title
            results.append(Opportunity(
                title=title, organization="FAO", url=link, source="FAO", source_mode="direct",
                country="Regional/Global", deadline=_extract_date(context), reference=extract_reference(context),
                notice_type="Consultancy/Vacancy", summary=context[:1200], raw_text=context,
            ))
    return results


def scrape_world_bank(session: requests.Session) -> List[Opportunity]:
    """Consulta la API oficial DS00979 por fecha de publicación reciente."""
    base = "https://datacatalogapi.worldbank.org/dexapps/fone/api/apiservice"
    results: List[Opportunity] = []
    seen = set()
    for offset in range(LOOKBACK_DAYS + 1):
        target = date.today() - timedelta(days=offset)
        params = {
            "datasetId": "DS00979", "resourceId": "RS00909", "type": "json",
            "top": 1000, "publication_date": target.strftime("%d-%b-%Y"),
        }
        try:
            payload = safe_get(session, base, params=params).json()
        except Exception as exc:
            log("World Bank {}: {}".format(target.isoformat(), exc), "!")
            continue
        for item in payload.get("data", []) if isinstance(payload, dict) else []:
            url = str(item.get("url", "") or "").strip()
            item_id = str(item.get("id", "") or "").strip()
            unique = item_id or url
            if not unique or unique in seen:
                continue
            seen.add(unique)
            country = str(item.get("country_name", "") or "").strip()
            category = str(item.get("procurement_category", "") or "")
            method = str(item.get("procurement_method", "") or "")
            notice = str(item.get("notice_type", "") or "")
            # Reducir volumen antes de la evaluación completa.
            prefilter = "{} {}".format(category, method).lower()
            if "consult" not in prefilter and "consult" not in notice.lower():
                continue
            if country and country not in ALC_WB_COUNTRIES:
                continue
            title = str(item.get("bid_description", "") or "").strip()
            if not title:
                continue
            reference = item_id or str(item.get("project_id", "") or "")
            results.append(Opportunity(
                title=title, organization="Banco Mundial", url=url,
                source="World Bank", source_mode="direct", country=country,
                region=str(item.get("region", "") or ""),
                deadline=str(item.get("deadline_date", "") or ""),
                publication_date=str(item.get("publication_date", "") or ""),
                reference=reference, notice_type="{} {} {}".format(notice, category, method),
                summary="Proyecto {}. Sector {}.".format(item.get("project_id", ""), item.get("sector", "")),
                raw_text=json.dumps(item, ensure_ascii=False),
            ))
    return results


def scrape_tavily() -> List[Opportunity]:
    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not api_key:
        return []
    try:
        from tavily import TavilyClient
    except ImportError:
        log("tavily-python no instalado", "!")
        return []
    client = TavilyClient(api_key=api_key)
    results: List[Opportunity] = []
    seen = set()
    start_date = (date.today() - timedelta(days=45)).isoformat()
    for group in TAVILY_SEARCH_GROUPS:
        for query in group["queries"]:
            try:
                payload = client.search(
                    query=query,
                    search_depth="basic",
                    max_results=8,
                    include_domains=group["domains"],
                    start_date=start_date,
                    include_raw_content=False,
                )
            except Exception as exc:
                log("Tavily {}: {}".format(group["name"], exc), "!")
                continue
            for item in payload.get("results", []):
                score = float(item.get("score", 0.0) or 0.0)
                if score < 0.65:
                    continue
                url = str(item.get("url", "") or "").strip()
                if not url or url in seen:
                    continue
                seen.add(url)
                title = str(item.get("title", "") or "").strip()
                content = str(item.get("content", "") or "")
                results.append(Opportunity(
                    title=title, organization=_organization_from_url(url), url=url,
                    source="Tavily – {}".format(group["name"]), source_mode="exploratory",
                    country="", deadline=_extract_date(content), reference=extract_reference(title + " " + content),
                    notice_type="Exploratory web result", summary=content[:1200], raw_text=content,
                    source_score=score,
                ))
    return results


def _organization_from_url(url: str) -> str:
    mapping = {
        "iadb.org": "BID", "caf.com": "CAF", "bcie.org": "BCIE", "iica.int": "IICA",
        "fontagro.org": "FONTAGRO", "cgiar.org": "CGIAR", "ifpri.org": "IFPRI",
        "alliancebioversityciat.org": "Alliance Bioversity-CIAT", "cimmyt.org": "CIMMYT",
        "catie.ac.cr": "CATIE", "giz.de": "GIZ", "aecid.es": "AECID",
        "expertisefrance.fr": "Expertise France", "afd.fr": "AFD", "ted.europa.eu": "Unión Europea/TED",
        "ungm.org": "UNGM", "ifad.org": "FIDA/IFAD", "wfp.org": "PMA/WFP",
        "ilo.org": "OIT/ILO", "devex.com": "Devex",
    }
    low = url.lower()
    for domain, name in mapping.items():
        if domain in low:
            return name
    return "A verificar"


def _extract_date(text: str) -> str:
    patterns = [
        r"\b(20\d{2}-\d{2}-\d{2})\b",
        r"\b(\d{1,2}[- ](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[- ,]20\d{2})\b",
        r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}, 20\d{2})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text or "", flags=re.I)
        if match:
            return match.group(1)
    return "A verificar"


def source_registry() -> List[Tuple[str, Callable[[requests.Session], List[Opportunity]]]]:
    return [
        ("UNDP", scrape_undp),
        ("World Bank", scrape_world_bank),
        ("ReliefWeb", scrape_reliefweb),
        ("FAO", scrape_fao),
    ]


def process_candidates(candidates: List[Opportunity]) -> Dict[str, object]:
    main_existing = load_csv_rows(MAIN_PATH)
    staging_existing = load_csv_rows(STAGING_PATH)
    accepted_rows: List[Dict[str, str]] = []
    staged_rows: List[Dict[str, str]] = []
    rejected = Counter()
    duplicates = 0
    assessments = []

    combined = list(main_existing) + list(staging_existing)
    for opp in candidates:
        if likely_duplicate(opp, combined + accepted_rows + staged_rows):
            duplicates += 1
            continue
        assessment = assess(opp)
        assessments.append((opp, assessment))
        if assessment.decision == "accept":
            row = to_main_row(opp, assessment)
            accepted_rows.append(row)
            combined.append(row)
        elif assessment.decision == "stage":
            row = to_staging_row(opp, assessment)
            staged_rows.append(row)
            combined.append(row)
        else:
            if assessment.reasons:
                for reason in assessment.reasons:
                    rejected[reason] += 1
            else:
                rejected["Rechazo sin motivo"] += 1

    accepted_added = append_unique(MAIN_PATH, accepted_rows, MAIN_COLUMNS, ["Enlace", "Título"])
    staged_added = append_unique(STAGING_PATH, staged_rows, STAGING_COLUMNS, ["ID canónico"])
    return {
        "accepted_rows": accepted_rows,
        "staged_rows": staged_rows,
        "accepted_added": accepted_added,
        "staged_added": staged_added,
        "rejected": dict(rejected),
        "duplicates": duplicates,
        "assessments": assessments,
    }


def write_report(stats: Dict[str, object], accepted: List[Dict[str, str]], staged: List[Dict[str, str]]) -> None:
    lines = [
        "NUEVAS OPORTUNIDADES – GRUPO CEO",
        "Fecha: {}".format(stats["fecha"]),
        "",
        "Incorporadas al pipeline: {}".format(stats["nuevas_pipeline"]),
        "Enviadas a revisión: {}".format(stats["nuevas_revision"]),
        "Duplicadas omitidas: {}".format(stats["duplicadas"]),
        "Rechazadas: {}".format(stats["rechazadas"]),
        "",
    ]
    if accepted:
        lines.append("PIPELINE")
        for row in accepted:
            lines.append("- {} | {} | {} | {}".format(row["Título"], row["Organización"], row["País"], row["Fecha límite"]))
        lines.append("")
    if staged:
        lines.append("REVISIÓN HUMANA")
        for row in staged:
            lines.append("- [{}] {} | {} | {}".format(row["Puntaje"], row["Título"], row["Organización"], row["Motivos"]))
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    log("Inicio del buscador v2")
    session = get_session()
    all_candidates: List[Opportunity] = []
    source_stats: Dict[str, Dict[str, object]] = {}
    source_errors: Dict[str, str] = {}

    for name, scraper in source_registry():
        started = time.time()
        try:
            found = scraper(session)
            all_candidates.extend(found)
            source_stats[name] = {"brutas": len(found), "segundos": round(time.time() - started, 2)}
            log("{}: {} registros brutos".format(name, len(found)), "✓")
        except Exception as exc:
            source_stats[name] = {"brutas": 0, "segundos": round(time.time() - started, 2)}
            source_errors[name] = str(exc)
            log("{}: {}".format(name, exc), "!")

    tavily_started = time.time()
    tavily_results = scrape_tavily()
    all_candidates.extend(tavily_results)
    source_stats["Tavily"] = {"brutas": len(tavily_results), "segundos": round(time.time() - tavily_started, 2)}
    log("Tavily: {} registros exploratorios".format(len(tavily_results)), "✓" if tavily_results else "•")

    processed = process_candidates(all_candidates)
    rejected_count = sum(processed["rejected"].values())
    stats = {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "version_motor": "2.0",
        "tavily_activo": bool(os.environ.get("TAVILY_API_KEY", "").strip()),
        "ungm_token_configurado": bool(os.environ.get("UNGM_ACCESS_TOKEN", "").strip()),
        "lookback_days": LOOKBACK_DAYS,
        "total_bruto": len(all_candidates),
        "nuevas_pipeline": processed["accepted_added"],
        "nuevas_revision": processed["staged_added"],
        "duplicadas": processed["duplicates"],
        "rechazadas": rejected_count,
        "total_csv": len(load_csv_rows(MAIN_PATH)),
        "total_revision_pendiente": sum(1 for r in load_csv_rows(STAGING_PATH) if r.get("Estado revisión", "Pendiente") == "Pendiente"),
        "por_fuente": source_stats,
        "errores_fuente": source_errors,
        "motivos_rechazo": processed["rejected"],
        "creditos_tavily_estimados": sum(len(g["queries"]) for g in TAVILY_SEARCH_GROUPS) if os.environ.get("TAVILY_API_KEY") else 0,
    }
    STATS_PATH.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(stats, processed["accepted_rows"], processed["staged_rows"])

    log("Pipeline: +{} | Revisión: +{} | Duplicadas: {} | Rechazadas: {}".format(
        stats["nuevas_pipeline"], stats["nuevas_revision"], stats["duplicadas"], stats["rechazadas"]
    ), "✓")


if __name__ == "__main__":
    main()
