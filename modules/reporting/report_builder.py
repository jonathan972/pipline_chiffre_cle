"""Générateur DOCX de contrôle fondé sur le master canonique."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from pipeline.publication import load_production_master, production_index
from pipeline.referentiel import Referentiel, read_csv
from pipeline.run import run as run_pipeline

BLUE = "174A72"
PALE_BLUE = "EAF2F8"
LIGHT_GRAY = "D9D9D9"
DOMAIN_LABELS = {
    "RESSOURCE": "Ressource en eau",
    "EAU_POTABLE": "Eau potable",
    "ASSAINISSEMENT_COLLECTIF": "Assainissement collectif",
    "ANC": "Assainissement non collectif",
    "TARIFS": "Tarifs",
}
PREFLIGHT_FIELDS = [
    "token", "page", "indicator_id", "territory", "perimeter_id", "status",
    "required", "value", "unit", "source", "message",
]


def _shade(cell, fill: str) -> None:
    props = cell._tc.get_or_add_tcPr()
    shading = props.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        props.append(shading)
    shading.set(qn("w:fill"), fill)


def _borders(table) -> None:
    props = table._tbl.tblPr
    borders = props.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        props.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        item = OxmlElement(f"w:{edge}")
        item.set(qn("w:val"), "single")
        item.set(qn("w:sz"), "4")
        item.set(qn("w:color"), LIGHT_GRAY)
        borders.append(item)


def _repeat_header(row) -> None:
    props = row._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    props.append(repeat)


def _configure_document(doc: Document, year: int) -> None:
    section = doc.sections[0]
    section.top_margin = Cm(1.8)
    section.bottom_margin = Cm(1.7)
    section.left_margin = Cm(1.8)
    section.right_margin = Cm(1.8)
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(9.5)
    normal.font.color.rgb = RGBColor(0, 0, 0)
    normal.paragraph_format.space_after = Pt(5)
    for name, size in (("Title", 24), ("Heading 1", 16), ("Heading 2", 12)):
        style = styles[name]
        style.font.name = "Arial"
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor(0, 0, 0)
    title = doc.add_paragraph(style="Title")
    title.add_run(f"Chiffres clés eau et assainissement {year}")
    subtitle = doc.add_paragraph()
    subtitle.add_run("Rapport de contrôle du socle de données").bold = True
    doc.add_paragraph(
        "Ce document présente les valeurs publiables disponibles et les lacunes "
        "identifiées pour le millésime. Il sert à valider les données avant leur "
        "mise en page dans le rapport éditorial."
    )


def _add_summary(doc: Document, certification: dict) -> None:
    doc.add_heading("État de la certification", level=1)
    table = doc.add_table(rows=2, cols=5)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers = ["Statut", "Production", "Lacunes", "À valider", "Manquantes"]
    values = [
        certification["status"],
        str(certification["cellules"]["PRODUCTION"]),
        str(certification["cellules"]["LACUNE_DECLAREE"]),
        str(certification["cellules"]["A_VALIDER"]),
        str(certification["cellules"]["MANQUANT"]),
    ]
    for col, value in enumerate(headers):
        cell = table.rows[0].cells[col]
        cell.text = value
        _shade(cell, BLUE)
        for run in cell.paragraphs[0].runs:
            run.font.color.rgb = RGBColor(255, 255, 255)
            run.bold = True
    for col, value in enumerate(values):
        table.rows[1].cells[col].text = value
        table.rows[1].cells[col].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for row in table.rows:
        for cell in row.cells:
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    _borders(table)


def _add_domain_table(doc: Document, label: str, rows: list[dict[str, str]]) -> None:
    doc.add_heading(label, level=1)
    if not rows:
        doc.add_paragraph("Aucune valeur publiable disponible.")
        return
    table = doc.add_table(rows=1, cols=5)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    headers = ["Indicateur", "Territoire", "Valeur", "Unité", "Source"]
    for col, value in enumerate(headers):
        cell = table.rows[0].cells[col]
        cell.text = value
        _shade(cell, BLUE)
        for run in cell.paragraphs[0].runs:
            run.font.color.rgb = RGBColor(255, 255, 255)
            run.bold = True
    _repeat_header(table.rows[0])
    for index, row in enumerate(rows):
        cells = table.add_row().cells
        values = [row["indicator_id"], row["territoire"], row["value"], row["unit"], row["source"]]
        for col, value in enumerate(values):
            cells[col].text = str(value)
            cells[col].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if col in (2, 3):
                cells[col].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            if index % 2:
                _shade(cells[col], PALE_BLUE)
    _borders(table)


def _preflight_rows(cells: list[dict[str, str]]) -> list[dict[str, str]]:
    out = []
    for cell in cells:
        status = cell["statut_couverture"]
        public_status = {
            "PRODUCTION": "READY",
            "LACUNE_DECLAREE": "DECLARED_GAP",
            "NON_APPLICABLE": "NOT_APPLICABLE",
            "REFERENCE_ONLY": "REFERENCE_ONLY",
            "REFERENCE_EXTERNE": "REFERENCE_EXTERNAL",
            "A_VALIDER": "MISSING_VALUE",
            "MANQUANT": "MISSING_VALUE",
        }[status]
        iid, pid = cell["indicator_id"], cell["perimeter_id"]
        out.append({
            "token": "{{" + iid + "_" + pid + "}}",
            "page": "",
            "indicator_id": iid,
            "territory": pid,
            "perimeter_id": pid,
            "status": public_status,
            "required": "yes" if cell["statut_attente"] == "EXPECTED" else "no",
            "value": cell["valeur_production"],
            "unit": cell["unite"],
            "source": cell["source"],
            "message": cell["explication"],
        })
    return out


def _write_preflight(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PREFLIGHT_FIELDS, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def build_docx(root: Path, year: int, out: Path, mode: str = "draft"):
    """Construit le rapport de contrôle et retourne son chemin et sa synthèse."""
    canonical = root / "outputs" / str(year)
    master_path = canonical / f"fact_indicateur_master_{year}.csv"
    coverage_path = canonical / f"couverture_{year}.csv"
    certification_path = canonical / f"certification_{year}.json"
    if not (master_path.exists() and coverage_path.exists() and certification_path.exists()):
        run_pipeline(year, canonical, root)

    production = load_production_master(master_path)
    production_by_cell = production_index(production)
    cells = read_csv(coverage_path)
    ref = Referentiel.load(root)
    certification = json.loads(certification_path.read_text(encoding="utf-8"))
    preflight = _preflight_rows(cells)
    out.mkdir(parents=True, exist_ok=True)
    preflight_path = out / f"preflight_report_{year}.csv"
    _write_preflight(preflight_path, preflight)

    document = Document()
    _configure_document(document, year)
    _add_summary(document, certification)
    displayed: list[dict[str, str]] = []
    for cell in cells:
        if cell["statut_couverture"] != "PRODUCTION":
            continue
        key = (cell["indicator_id"], cell["perimeter_id"])
        if key not in production_by_cell:
            raise ValueError(f"Couverture PRODUCTION sans fait publiable : {key[0]} × {key[1]}")
        displayed.append(production_by_cell[key])
    by_domain: dict[str, list[dict[str, str]]] = {}
    for row in displayed:
        if ref.indicateurs[row["indicator_id"]]["type"] == "PUBLICATION":
            by_domain.setdefault(row["domain"], []).append(row)
    for domain, label in DOMAIN_LABELS.items():
        rows = sorted(by_domain.get(domain, []), key=lambda r: (r["indicator_id"], r["perimeter_id"]))
        _add_domain_table(document, label, rows)

    docx_path = out / f"rapport_controle_{year}.docx"
    document.save(docx_path)
    blocking = sum(row["required"] == "yes" and row["status"] == "MISSING_VALUE" for row in preflight)
    summary = {
        "mode": mode,
        "report_kind": "controle_canonique",
        "certification": certification["status"],
        "production_count": len(displayed),
        "blocking_count": blocking,
        "preflight_count": len(preflight),
    }
    return docx_path, summary
