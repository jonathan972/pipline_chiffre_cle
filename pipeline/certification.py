"""Certification d'un millésime contre la matrice des attentes.

Une année n'est plus jugée sur les lignes présentes, mais sur ce qui devrait
exister (referentiel/attentes.csv). Chaque cellule attendue indicateur × périmètre
reçoit un statut explicite :

- PRODUCTION           : une valeur publiable existe ;
- LACUNE_DECLAREE      : absence documentée (lacunes_declarees.csv, known_absences.csv,
                         ou statut de source du type INCOMPLETE_INVENTORY) ;
- NON_APPLICABLE       : déclaré sans objet pour ce millésime ;
- A_VALIDER            : seules des valeurs DIAGNOSTIC / VALIDATION existent ;
- MANQUANT             : rien, et aucune explication ;
- REFERENCE_ONLY / REFERENCE_EXTERNE : contenu de référence, hors certification.

Statut global :
- NOT_CERTIFIED       : anomalie bloquante, cellule A_VALIDER ou MANQUANT, ou aucune valeur PRODUCTION ;
- CERTIFIED_WITH_GAPS : tout est PRODUCTION ou explicitement déclaré, avec au moins une lacune ;
- CERTIFIED           : tout est PRODUCTION (ou non applicable).
"""
from __future__ import annotations

from datetime import datetime, timezone

from .referentiel import Referentiel

LACUNES_PAR_STATUT_SOURCE = {"INCOMPLETE_INVENTORY", "SOURCE_MANUELLE_REQUISE", "SOURCE_NOT_PRODUCED"}
STATUTS_CELLULE = ("PRODUCTION", "LACUNE_DECLAREE", "NON_APPLICABLE", "A_VALIDER", "MANQUANT",
                   "REFERENCE_ONLY", "REFERENCE_EXTERNE")
STATUTS_INDICATEUR = ("COMPLET", "COMPLET_AVEC_LACUNES", "PARTIEL", "A_VALIDER", "MANQUANT", "LACUNE_DECLAREE",
                      "NON_APPLICABLE", "REFERENCE_ONLY")
COUVERTURE_FIELDS = ["annee", "indicator_id", "libelle", "perimeter_id", "statut_attente", "statut_couverture",
                     "valeur_production", "unite", "source", "explication"]


def _declared_gap(ref: Referentiel, year: int, iid: str, pid: str) -> tuple[str, str] | None:
    for l in ref.lacunes:
        if l["annee"] == str(year) and l["indicator_id"] in (iid, "*") and l["perimeter_id"] in (pid, "*"):
            statut = "NON_APPLICABLE" if l["statut"] == "NON_APPLICABLE" else "LACUNE_DECLAREE"
            return statut, l["note"] or l["statut"]
    domain = ref.indicateurs.get(iid, {}).get("domaine", "")
    ind = ref.indicateurs.get(iid, {})
    for a in ref.absences:
        if a["year"] != str(year) or a["domain"] != domain:
            continue
        epci = ref.epci_du_territoire(a["territory"])
        if epci == pid:
            return "LACUNE_DECLAREE", f"{a['status']} : {a['note']}"
        if pid == "MARTINIQUE" and epci and ind.get("agregation_martinique") == "SOMME_EPCI":
            return "LACUNE_DECLAREE", f"Total Martinique incalculable : {a['territory']} {a['status']} ({a['note']})"
    return None


