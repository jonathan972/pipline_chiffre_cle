#!/usr/bin/env python3
"""Certification métier d'un millésime consolidé.

La certification distingue les anomalies de PRODUCTION (bloquantes) des
révisions et erreurs historiques conservées en AUDIT, et des lacunes de source
connues qui conduisent à CERTIFIED_WITH_GAPS.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


REVISION_STATUSES = {
    "REVISED_SNAPSHOT",
    "REVISED_BY_LATER_SOURCE",
    "REVISED_LATER",
    "SOURCE_REVISION_MINOR",
}
GAP_STATUSES = {
    "INCOMPLETE_INVENTORY",
    "SOURCE_MANUELLE_REQUISE",
    "SOURCE_NOT_PRODUCED",
}
BAD_TOKENS = ("ERROR", "INVALID", "INCOHERENT", "SUSPECTED")


def read_semicolon(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def unique(items: list[dict[str, str]], keys: tuple[str, ...]) -> list[dict[str, str]]:
    result: dict[tuple[str, ...], dict[str, str]] = {}
    for item in items:
        result[tuple(item.get(key, "") for key in keys)] = item
    return list(result.values())


def certify(
    year: int,
    facts: list[dict[str, str]],
    quality_rows: list[dict[str, str]],
    absences: list[dict[str, str]],
) -> dict:
    blocking: list[dict[str, str]] = []
    audit_findings: list[dict[str, str]] = []
    gaps: list[dict[str, str]] = []

    for row in facts:
        role = row.get("record_role", "")
        status = row.get("quality_status", "")
        coverage = row.get("coverage_status", "")
        item = {
            "indicator_id": row.get("indicator_id", ""),
            "territoire": row.get("territoire", ""),
            "perimeter_id": row.get("perimeter_id", ""),
            "record_role": role,
            "coverage_status": coverage,
            "quality_status": status,
        }

        if status in GAP_STATUSES:
            gaps.append(item)
        if role == "AUDIT" and (status not in {"", "OK"}):
            audit_findings.append(item)
        if role == "PRODUCTION" and status not in REVISION_STATUSES:
            if coverage in {"MISSING", "NO_DATA"} or any(token in status for token in BAD_TOKENS):
                blocking.append(item)

    # Les absences déclarées sont comptées au grain année × territoire × domaine,
    # même si le master les résume ensuite en une ligne SOURCE_COVERAGE.
    declared_absences = [
        {
            "indicator_id": "SOURCE_COVERAGE",
            "territoire": row.get("territory", ""),
            "domain": row.get("domain", ""),
            "coverage_status": row.get("status", ""),
            "quality_status": "SOURCE_NOT_PRODUCED",
            "note": row.get("note", ""),
        }
        for row in absences
        if row.get("year") == str(year)
    ]
    if declared_absences:
        # Les lignes SOURCE_COVERAGE du master sont des résumés. Le registre
        # détaillé année × territoire × domaine est la source de comptage.
        gaps = [gap for gap in gaps if gap.get("quality_status") != "SOURCE_NOT_PRODUCED"]
    gaps.extend(declared_absences)

    gaps = unique(gaps, ("indicator_id", "territoire", "domain", "perimeter_id"))
    blocking = unique(blocking, ("indicator_id", "territoire", "perimeter_id"))
    audit_findings = unique(audit_findings, ("indicator_id", "territoire", "perimeter_id"))

    if blocking:
        status = "NOT_CERTIFIED"
    elif gaps:
        status = "CERTIFIED_WITH_GAPS"
    else:
        status = "CERTIFIED"

    return {
        "schema_version": "1.0",
        "year": year,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "blocking_anomalies_count": len(blocking),
        "gaps_count": len(gaps),
        "audit_findings_count": len(audit_findings),
        "quality_report_rows": len(quality_rows),
        "policy": {
            "CERTIFIED": "aucune anomalie bloquante et aucune lacune déclarée",
            "CERTIFIED_WITH_GAPS": "aucune anomalie bloquante, mais source manuelle ou donnée non produite",
            "NOT_CERTIFIED": "au moins une valeur PRODUCTION incohérente ou invalide non résolue",
        },
        "blocking_anomalies": blocking,
        "gaps": gaps,
        "audit_findings": audit_findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--facts", type=Path, required=True)
    parser.add_argument("--quality-report", type=Path, required=True)
    parser.add_argument("--known-absences", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    result = certify(
        args.year,
        read_semicolon(args.facts),
        read_semicolon(args.quality_report),
        read_semicolon(args.known_absences),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] != "NOT_CERTIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
