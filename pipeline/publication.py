"""Frontière de publication : seules les valeurs PRODUCTION sont publiables.

Le master conserve volontairement tous les rôles pour l'audit. Tout consommateur
éditorial (Word, PDF, graphiques publics) doit passer par ce module afin qu'une
valeur VALIDATION, DIAGNOSTIC ou AUDIT ne puisse jamais servir de repli.
"""
from __future__ import annotations

from pathlib import Path

from .referentiel import read_csv


def production_rows(facts: list[dict[str, str]]) -> list[dict[str, str]]:
    """Retourne les faits publiables et refuse toute clé ambiguë."""
    rows = [row for row in facts if row.get("record_role") == "PRODUCTION"]
    seen: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        key = (row.get("indicator_id", ""), row.get("perimeter_id", ""))
        if not all(key):
            raise ValueError("Ligne PRODUCTION sans indicator_id ou perimeter_id.")
        if key in seen:
            raise ValueError(
                "Plusieurs lignes PRODUCTION pour "
                f"{key[0]} × {key[1]} : publication indéterministe."
            )
        seen[key] = row
    return rows


def load_production_master(path: Path) -> list[dict[str, str]]:
    """Charge un master canonique et applique la frontière PRODUCTION-only."""
    return production_rows(read_csv(path))


def production_index(facts: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    """Index strict destiné aux remplacements de placeholders et graphiques."""
    return {(row["indicator_id"], row["perimeter_id"]): row for row in production_rows(facts)}
