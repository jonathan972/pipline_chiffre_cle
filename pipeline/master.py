"""Master unique : un millésime -> fact_indicateur_master_YYYY.csv en identifiants canoniques.

Étapes :
1. collecte des faits bruts de chaque adaptateur (sources.py) ;
2. traduction code source -> indicator_id canonique (correspondance_codes.csv) ;
3. résolution du périmètre (perimetres.csv) ;
4. calculs dérivés déclarés ci-dessous (sommes EPCI, ratios) ;
5. détection des anomalies (code inconnu, périmètre inconnu, conflit de PRODUCTION…).

Toutes les lignes sont conservées (PRODUCTION, VALIDATION, DIAGNOSTIC, AUDIT) :
le master est une table de faits, pas une sélection. La règle « une seule
valeur PRODUCTION par indicateur × périmètre » est vérifiée, jamais forcée.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from .referentiel import Referentiel
from .sources import ADAPTATEURS

FIELDS = [
    "annee_reference", "indicator_id", "domain", "perimeter_id", "territoire", "value", "unit",
    "record_role", "quality_status", "coverage_status", "source", "code_source", "source_file",
    "source_page", "source_detail", "population_millesime", "definition", "note",
]
ANOMALY_FIELDS = ["severite", "type", "indicator_id", "perimeter_id", "source", "code_source", "message"]

RANG_ROLE = {"PRODUCTION": 3, "VALIDATION": 2, "DIAGNOSTIC": 1, "AUDIT": 0}
MAUVAIS_STATUTS = ("ERROR", "INVALID", "INCOHERENT", "SUSPECTED")
EPCI = ("CACEM_EPCI", "CAESM_EPCI", "CAP_NORD_EPCI")

# Ratios calculés : (indicateur, formule lisible, fonction, entrées, unité, périmètres)
# Le rôle du résultat est le plus faible des rôles des entrées.
RATIOS = [
    ("RES_018", "RES_014 × 1000 / (365 × 86 400)", lambda v: v["RES_014"] * 1000 / (365 * 86400), ["RES_014"], "L/s", ["MARTINIQUE"]),
    ("EP_001", "EP_006 × 1000 / (POP_001 × 365)", lambda v: v["EP_006"] * 1000 / (v["POP_001"] * 365), ["EP_006", "POP_001"], "L/j/hab", ["MARTINIQUE"]),
    ("EP_008", "EP_006 / RES_014 × 100", lambda v: v["EP_006"] / v["RES_014"] * 100, ["EP_006", "RES_014"], "%", ["MARTINIQUE"]),
    ("EP_009", "(RES_014 − EP_007) / RES_014 × 100", lambda v: (v["RES_014"] - v["EP_007"]) / v["RES_014"] * 100, ["RES_014", "EP_007"], "%", ["MARTINIQUE"]),
    ("EP_010", "(EP_007 − EP_006) / EP_007 × 100", lambda v: (v["EP_007"] - v["EP_006"]) / v["EP_007"] * 100, ["EP_007", "EP_006"], "%", ["MARTINIQUE"]),
    ("AC_013", "AC_012 × 1000 / AC_014", lambda v: v["AC_012"] * 1000 / v["AC_014"], ["AC_012", "AC_014"], "kg MS/abonné/an", list(EPCI)),
    ("AC_016", "AC_014 / EP_005 × 100", lambda v: v["AC_014"] / v["EP_005"] * 100, ["AC_014", "EP_005"], "%", ["MARTINIQUE", *EPCI]),
    ("ANC_001", "ANC_002 / POP_001 × 100", lambda v: v["ANC_002"] / v["POP_001"] * 100, ["ANC_002", "POP_001"], "%", ["MARTINIQUE"]),
    ("TAR_003", "TAR_002 / 12", lambda v: v["TAR_002"] / 12, ["TAR_002"], "€/mois", ["MARTINIQUE"]),
    ("TAR_007", "TAR_006 / 12", lambda v: v["TAR_006"] / 12, ["TAR_006"], "€/mois", ["MARTINIQUE"]),
]
# Sommes de variables sur un même périmètre.
SOMMES = [
    ("ANC_010", ["VAR_ANC_CTRL_CONCEPTION", "VAR_ANC_CTRL_EXECUTION"], "contrôles/an",
     "Contrôles du neuf = conception + bonne exécution."),
]


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Master:
    def __init__(self, ref: Referentiel, year: int):
        self.ref = ref
        self.year = year
        self.facts: list[dict] = []
        self.anomalies: list[dict] = []
        self.sources_used: list[Path] = []
        self.events: list[dict] = []

    # ------------------------------------------------------------ helpers
    def anomaly(self, severite, type_, message, **kw):
        a = {"severite": severite, "type": type_, "message": message}
        a.update(kw)
        self.anomalies.append(a)

    def rows(self, iid: str, pid: str) -> list[dict]:
        return [f for f in self.facts if f["indicator_id"] == iid and f["perimeter_id"] == pid]

    def best(self, iid: str, pid: str) -> dict | None:
        """Meilleure ligne exploitable (hors AUDIT et sans valeur vide) pour un calcul."""
        cands = [f for f in self.rows(iid, pid) if f["record_role"] != "AUDIT" and _num(f["value"]) is not None]
        return max(cands, key=lambda f: RANG_ROLE.get(f["record_role"], 0), default=None)

    def has_production(self, iid: str, pid: str) -> bool:
        return any(f["record_role"] == "PRODUCTION" for f in self.rows(iid, pid))

    def add(self, iid, pid, value, unit, role, **kw):
        ind = self.ref.indicateurs.get(iid, {})
        f = {k: "" for k in FIELDS}
        f.update(annee_reference=str(self.year), indicator_id=iid, domain=ind.get("domaine", ""),
                 perimeter_id=pid, territoire=self.ref.territoire(pid), value=value, unit=unit or ind.get("unite", ""),
                 record_role=role, quality_status="OK", coverage_status="COMPLETE")
        f.update({k: v for k, v in kw.items() if k in FIELDS})
        self.facts.append(f)

    # ------------------------------------------------------------ étapes
    def collect(self):
        for name, adapter in ADAPTATEURS:
            used: list[Path] = []
            raw = adapter(self.ref, self.year, used)
            self.sources_used += used
            self.events.append({"module": name, "status": "OK" if raw else "ABSENT", "faits": len(raw),
                                "fichiers": [str(p.relative_to(self.ref.root)) for p in used]})
            for r in raw:
                self.translate(r)

    def translate(self, r: dict):
        src, code = r["source"], r["code_source"]
        if src == "SAISIE":
            iid, mapping = code, {}
            if iid not in self.ref.indicateurs:
                self.anomaly("BLOQUANT", "INDICATEUR_INCONNU", "Identifiant absent de referentiel/indicateurs.csv.",
                             indicator_id=iid, source=src, code_source=code)
                return
        else:
            mapping = self.ref.correspondances.get((src, code))
            if mapping is None:
                self.anomaly("BLOQUANT", "CODE_NON_MAPPE",
                             "Code source sans correspondance dans referentiel/correspondance_codes.csv : la valeur est écartée.",
                             source=src, code_source=code)
                return
            if mapping["record_role_force"] == "IGNORE":
                return
            iid = mapping["indicator_id"]
        pid = self.ref.perimetre(r["perimeter_raw"], r["territoire_raw"])
        if pid is None:
            self.anomaly("BLOQUANT", "PERIMETRE_INCONNU",
                         f"Périmètre « {r['perimeter_raw'] or r['territoire_raw']} » absent de referentiel/perimetres.csv.",
                         indicator_id=iid, source=src, code_source=code)
            return
        note = " | ".join(x for x in (r["note"], mapping.get("note", "")) if x)
        self.add(iid, pid, r["value"], r["unit"],
                 mapping.get("record_role_force") or r["record_role"],
                 quality_status=mapping.get("quality_status_force") or r["quality_status"],
                 coverage_status=r["coverage_status"], source=src, code_source=code,
                 source_file=r["source_file"], source_page=r["source_page"], source_detail=r["source_detail"],
                 population_millesime=r["population_millesime"], definition=r["definition"], note=note)

    def derive(self):
        # 1. Sommes de variables sur un même périmètre (ex. ANC_010).
        pids = sorted({f["perimeter_id"] for f in self.facts})
        for iid, inputs, unit, note in SOMMES:
            for pid in pids:
                if self.has_production(iid, pid):
                    continue
                parts = [self.best(i, pid) for i in inputs]
                if all(parts):
                    self.add(iid, pid, sum(_num(p["value"]) for p in parts), unit, self._role(parts),
                             source="CALCUL", code_source=" + ".join(inputs), note=note)
        # 2. Martinique = somme des trois EPCI pour les indicateurs additifs.
        tol = float(self.ref.parametres.get("tolerance_somme_epci_pct", 0.5))
        for iid, ind in self.ref.indicateurs.items():
            if ind["agregation_martinique"] != "SOMME_EPCI":
                continue
            parts = [self.best(iid, e) for e in EPCI]
            if not all(parts):
                continue
            total = sum(_num(p["value"]) for p in parts)
            existing = self.best(iid, "MARTINIQUE")
            if existing is None:
                self.add(iid, "MARTINIQUE", total, ind["unite"], self._role(parts), source="CALCUL",
                         code_source="SOMME_EPCI", note="Somme CACEM + CAESM + CAP Nord.")
            elif total and abs(_num(existing["value"]) - total) / total * 100 > tol:
                self.anomaly("AVERTISSEMENT", "INCOHERENCE_SOMME_EPCI",
                             f"Martinique = {existing['value']} ({existing['source']}) mais somme EPCI = {total:g}.",
                             indicator_id=iid, perimeter_id="MARTINIQUE", source=existing["source"])
        # 3. Ratios.
        for iid, formula, fn, inputs, unit, perims in RATIOS:
            for pid in perims:
                if self.has_production(iid, pid):
                    continue
                parts = {i: self.best(i, pid) for i in inputs}
                if not all(parts.values()):
                    continue
                try:
                    value = fn({i: _num(p["value"]) for i, p in parts.items()})
                except ZeroDivisionError:
                    continue
                self.add(iid, pid, round(value, 6), unit, self._role(list(parts.values())), source="CALCUL",
                         code_source=formula,
                         population_millesime=next((p["population_millesime"] for p in parts.values() if p["population_millesime"]), ""),
                         note="Entrées : " + ", ".join(f"{i}={p['value']} ({p['record_role']})" for i, p in parts.items()))

    @staticmethod
    def _role(parts: list[dict]) -> str:
        worst = min(RANG_ROLE.get(p["record_role"], 0) for p in parts)
        return "PRODUCTION" if worst == 3 else "DIAGNOSTIC"

    def check(self):
        groups: dict[tuple[str, str], list[dict]] = {}
        for f in self.facts:
            if f["record_role"] == "PRODUCTION":
                groups.setdefault((f["indicator_id"], f["perimeter_id"]), []).append(f)
                bad = [t for t in MAUVAIS_STATUTS if t in f["quality_status"]]
                if bad or f["coverage_status"] in ("MISSING", "NO_DATA") or _num(f["value"]) is None:
                    self.anomaly("BLOQUANT", "PRODUCTION_INVALIDE",
                                 f"Ligne PRODUCTION inutilisable (valeur « {f['value']} », {f['coverage_status']} / {f['quality_status']}).",
                                 indicator_id=f["indicator_id"], perimeter_id=f["perimeter_id"], source=f["source"], code_source=f["code_source"])
        for (iid, pid), rows in groups.items():
            values = {round(_num(r["value"]), 6) for r in rows if _num(r["value"]) is not None}
            if len(values) > 1:
                self.anomaly("BLOQUANT", "CONFLIT_PRODUCTION",
                             "Plusieurs valeurs PRODUCTION : " + " ; ".join(f"{r['value']} ({r['source']} {r['code_source']})" for r in rows),
                             indicator_id=iid, perimeter_id=pid)

    def build(self) -> "Master":
        self.collect()
        self.derive()
        self.check()
        self.facts.sort(key=lambda f: (f["domain"], f["indicator_id"], f["perimeter_id"], -RANG_ROLE.get(f["record_role"], 0)))
        return self

    def manifest_sources(self) -> list[dict]:
        seen = []
        for p in dict.fromkeys(self.sources_used):
            seen.append({"fichier": str(p.relative_to(self.ref.root)), "sha256": sha256(p)})
        return seen
