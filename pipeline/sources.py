"""Adaptateurs de sources.

Chaque adaptateur lit les sorties d'un module de collecte pour un millésime et
renvoie des faits « bruts » : code de la source, périmètre tel qu'écrit par la
source, valeur, rôle et statuts. Le passage aux identifiants canoniques se fait
ensuite dans master.py, via referentiel/correspondance_codes.csv.

Un adaptateur ne décide d'aucun rattachement territorial : il transmet ce que
la source déclare, ou applique referentiel/services_sispea.csv.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from .referentiel import Referentiel, read_csv, year_in

Fact = dict[str, str]


def _fact(source: str, code: str, value, **kw) -> Fact:
    base = {
        "source": source, "code_source": code, "perimeter_raw": "", "territoire_raw": "",
        "value": "" if value is None else str(value), "unit": "", "record_role": "PRODUCTION",
        "quality_status": "OK", "coverage_status": "COMPLETE", "source_file": "", "source_page": "",
        "source_detail": "", "population_millesime": "", "definition": "", "note": "",
    }
    base.update({k: "" if v is None else str(v) for k, v in kw.items()})
    return base


def _num(v: str):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- INSEE
def insee(ref: Referentiel, year: int, used: list[Path]) -> list[Fact]:
    p = ref.root / "modules/insee_population/outputs/fact_population_resolue_2019_2024.csv"
    rows = [r for r in read_csv(p) if r["annee_indicateur"] == str(year)]
    if rows:
        used.append(p)
    lag_role = ref.parametres.get("role_population_non_millesimee", "DIAGNOSTIC")
    out = []
    for r in rows:
        official = r["statut_resolution"] == "OFFICIEL_MILLESIME_N"
        out.append(_fact(
            "INSEE", "POP_MUNICIPALE", r["population_utilisee"], territoire_raw=r["territoire"],
            unit="hab", record_role="PRODUCTION" if official else lag_role,
            quality_status="OK" if official else "POPULATION_LAG", source_file=p.name,
            source_detail=r["statut_resolution"], population_millesime=r["millesime_population"],
            note="" if official else f"Population du millésime {r['millesime_population']} utilisée pour {year}.",
        ))
    return out


# ---------------------------------------------------------------- BNPE
def bnpe(ref: Referentiel, year: int, used: list[Path]) -> list[Fact]:
    for p in (ref.root / f"modules/bnpe/outputs_{year}/mart_bnpe_indicateurs_{year}.csv",
              ref.root / f"modules/bnpe/outputs/mart_bnpe_indicateurs_{year}.csv"):
        if p.exists():
            used.append(p)
            return [_fact("BNPE", r["indicator_id"], r["value"], territoire_raw="Martinique",
                          unit=r.get("unit", ""), source_file=p.name, source_detail=r.get("calculation", ""))
                    for r in read_csv(p)]
    return []


# ---------------------------------------------------------------- SISPEA
def sispea(ref: Referentiel, year: int, used: list[Path]) -> list[Fact]:
    base = ref.root / "modules/sispea/outputs"
    con_p = base / f"fact_sispea_consolidee_{year}.csv"
    srv_p = base / f"fact_sispea_service_{year}.csv"
    out: list[Fact] = []
    expected_anc = int(ref.parametres.get("sispea_services_anc_attendus", 0))

    def coverage_role(used_n: int):
        complete = used_n >= expected_anc
        return ("COMPLETE", "OK", "PRODUCTION") if complete else ("PARTIAL", "COVERAGE_PARTIAL", "DIAGNOSTIC")

    if con_p.exists():
        used.append(con_p)
        for r in read_csv(con_p):
            code = f"{r['competence']}:{r['code']}"
            if ("SISPEA", code) not in ref.correspondances:
                continue  # seules les variables utiles au rapport sont reprises
            n = int(float(r["nombre_donnees_utilisees"] or 0))
            kw = dict(territoire_raw="Martinique", unit=r["unite"], source_file=r["source_file"],
                      source_detail=r["code"], note=f"{r['code']} ; {n} donnée(s) utilisée(s).")
            if code in ("ANC:P301.3",):
                cov, q, role = coverage_role(n)
                kw.update(coverage_status=cov, quality_status=q, record_role=role,
                          note=f"{n}/{expected_anc} services utilisés.")
            out.append(_fact("SISPEA", code, r["valeur_consolidee"], **kw))

    if srv_p.exists():
        used.append(srv_p)
        rows = read_csv(srv_p)
        # Indicateurs de performance par service -> périmètre déclaré dans services_sispea.csv
        for s in ref.services_sispea:
            if not year_in(year, s["annee_debut"], s["annee_fin"]):
                continue
            for r in rows:
                if r["service_id"] == s["service_id"] and ("SISPEA", f"SERVICE:{r['code']}") in ref.correspondances:
                    out.append(_fact("SISPEA", f"SERVICE:{r['code']}", r["valeur_num"],
                                     perimeter_raw=s["perimeter_id"], source_file=r["source_file"],
                                     source_detail=f"service {s['service_id']} / {r['code']}", note=s["note"]))
        # Variables ANC sommées sur les services renseignés
        anc = [r for r in rows if r["competence"] == "ANC" and _num(r["valeur_num"]) is not None]
        for code in ("DC.306", "DC.332", "DC.333", "VP.334"):
            vals = [_num(r["valeur_num"]) for r in anc if r["code"] == code]
            if not vals:
                continue
            kw = dict(territoire_raw="Martinique", source_file=srv_p.name,
                      source_detail=f"somme {code} sur {len(vals)} service(s)")
            if code == "VP.334":
                cov, q, role = coverage_role(len(vals))
                kw.update(coverage_status=cov, quality_status=q, record_role=role,
                          note=f"{len(vals)}/{expected_anc} services renseignés.")
            out.append(_fact("SISPEA", f"ANC:{code}", sum(vals), **kw))
    return out


# ---------------------------------------------------------------- ERU / STEU
def steu(ref: Referentiel, year: int, used: list[Path]) -> list[Fact]:
    p = ref.root / f"modules/steu/outputs/summary_{year}.json"
    if not p.exists():
        return []
    used.append(p)
    sm = json.loads(p.read_text(encoding="utf-8"))
    m = sm["metrics"]
    terr = {"_cacem": "CACEM", "_caesm": "CAESM", "_cap_nord": "CAP_NORD"}
    out = []
    for key, value in m.items():
        if ("STEU", key) not in ref.correspondances:
            continue
        t = next((v for suf, v in terr.items() if key.endswith(suf)), "Martinique")
        out.append(_fact("STEU", key, value, territoire_raw=t, source_file=sm.get("source_file", p.name),
                         source_detail=key, note=f"Snapshot du portail ERU modifié le {m.get('latest_source_modification_date', '?')}."))
    return out


# ---------------------------------------------------------------- Portail assainissement
def portail(ref: Referentiel, year: int, used: list[Path]) -> list[Fact]:
    for p in (ref.root / f"modules/assainissement_portal/outputs/{year}/fact_assainissement_portal_{year}.csv",
              ref.root / f"modules/assainissement_portal/outputs/fact_assainissement_portal_{year}.csv"):
        if p.exists():
            used.append(p)
            return [_fact("PORTAIL", r["indicator_id"], r["value"], territoire_raw=r.get("territoire", ""),
                          perimeter_raw=r.get("perimeter_id", ""), unit=r.get("unit", ""),
                          record_role=r.get("record_role", "PRODUCTION"), quality_status=r.get("quality_status", "OK"),
                          coverage_status=r.get("coverage_status", "COMPLETE"), source_file=r.get("source_file", p.name),
                          definition=r.get("definition", ""), note=r.get("note", ""))
                    for r in read_csv(p)]
    return []


# ---------------------------------------------------------------- RAD / RPQS (réconciliés)
def local(ref: Referentiel, year: int, used: list[Path]) -> list[Fact]:
    p = ref.root / f"modules/perimeters/outputs/fact_local_reports_reconciled_{year}.csv"
    if not p.exists():
        return []
    used.append(p)
    return [_fact("LOCAL", r["indicator_id"], r["value"], territoire_raw=r["territoire"], perimeter_raw=r["perimeter_id"],
                  unit=r["unit"], record_role=r["record_role"], quality_status=r["quality_status"],
                  coverage_status=r["coverage_status"], source_file=r["source_file"], source_page=r["source_page"],
                  source_detail=r["source_family"], definition=r["definition"], note=r["note"])
            for r in read_csv(p)]


# ---------------------------------------------------------------- ARS / Hub'Eau
def ars(ref: Referentiel, year: int, used: list[Path]) -> list[Fact]:
    p = ref.root / f"modules/ars_quality/outputs/{year}/fact_ars_quality_{year}.csv"
    if not p.exists():
        return []
    used.append(p)
    return [_fact("ARS", r["indicator_id"], r["value"], territoire_raw=r["territoire"], perimeter_raw=r["perimeter_id"],
                  unit=r["unit"], record_role=r["record_role"], quality_status=r["quality_status"],
                  coverage_status=r["coverage_status"], source_file=p.name, source_detail=r.get("source_detail", ""),
                  definition=r.get("definition", ""),
                  note=f"{r.get('numerator', '')}/{r.get('denominator', '')} prélèvements conformes. {r.get('note', '')}".strip())
            for r in read_csv(p)]


# ---------------------------------------------------------------- Entrées manuelles historiques
def manuel(ref: Referentiel, year: int, used: list[Path]) -> list[Fact]:
    p = ref.root / f"modules/master/manual_inputs/manual_external_facts_{year}.csv"
    if not p.exists():
        return []
    used.append(p)
    return [_fact("MANUEL", r["indicator_id"], r["value"], territoire_raw=r["territoire"], unit=r["unit"],
                  record_role=r["record_role"], quality_status="OK", source_file=p.name,
                  source_detail=r.get("source_detail", ""), note=r.get("note", ""))
            for r in read_csv(p, delimiter=",")]


# ---------------------------------------------------------------- Saisie contrôlée (gabarit)
def saisie(ref: Referentiel, year: int, used: list[Path]) -> list[Fact]:
    """Gabarit de saisie RAD/RPQS : saisie/saisie_locale_YYYY.csv, déjà en identifiants canoniques."""
    p = ref.root / f"saisie/saisie_locale_{year}.csv"
    if not p.exists():
        return []
    used.append(p)
    out = []
    for r in read_csv(p):
        if not r.get("value"):
            continue  # ligne du gabarit non remplie
        out.append(_fact("SAISIE", r["indicator_id"], r["value"], perimeter_raw=r["perimeter_id"], unit=r.get("unit", ""),
                         record_role=r.get("record_role") or "PRODUCTION", quality_status=r.get("quality_status") or "OK",
                         source_file=r.get("source_file", ""), source_page=r.get("source_page", ""),
                         note=r.get("commentaire", "")))
    return out


ADAPTATEURS: list[tuple[str, Callable[[Referentiel, int, list[Path]], list[Fact]]]] = [
    ("insee", insee), ("bnpe", bnpe), ("sispea", sispea), ("steu", steu), ("portail", portail),
    ("local", local), ("ars", ars), ("manuel", manuel), ("saisie", saisie),
]
