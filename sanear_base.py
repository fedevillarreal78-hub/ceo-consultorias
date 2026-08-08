#!/usr/bin/env python3
"""Audita la base histórica sin eliminar datos por defecto.

Uso:
  python sanear_base.py
  python sanear_base.py --apply   # mueve inválidas/vencidas a archivo_oportunidades.csv
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from opportunity_engine import MAIN_COLUMNS, Opportunity, assess, load_csv_rows, write_csv_rows

BASE_DIR = Path(__file__).parent
MAIN_PATH = BASE_DIR / "oportunidades_consultoria.csv"
AUDIT_PATH = BASE_DIR / "auditoria_oportunidades.csv"
ARCHIVE_PATH = BASE_DIR / "archivo_oportunidades.csv"
SUMMARY_PATH = BASE_DIR / "auditoria_oportunidades_stats.json"

AUDIT_COLUMNS = MAIN_COLUMNS + ["Decisión auditoría", "Puntaje auditoría", "Motivos auditoría"]


def row_to_opp(row: Dict[str, str]) -> Opportunity:
    observations = row.get("Observaciones", "")
    organization = row.get("Organización", "")
    low_org = organization.lower()
    if "undp" in low_org or "pnud" in low_org:
        source = "UNDP"
    elif "world bank" in low_org or "banco mundial" in low_org:
        source = "World Bank"
    elif "fao" in low_org:
        source = "FAO"
    elif "reliefweb" in low_org:
        source = "ReliefWeb"
    else:
        source = "Base histórica"
    reference = ""
    match = __import__("re").search(r"(?:nego_id=|notice_id=|\bOP)([A-Za-z0-9_-]+)", row.get("Enlace", "") + " " + row.get("Título", ""), __import__("re").I)
    if match:
        reference = match.group(0)
    return Opportunity(
        title=row.get("Título", ""), organization=organization,
        url=row.get("Enlace", ""), source=source, source_mode="direct",
        country=row.get("País", ""), region=row.get("Región", ""),
        deadline=row.get("Fecha límite", ""), reference=reference, summary=observations,
        raw_text="{} {} {}".format(row.get("Tipo", ""), row.get("Afinidad", ""), observations),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Archiva registros rechazados por el motor")
    args = parser.parse_args()

    rows = load_csv_rows(MAIN_PATH)
    audited: List[Dict[str, str]] = []
    keep: List[Dict[str, str]] = []
    archive: List[Dict[str, str]] = load_csv_rows(ARCHIVE_PATH)
    counts = Counter()

    for row in rows:
        assessment = assess(row_to_opp(row))
        # Preservar oportunidades con trabajo humano avanzado, aunque el motor no reconozca texto histórico.
        protected = row.get("Estado", "") in {"En análisis", "Postulada", "Ganada"}
        decision = "conservar" if protected else assessment.decision
        counts[decision] += 1
        audit_row = dict(row)
        audit_row.update({
            "Decisión auditoría": decision,
            "Puntaje auditoría": str(assessment.score),
            "Motivos auditoría": "; ".join(assessment.reasons),
        })
        audited.append(audit_row)
        if args.apply and decision == "reject":
            archive.append(row)
        else:
            keep.append(row)

    write_csv_rows(AUDIT_PATH, audited, AUDIT_COLUMNS)
    if args.apply:
        write_csv_rows(MAIN_PATH, keep, MAIN_COLUMNS)
        write_csv_rows(ARCHIVE_PATH, archive, MAIN_COLUMNS)

    summary = {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "aplicada": args.apply,
        "total": len(rows),
        "decisiones": dict(counts),
        "conservadas": len(keep),
        "archivadas": len(archive) if args.apply else 0,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
