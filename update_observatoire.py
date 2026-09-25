#!/usr/bin/env python3
"""Point d'entrée annuel V1/v8 du Référentiel Eau & Assainissement."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Consolide un millésime puis produit sa certification."
    )
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--out", help="Répertoire de sortie (défaut : outputs/annual_YYYY)")
    parser.add_argument("--refresh-ars", action="store_true")
    parser.add_argument("--ars-fixture")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    out = Path(args.out).resolve() if args.out else (
        root / "modules" / "orchestrator" / "outputs" / f"annual_{args.year}"
    )

    command = [
        sys.executable,
        str(root / "modules" / "orchestrator" / "update_observatoire.py"),
        "--year",
        str(args.year),
        "--root",
        str(root),
        "--out",
        str(out),
    ]
    if args.refresh_ars:
        command.append("--refresh-ars")
    if args.ars_fixture:
        command.extend(["--ars-fixture", args.ars_fixture])
    if args.strict:
        command.append("--strict")

    subprocess.run(command, check=True)
    subprocess.run(
        [
            sys.executable,
            str(root / "modules" / "orchestrator" / "certify_year.py"),
            "--year",
            str(args.year),
            "--facts",
            str(out / f"fact_indicateur_master_{args.year}.csv"),
            "--quality-report",
            str(out / f"quality_report_{args.year}.csv"),
            "--known-absences",
            str(root / "modules" / "perimeters" / "known_absences.csv"),
            "--out",
            str(out / f"certification_{args.year}.json"),
        ],
        check=True,
    )
    print(f"\nLivrables V1/v8 : {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