def certify(ref: Referentiel, year: int, facts: list[dict], anomalies: list[dict]) -> tuple[dict, list[dict], list[dict]]:
    cells = []
    for att in ref.attentes_annee(year):
        iid, pid, statut_att = att["indicator_id"], att["perimeter_id"], att["statut_attente"]
        rows = [f for f in facts if f["indicator_id"] == iid and f["perimeter_id"] == pid]
        prod = [f for f in rows if f["record_role"] == "PRODUCTION"]
        cell = {"annee": year, "indicator_id": iid, "libelle": ref.indicateurs.get(iid, {}).get("libelle", ""),
                "perimeter_id": pid, "statut_attente": statut_att, "valeur_production": "", "unite": "",
                "source": "", "explication": att.get("note", "")}
        if statut_att in ("REFERENCE_ONLY", "REFERENCE_EXTERNE"):
            cell["statut_couverture"] = statut_att
        elif prod:
            p = prod[0]
            cell.update(statut_couverture="PRODUCTION", valeur_production=p["value"], unite=p["unit"],
                        source=f"{p['source']} {p['code_source']} {p['source_file']}".strip())
        elif (gap := _declared_gap(ref, year, iid, pid)) is not None:
            cell["statut_couverture"], cell["explication"] = gap
        elif any(f["quality_status"] in LACUNES_PAR_STATUT_SOURCE for f in rows):
            f = next(f for f in rows if f["quality_status"] in LACUNES_PAR_STATUT_SOURCE)
            cell.update(statut_couverture="LACUNE_DECLAREE", explication=f"{f['quality_status']} : {f['note']}")
        elif any(f["record_role"] in ("DIAGNOSTIC", "VALIDATION") for f in rows):
            f = max((f for f in rows if f["record_role"] in ("DIAGNOSTIC", "VALIDATION")), key=lambda f: f["record_role"] == "VALIDATION")
            cell.update(statut_couverture="A_VALIDER", explication=f"Valeur {f['record_role']} {f['value']} ({f['source']}) : {f['quality_status']}. {f['note']}"[:400])
        else:
            cell["statut_couverture"] = "MANQUANT"
            cell["explication"] = "Aucune valeur et aucune absence déclarée."
        cells.append(cell)

    # Synthèse exhaustive : chaque indicateur de publication reçoit un statut.
    par_indicateur = []
    for iid in ref.publication_ids():
        cs = [c for c in cells if c["indicator_id"] == iid and c["statut_attente"] != "REFERENCE_EXTERNE"]
        st = {c["statut_couverture"] for c in cs}
        if not cs:
            statut = "NON_APPLICABLE"
        elif st <= {"REFERENCE_ONLY"}:
            statut = "REFERENCE_ONLY"
        elif st <= {"PRODUCTION", "NON_APPLICABLE"}:
            statut = "COMPLET"
        elif st <= {"PRODUCTION", "NON_APPLICABLE", "LACUNE_DECLAREE"} and "PRODUCTION" in st:
            statut = "COMPLET_AVEC_LACUNES"
        elif st <= {"LACUNE_DECLAREE", "NON_APPLICABLE"}:
            statut = "LACUNE_DECLAREE"
        elif "PRODUCTION" in st:
            statut = "PARTIEL"
        elif "A_VALIDER" in st:
            statut = "A_VALIDER"
        else:
            statut = "MANQUANT"
        par_indicateur.append({"annee": year, "indicator_id": iid, "libelle": ref.indicateurs[iid]["libelle"],
                               "statut_indicateur": statut, "cellules": len(cs),
                               "cellules_production": sum(c["statut_couverture"] == "PRODUCTION" for c in cs)})

    count = lambda s: sum(c["statut_couverture"] == s for c in cells)
    blocking = [a for a in anomalies if a["severite"] == "BLOQUANT"]
    certifiables = [c for c in cells if c["statut_attente"] == "EXPECTED"]
    n_prod = count("PRODUCTION")
    if blocking or count("MANQUANT") or count("A_VALIDER") or n_prod == 0:
        status = "NOT_CERTIFIED"
    elif count("LACUNE_DECLAREE"):
        status = "CERTIFIED_WITH_GAPS"
    else:
        status = "CERTIFIED"

    result = {
        "schema_version": "2.0",
        "year": year,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "cellules_attendues": len(certifiables),
        "cellules": {s: count(s) for s in STATUTS_CELLULE},
        "taux_production_pct": round(100 * n_prod / len(certifiables), 1) if certifiables else 0.0,
        "indicateurs": {s: sum(p["statut_indicateur"] == s for p in par_indicateur) for s in STATUTS_INDICATEUR},
        "anomalies_bloquantes": len(blocking),
        "avertissements": sum(a["severite"] == "AVERTISSEMENT" for a in anomalies),
        "politique": {
            "CERTIFIED": "toutes les cellules attendues ont une valeur PRODUCTION",
            "CERTIFIED_WITH_GAPS": "cellules PRODUCTION ou absences explicitement déclarées",
            "NOT_CERTIFIED": "anomalie bloquante, valeur à valider, valeur manquante non expliquée, ou millésime vide",
        },
        "detail_anomalies_bloquantes": blocking,
    }
    return result, cells, par_indicateur
