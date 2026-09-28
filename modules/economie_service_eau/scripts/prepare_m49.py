#!/usr/bin/env python3
"""Agrège une balance M49 JSON en tables réutilisables pour le livrable.

Aucune dépendance externe : Python >= 3.10 suffit.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def read_mapping(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def amount(row: dict, direction: str) -> float:
    key = "obnetdeb" if direction == "debit" else "obnetcre"
    return float(row.get(key) or 0.0)


def service_for_budget(lbudg: str, water_budget: str, sanitation_budget: str) -> str | None:
    if lbudg == water_budget:
        return "Eau"
    if lbudg == sanitation_budget:
        return "Assainissement"
    return None


def write_csv(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(headers)
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True, type=Path)
    ap.add_argument("--year", required=True, type=int)
    ap.add_argument("--water-budget", required=True)
    ap.add_argument("--sanitation-budget", required=True)
    ap.add_argument("--mapping", type=Path, default=Path(__file__).resolve().parents[1] / "config" / "m49_mapping.csv")
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    data = json.loads(args.json.read_text(encoding="utf-8-sig"))
    mapping = read_mapping(args.mapping)

    sums: dict[tuple[str, str, str, str], float] = defaultdict(float)
    raw_rows = []

    for row in data:
        if str(row.get("exer")) != str(args.year):
            continue
        service = service_for_budget(str(row.get("lbudg") or ""), args.water_budget, args.sanitation_budget)
        if not service:
            continue
        compte = str(row.get("compte") or "")
        raw_rows.append(row)
        for m in mapping:
            if compte.startswith(m["prefix"]):
                value = amount(row, m["direction"])
                sums[(m["section"], service, m["poste"], m["role"])] += value

    for section in ("fonctionnement", "investissement"):
        rows = []
        for (sec, service, poste, role), value in sums.items():
            if sec == section:
                rows.append([service, poste, round(value, 2)])
        rows.sort(key=lambda x: (x[0], x[1]))
        write_csv(args.out_dir / f"m49_{section}.csv", ["service", "poste", "montant_eur"], rows)

    resource_rows = []
    for (sec, service, poste, role), value in sums.items():
        if sec == "ressources":
            resource_rows.append([service, poste, round(value, 2), role])
    resource_rows.sort(key=lambda x: (x[0], x[1]))
    write_csv(args.out_dir / "m49_ressources.csv", ["service", "poste", "montant_eur", "role"], resource_rows)

    indicator_rows = []
    for service in ("Eau", "Assainissement"):
        f_total = sum(v for (sec, srv, _p, _r), v in sums.items() if sec == "fonctionnement" and srv == service)
        i_total = sum(v for (sec, srv, _p, _r), v in sums.items() if sec == "investissement" and srv == service)
        debt = sum(v for (sec, srv, _p, role), v in sums.items() if sec == "indicateurs" and srv == service and role == "remboursement_capital")
        indicator_rows.extend([
            [service, "Fonctionnement – classe 6", round(f_total, 2)],
            [service, "Investissement – débits classe 2", round(i_total, 2)],
            [service, "Remboursement du capital des emprunts – débits classe 16", round(debt, 2)],
        ])
    write_csv(args.out_dir / "m49_indicateurs.csv", ["service", "indicateur", "montant_eur"], indicator_rows)

    # Audit minimal des lignes retenues
    audit_headers = ["exer", "lbudg", "compte", "obnetdeb", "obnetcre", "sd", "sc"]
    audit = [[r.get(h, "") for h in audit_headers] for r in raw_rows]
    write_csv(args.out_dir / "m49_audit_exercice.csv", audit_headers, audit)

    print(f"OK - {len(raw_rows)} lignes M49 retenues pour {args.year}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
