#!/usr/bin/env python3
"""Contrôles de cohérence avant génération du livrable."""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

ALLOWED_NATURES = {"delegataire", "collectivite", "redevance", "taxe", "tva"}


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def num(value: str | None) -> float:
    if value is None or value == "":
        return 0.0
    return float(str(value).replace(",", "."))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, type=Path)
    ap.add_argument("--facture", required=True, type=Path)
    ap.add_argument("--care-resume", required=True, type=Path)
    ap.add_argument("--care-couts", required=True, type=Path)
    ap.add_argument("--tolerance", type=float, default=2.0)
    args = ap.parse_args()

    project = json.loads(args.project.read_text(encoding="utf-8-sig"))
    facture = read_csv(args.facture)
    care_resume = read_csv(args.care_resume)
    care_couts = read_csv(args.care_couts)

    errors: list[str] = []
    warnings: list[str] = []

    facture_by_service = defaultdict(float)
    nature_totals = defaultdict(float)
    for row in facture:
        nature = row.get("nature", "").strip()
        if nature not in ALLOWED_NATURES:
            errors.append(f"Nature de facture inconnue: {nature!r}")
        value = num(row.get("montant_eur"))
        facture_by_service[row.get("service", "")] += value
        nature_totals[nature] += value

    if nature_totals["redevance"] and not any(r.get("nature") == "taxe" for r in facture):
        warnings.append("Aucune taxe hors TVA n'est renseignée ; vérifier que ce n'est pas un oubli.")

    care_costs = defaultdict(float)
    for row in care_couts:
        care_costs[row.get("service", "")] += num(row.get("montant_eur"))

    for row in care_resume:
        service = row.get("service", "")
        products = num(row.get("total_produits"))
        public = num(row.get("reversements_publics"))
        charges = num(row.get("charges_hors_reversements"))
        result = num(row.get("resultat_avant_impot"))
        eq = products - public - charges
        if abs(eq - result) > args.tolerance:
            errors.append(f"CARE {service}: produits - reversements - charges = {eq:.2f}, résultat déclaré = {result:.2f}")
        if abs(care_costs[service] - charges) > args.tolerance:
            errors.append(f"CARE {service}: somme des postes = {care_costs[service]:.2f}, charges hors reversements = {charges:.2f}")

    if project.get("annee_facture") != project.get("annee_comptable"):
        warnings.append(
            f"Millésimes différents: facture {project.get('annee_facture')} / CARE-M49 {project.get('annee_comptable')}. "
            "Le livrable doit afficher l'avertissement méthodologique."
        )

    print("=== Totaux facture ===")
    for service, value in sorted(facture_by_service.items()):
        print(f"{service}: {value:.2f} €")
    print(f"TOTAL: {sum(facture_by_service.values()):.2f} €")

    for w in warnings:
        print(f"WARNING: {w}")
    for e in errors:
        print(f"ERROR: {e}")

    if errors:
        return 2
    print("OK - contrôles d'entrée réussis")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
