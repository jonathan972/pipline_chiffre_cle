"""Chargement du référentiel canonique (dossier referentiel/).

Toutes les règles de nommage, de périmètre et d'attente sont lues ici depuis
des CSV éditables. Aucun module ne doit coder en dur un rattachement
territorial ou une correspondance de code.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "referentiel"


def read_csv(path: Path, delimiter: str = ";") -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = []
        for n, r in enumerate(csv.DictReader(f, delimiter=delimiter), start=2):
            if None in r:
                raise ValueError(f"{path.name}, ligne {n} : trop de colonnes (point-virgule dans un texte ?).")
            rows.append({k: (v or "").strip() for k, v in r.items()})
        return rows


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def year_in(year: int, start: str, end: str) -> bool:
    return (not start or int(start) <= year) and (not end or year <= int(end))


@dataclass
class Referentiel:
    root: Path
    indicateurs: dict[str, dict] = field(default_factory=dict)
    correspondances: dict[tuple[str, str], dict] = field(default_factory=dict)
    perimetres: dict[str, dict] = field(default_factory=dict)
    alias_perimetre: dict[str, str] = field(default_factory=dict)
    services_sispea: list[dict] = field(default_factory=list)
    attentes: list[dict] = field(default_factory=list)
    lacunes: list[dict] = field(default_factory=list)
    absences: list[dict] = field(default_factory=list)
    parametres: dict = field(default_factory=dict)

    @classmethod
    def load(cls, root: Path = ROOT) -> "Referentiel":
        ref = root / "referentiel"
        r = cls(root=root)
        r.indicateurs = {x["indicator_id"]: x for x in read_csv(ref / "indicateurs.csv")}
        r.correspondances = {(x["source"], x["code_source"]): x for x in read_csv(ref / "correspondance_codes.csv")}
        for p in read_csv(ref / "perimetres.csv"):
            r.perimetres[p["perimeter_id"]] = p
            r.alias_perimetre[p["perimeter_id"]] = p["perimeter_id"]
            for a in filter(None, p["alias"].split("|")):
                r.alias_perimetre[a] = p["perimeter_id"]
        # Suffixes historiques des modules RAD/RPQS (CACEM_EPCI, etc.) déjà canoniques.
        r.services_sispea = read_csv(ref / "services_sispea.csv")
        r.attentes = read_csv(ref / "attentes.csv")
        r.lacunes = read_csv(ref / "lacunes_declarees.csv")
        r.absences = read_csv(root / "modules" / "perimeters" / "known_absences.csv")
        r.parametres = json.loads((ref / "parametres.json").read_text(encoding="utf-8"))
        r.validate()
        return r

    def validate(self) -> None:
        """Refuse un référentiel ambigu ou incomplet avant toute collecte."""
        allowed_expectations = {"EXPECTED", "REFERENCE_ONLY", "REFERENCE_EXTERNE"}
        seen: set[tuple[str, str, str, str]] = set()
        publication_with_expectation: set[str] = set()
        errors: list[str] = []
        for row in self.attentes:
            iid, pid = row["indicator_id"], row["perimeter_id"]
            key = (iid, pid, row["annee_debut"], row["annee_fin"])
            if iid not in self.indicateurs:
                errors.append(f"attente sur indicateur inconnu : {iid}")
            if pid not in self.perimetres:
                errors.append(f"attente sur périmètre inconnu : {pid}")
            if row["statut_attente"] not in allowed_expectations:
                errors.append(f"statut d'attente inconnu : {row['statut_attente']}")
            if key in seen:
                errors.append(f"attente dupliquée : {iid} × {pid} ({row['annee_debut']}-{row['annee_fin']})")
            seen.add(key)
            publication_with_expectation.add(iid)
            if row["annee_debut"] and row["annee_fin"] and int(row["annee_debut"]) > int(row["annee_fin"]):
                errors.append(f"période inversée : {iid} × {pid}")
        missing = sorted(set(self.publication_ids()) - publication_with_expectation)
        if missing:
            errors.append("indicateurs de publication sans attente : " + ", ".join(missing))
        for (source, code), mapping in self.correspondances.items():
            if mapping["record_role_force"] != "IGNORE" and mapping["indicator_id"] not in self.indicateurs:
                errors.append(f"correspondance {source}:{code} vers indicateur inconnu : {mapping['indicator_id']}")
        if errors:
            raise ValueError("Référentiel invalide :\n- " + "\n- ".join(errors))

    # --- Résolution -------------------------------------------------------
    def perimetre(self, perimeter_id: str, territoire: str = "") -> str | None:
        for candidate in (perimeter_id, territoire):
            if candidate in self.alias_perimetre:
                return self.alias_perimetre[candidate]
        return None

    def territoire(self, perimeter_id: str) -> str:
        return self.perimetres.get(perimeter_id, {}).get("territoire", perimeter_id)

    def epci_du_territoire(self, territoire: str) -> str | None:
        """known_absences.csv parle en territoire (CACEM…) : on le ramène au périmètre EPCI."""
        pid = self.perimetre(territoire)
        if pid and self.perimetres[pid]["type"] == "EPCI":
            return pid
        return None

    def attentes_annee(self, year: int) -> list[dict]:
        return [a for a in self.attentes if year_in(year, a["annee_debut"], a["annee_fin"])]

    def publication_ids(self) -> list[str]:
        return [i for i, x in self.indicateurs.items() if x["type"] == "PUBLICATION"]
