#!/usr/bin/env python3
"""Génère le classeur pédagogique avec la mise en forme canonique.

Ce script requiert un environnement où `artifact_tool` est disponible.
Le classeur d'exemple du dossier `examples/` est le golden master visuel.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from artifact_tool import SpreadsheetFile, Workbook


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def num(v) -> float:
    if v is None or v == "":
        return 0.0
    return float(str(v).replace(",", "."))


def group_amount(rows, key, value="montant_eur"):
    out = defaultdict(float)
    for r in rows:
        out[r[key]] += num(r.get(value))
    return dict(out)


def service_rows(rows, service):
    return [r for r in rows if r.get("service") == service]


def load_m49(m49_dir: Path):
    return {
        "fonctionnement": read_csv(m49_dir / "m49_fonctionnement.csv"),
        "investissement": read_csv(m49_dir / "m49_investissement.csv"),
        "ressources": read_csv(m49_dir / "m49_ressources.csv"),
        "indicateurs": read_csv(m49_dir / "m49_indicateurs.csv"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, type=Path)
    ap.add_argument("--facture", required=True, type=Path)
    ap.add_argument("--care-resume", required=True, type=Path)
    ap.add_argument("--care-couts", required=True, type=Path)
    ap.add_argument("--m49-dir", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()

    p = json.loads(args.project.read_text(encoding="utf-8-sig"))
    facture = read_csv(args.facture)
    care_resume = read_csv(args.care_resume)
    care_couts = read_csv(args.care_couts)
    m49 = load_m49(args.m49_dir)

    year_f = p["annee_facture"]
    year_c = p["annee_comptable"]
    collectivite = p["collectivite"]
    delegataire = p["delegataire"]
    volume = num(p.get("volume_reference_m3", 120))

    title_fmt = {"fill":"#123B5D","font":{"bold":True,"color":"#FFFFFF","size":16},"horizontal_alignment":"left","vertical_alignment":"center"}
    section_fmt = {"fill":"#DCEAF5","font":{"bold":True,"color":"#123B5D","size":12},"horizontal_alignment":"left","vertical_alignment":"center"}
    header_fmt = {"fill":"#4F81BD","font":{"bold":True,"color":"#FFFFFF"},"horizontal_alignment":"center","vertical_alignment":"center","wrap_text":True}
    subheader_fmt = {"fill":"#EAF2F8","font":{"bold":True,"color":"#123B5D"},"wrap_text":True}
    note_fmt = {"fill":"#FFF2CC","font":{"italic":True,"color":"#7F6000"},"wrap_text":True}
    kpi_fmt = {"fill":"#E2F0D9","font":{"bold":True,"color":"#375623","size":12},"horizontal_alignment":"center","vertical_alignment":"center"}

    wb = Workbook.create()
    s0 = wb.worksheets.add("0_Parcours")
    s1 = wb.worksheets.add(f"1_Facture_{year_f}")
    s2 = wb.worksheets.add(f"2_CARE_{delegataire}_{year_c}"[:31])
    s3 = wb.worksheets.add(f"3_Budget_{collectivite}_{year_c}"[:31])
    s4 = wb.worksheets.add("4_Detail_sources")
    s5 = wb.worksheets.add("5_Texte_public")

    def pie(sheet, source, title, start, end):
        ch = sheet.charts.add("pie", sheet.get_range(source))
        ch.title_text = title
        ch.has_legend = True
        ch.legend.position = "right"
        ch.set_position(start, end)
        return ch

    # 0 - parcours
    s0.merge_cells("A1:J2"); s0.get_range("A1").values=[[p.get("titre") or "Comprendre le prix de l'eau : de la facture au coût réel du service"]]; s0.get_range("A1:J2").format=title_fmt
    s0.merge_cells("A4:J4"); s0.get_range("A4").values=[["Parcours de lecture"]]; s0.get_range("A4:J4").format=section_fmt
    s0.get_range("A6:D9").values=[
        ["Étape","Source / année","Question grand public","Source"],
        ["1",f"FACTURE {volume:g} m³ – {year_f}","Qui reçoit l'argent payé par l'usager ?",p.get("source_facture","")],
        ["2",f"CARE {delegataire} – {year_c}","À quoi servent les recettes du contrat délégué ?",p.get("source_care","")],
        ["3",f"BUDGET {collectivite} M49 – {year_c}","Que finance la collectivité et d'où viennent ses autres ressources ?",p.get("source_m49","")],
    ]; s0.get_range("A6:D6").format=header_fmt; s0.get_range("A7:D9").format.wrap_text=True
    s0.merge_cells("A11:J15")
    mismatch = "" if year_f == year_c else f" Les factures portent sur {year_f}, tandis que le CARE et la balance M49 portent sur {year_c}."
    s0.get_range("A11").values=[["Les graphiques se suivent pour expliquer les mécanismes, mais ne constituent pas une réconciliation comptable automatique euro pour euro." + mismatch + " Le CARE décrit l'économie du contrat du délégataire ; la balance M49 décrit la comptabilité publique de la collectivité."]]
    s0.get_range("A11:J15").format=note_fmt
    for c,w in [("A:A",9),("B:B",28),("C:C",46),("D:D",38)]: s0.get_range(c).format.column_width=w
    s0.freeze_panes.freeze_rows(4)

    # 1 - facture
    service_totals = group_amount(facture, "service")
    total = sum(service_totals.values())
    nature_totals = group_amount(facture, "nature")
    main = [
        [f"Part {delegataire} (hors TVA)", nature_totals.get("delegataire",0)],
        [f"Part {collectivite} (hors TVA)", nature_totals.get("collectivite",0)],
        ["Redevances", nature_totals.get("redevance",0)],
        ["Taxes hors TVA", nature_totals.get("taxe",0)],
        ["TVA", nature_totals.get("tva",0)],
    ]
    s1.merge_cells("A1:N2"); s1.get_range("A1").values=[[f"1. Facture type {volume:g} m³ – qui reçoit l'argent ?"]]; s1.get_range("A1:N2").format=title_fmt
    s1.get_range("A4:C8").values=[
        ["Indicateur","Valeur","Unité"],
        ["Eau potable",service_totals.get("Eau",0),"€ TTC"],
        ["Assainissement",service_totals.get("Assainissement",0),"€ TTC"],
        ["Total petit cycle",total,"€ TTC"],
        ["Prix moyen",total/volume if volume else 0,"€ / m³ TTC"],
    ]; s1.get_range("A4:C4").format=header_fmt; s1.get_range("A5:C8").format=kpi_fmt; s1.get_range("B5:B8").format.number_format='#,##0.00'
    table = [["Destination","Montant (€)","Part de la facture","Sur 100 €"]] + [[k,v,None,None] for k,v in main] + [["TOTAL",total,None,None]]
    s1.get_range("A11:D17").values=table; s1.get_range("A11:D11").format=header_fmt
    for r in range(12,17): s1.get_range(f"C{r}").formulas=[[f"=B{r}/$B$17"]]; s1.get_range(f"D{r}").formulas=[[f"=C{r}*100"]]
    s1.get_range("C17").formulas=[["=SUM(C12:C16)"]]; s1.get_range("D17").formulas=[["=SUM(D12:D16)"]]; s1.get_range("A17:D17").format=subheader_fmt
    s1.get_range("B12:B17").format.number_format='#,##0.00 "€"'; s1.get_range("C12:C17").format.number_format='0.0%'; s1.get_range("D12:D17").format.number_format='0.0'
    s1.get_range("J11:K16").values=[["Destination","Part (%)"]]+[[k,(v/total*100 if total else 0)] for k,v in main]; s1.get_range("J11:K11").format=header_fmt
    pie(s1,"J11:K16","Sur 100 € payés : qui reçoit quoi ?","F16","N31")
    s1.get_range("F11:G13").values=[["Service","Montant TTC (€)"],["Eau potable",service_totals.get("Eau",0)],["Assainissement",service_totals.get("Assainissement",0)]]; s1.get_range("F11:G11").format=header_fmt
    pie(s1,"F11:G13","Eau potable vs assainissement","F33","N48")
    detail_tax = [[r.get("sous_categorie") or r.get("categorie"),num(r.get("montant_eur")),r.get("nature")] for r in facture if r.get("nature") in {"redevance","taxe"}]
    if detail_tax:
        end=26+len(detail_tax); s1.get_range(f"A26:C{end}").values=[["Prélèvement public","Montant (€)","Nature"]]+detail_tax; s1.get_range("A26:C26").format=header_fmt
    s1.merge_cells("A19:D23"); s1.get_range("A19").values=[["Lecture : les redevances sont volontairement séparées des taxes et de la TVA. La part du délégataire n'est pas son bénéfice : elle finance l'exploitation du service."]]; s1.get_range("A19:D23").format=note_fmt
    for c,w in [("A:A",34),("B:B",18),("C:C",19),("D:D",14),("F:F",22),("G:G",18),("J:J",30),("K:K",12)]: s1.get_range(c).format.column_width=w
    s1.freeze_panes.freeze_rows(2)

    # 2 - CARE
    resume = {r["service"]:r for r in care_resume}
    s2.merge_cells("A1:N2"); s2.get_range("A1").values=[[f"2. CARE {year_c} – à quoi servent les recettes du contrat délégué ?"]]; s2.get_range("A1:N2").format=title_fmt
    s2.get_range("A4:D8").values=[["Indicateur","Eau","Assainissement","Lecture"],
        ["Total produits CARE",num(resume.get("Eau",{}).get("total_produits")),num(resume.get("Assainissement",{}).get("total_produits")),"Produits du contrat"],
        ["Sommes collectivités / organismes publics",num(resume.get("Eau",{}).get("reversements_publics")),num(resume.get("Assainissement",{}).get("reversements_publics")),"Reversements / charges publiques"],
        ["Charges hors reversements publics",num(resume.get("Eau",{}).get("charges_hors_reversements")),num(resume.get("Assainissement",{}).get("charges_hors_reversements")),"Coûts du contrat après neutralisation des sommes publiques"],
        ["Résultat avant impôt",num(resume.get("Eau",{}).get("resultat_avant_impot")),num(resume.get("Assainissement",{}).get("resultat_avant_impot")),"Résultat comptable du contrat"],
    ]; s2.get_range("A4:D4").format=header_fmt; s2.get_range("B5:C8").format.number_format='#,##0 "€"'; s2.get_range("D5:D8").format.wrap_text=True
    s2.get_range("A10").values=[["Note de lecture"]]; s2.get_range("A10").format=section_fmt
    s2.get_range("A11").values=[["Le CARE n'est pas le budget de la collectivité. Il retrace l'économie du contrat exploité par le délégataire. Les graphiques neutralisent les montants classés comme collectivités / organismes publics."]]; s2.get_range("A11").format=note_fmt; s2.get_range("A11").format.row_height=72

    def write_cost_block(service, start, chart_start, chart_end):
        rows=service_rows(care_couts,service); end=start+len(rows)+1
        s2.get_range(f"A{start}:C{end}").values=[[f"{service} – poste de coût","Montant (€)","Part"]]+[[r["poste"],num(r["montant_eur"]),None] for r in rows]+[["TOTAL",sum(num(r["montant_eur"]) for r in rows),None]]
        s2.get_range(f"A{start}:C{start}").format=header_fmt
        for rr in range(start+1,end): s2.get_range(f"C{rr}").formulas=[[f"=B{rr}/$B${end}"]]
        s2.get_range(f"C{end}").formulas=[[f"=SUM(C{start+1}:C{end-1})"]]; s2.get_range(f"A{end}:C{end}").format=subheader_fmt
        helper_start=start; helper_end=start+len(rows); s2.get_range(f"E{helper_start}:F{helper_end}").values=[[f"{service} – coût","Montant"]]+[[r["poste"],num(r["montant_eur"])] for r in rows]; s2.get_range(f"E{helper_start}:F{helper_start}").format=header_fmt
        pie(s2,f"E{helper_start}:F{helper_end}",f"Structure des coûts du contrat – {service} ({year_c})",chart_start,chart_end)
        s2.get_range(f"B{start+1}:B{end}").format.number_format='#,##0 "€"'; s2.get_range(f"C{start+1}:C{end}").format.number_format='0.0%'
        return end
    write_cost_block("Eau",15,"H15","N28")
    write_cost_block("Assainissement",30,"H31","N45")
    s2.get_range("A43").values=[["Repère : la part du délégataire finance ces coûts ; seul le résultat du CARE correspond au résultat comptable du contrat."]]; s2.get_range("A43").format=note_fmt; s2.get_range("A43").format.row_height=60
    for c,w in [("A:A",40),("B:B",18),("C:C",12),("D:D",48),("E:E",42),("F:F",16)]: s2.get_range(c).format.column_width=w
    s2.freeze_panes.freeze_rows(2)

    # 3 - M49
    indicators = {(r["service"],r["indicateur"]):num(r["montant_eur"]) for r in m49["indicateurs"]}
    s3.merge_cells("A1:N2"); s3.get_range("A1").values=[[f"3. Budget {collectivite} M49 {year_c} – combien coûte le service public et d'où vient l'argent ?"]]; s3.get_range("A1:N2").format=title_fmt
    ind_labels=["Fonctionnement – classe 6","Investissement – débits classe 2","Remboursement du capital des emprunts – débits classe 16"]
    s3.get_range("A4:D8").values=[["Dépense budgétaire", "Eau","Assainissement","Attention"]]+[[lab,indicators.get(("Eau",lab),0),indicators.get(("Assainissement",lab),0),"Flux budgétaire annuel"] for lab in ind_labels]+[["Total indicatif des trois blocs",None,None,"À ne pas appeler coût complet"]]
    s3.get_range("A4:D4").format=header_fmt; s3.get_range("B5:C7").format.number_format='#,##0.00 "€"'; s3.get_range("B8").formulas=[["=SUM(B5:B7)"]]; s3.get_range("C8").formulas=[["=SUM(C5:C7)"]]; s3.get_range("A8:D8").format=subheader_fmt
    s3.get_range("A10").values=[["Note de lecture"]]; s3.get_range("A10").format=section_fmt; s3.get_range("A11").values=[["La balance M49 décrit les finances de la collectivité. Les produits exceptionnels ne doivent pas être considérés comme des recettes récurrentes."]]; s3.get_range("A11").format=note_fmt; s3.get_range("A11").format.row_height=72

    def m49_block(rows, service, start, chart_start, chart_end, title):
        rr=service_rows(rows,service); end=start+len(rr)+1
        s3.get_range(f"A{start}:C{end}").values=[[title,"Montant (€)","Part"]]+[[r["poste"],num(r["montant_eur"]),None] for r in rr]+[["TOTAL",sum(num(r["montant_eur"]) for r in rr),None]]
        s3.get_range(f"A{start}:C{start}").format=header_fmt
        for x in range(start+1,end): s3.get_range(f"C{x}").formulas=[[f"=B{x}/$B${end}"]]
        s3.get_range(f"C{end}").formulas=[[f"=SUM(C{start+1}:C{end-1})"]]; s3.get_range(f"A{end}:C{end}").format=subheader_fmt
        hstart=start; hend=start+len(rr); s3.get_range(f"E{hstart}:F{hend}").values=[[title,"Montant"]]+[[r["poste"],num(r["montant_eur"])] for r in rr]; s3.get_range(f"E{hstart}:F{hstart}").format=header_fmt
        pie(s3,f"E{hstart}:F{hend}",title,chart_start,chart_end)
    m49_block(m49["fonctionnement"],"Eau",16,"H16","N28",f"{collectivite} – où part le fonctionnement Eau ?")
    m49_block(m49["fonctionnement"],"Assainissement",30,"H31","N44",f"{collectivite} – où part le fonctionnement Assainissement ?")

    for service,start,col in [("Eau",44,"A"),("Assainissement",44,"E")]:
        rr=service_rows(m49["investissement"],service); total_i=sum(num(r["montant_eur"]) for r in rr)
        if col=="A":
            s3.get_range(f"A{start}:C{start+len(rr)+1}").values=[[f"Investissements {year_c} – {service}","Montant (€)","Part"]]+[[r["poste"],num(r["montant_eur"]),None] for r in rr]+[["TOTAL",total_i,None]]; s3.get_range(f"A{start}:C{start}").format=header_fmt
        else:
            s3.get_range(f"E{start}:G{start+len(rr)+1}").values=[[f"Investissements {year_c} – {service}","Montant (€)","Part"]]+[[r["poste"],num(r["montant_eur"]),None] for r in rr]+[["TOTAL",total_i,None]]; s3.get_range(f"E{start}:G{start}").format=header_fmt

    s3.merge_cells("A51:N51"); s3.get_range("A51").values=[["D'où vient l'argent en dehors des produits du service ?"]]; s3.get_range("A51:N51").format=section_fmt
    for service,col in [("Eau","A"),("Assainissement","E")]:
        rr=service_rows(m49["ressources"],service)
        rows=[[r["poste"],num(r["montant_eur"]),r.get("role","")] for r in rr]
        if col=="A": s3.get_range(f"A53:C{53+len(rows)}").values=[[f"{service} – ressources {year_c}","Montant (€)","Lecture"]]+rows; s3.get_range("A53:C53").format=header_fmt
        else: s3.get_range(f"E53:G{53+len(rows)}").values=[[f"{service} – ressources {year_c}","Montant (€)","Lecture"]]+rows; s3.get_range("E53:G53").format=header_fmt
    for c,w in [("A:A",42),("B:B",18),("C:C",17),("D:D",42),("E:E",44),("F:F",18),("G:G",22)]: s3.get_range(c).format.column_width=w
    s3.freeze_panes.freeze_rows(2)

    # 4 - audit sources
    s4.merge_cells("A1:K2"); s4.get_range("A1").values=[["Détail des données sources utilisées"]]; s4.get_range("A1:K2").format=title_fmt
    invoice_rows=[[r.get("service"),r.get("categorie"),r.get("sous_categorie"),r.get("nature"),num(r.get("montant_eur")),r.get("source_note","")] for r in facture]
    s4.get_range(f"A5:F{5+len(invoice_rows)}").values=[["Service","Catégorie","Sous-catégorie","Nature","Montant (€)","Source"]]+invoice_rows; s4.get_range("A5:F5").format=header_fmt
    care_rows=[[r.get("service"),r.get("poste"),num(r.get("montant_eur")),r.get("source_note","")] for r in care_couts]
    s4.get_range(f"H5:K{5+len(care_rows)}").values=[["Service","Poste CARE","Montant (€)","Source"]]+care_rows; s4.get_range("H5:K5").format=header_fmt
    s4.freeze_panes.freeze_rows(5)

    # 5 - texte public
    text=[
        "Comprendre le prix de l'eau : qui reçoit l'argent et à quoi sert-il ?",
        f"Pour {volume:g} m³, la facture type étudiée représente {total:,.2f} € TTC, dont {service_totals.get('Eau',0):,.2f} € pour l'eau potable et {service_totals.get('Assainissement',0):,.2f} € pour l'assainissement.",
        f"Sur 100 € payés, environ {nature_totals.get('delegataire',0)/total*100:.1f} € correspondent à la part hors TVA du délégataire, {nature_totals.get('collectivite',0)/total*100:.1f} € à la collectivité, {nature_totals.get('redevance',0)/total*100:.1f} € aux redevances, {nature_totals.get('taxe',0)/total*100:.1f} € aux taxes hors TVA et {nature_totals.get('tva',0)/total*100:.1f} € à la TVA.",
        "La part du délégataire n'est pas un bénéfice : le CARE montre qu'elle finance le personnel, l'énergie, les achats, la sous-traitance, le renouvellement et les autres charges du contrat.",
        "La part de la collectivité relève du budget public M49 : elle finance le fonctionnement, l'investissement et le remboursement du capital, selon des règles comptables distinctes du CARE.",
        "Les produits du service ne sont pas la seule ressource de la collectivité : subventions d'investissement, emprunts nouveaux, autres produits et produits exceptionnels doivent être distingués.",
    ]
    s5.merge_cells("A1:H2"); s5.get_range("A1").values=[["Texte explicatif – version grand public"]]; s5.get_range("A1:H2").format=title_fmt
    row=4
    for i,t in enumerate(text):
        s5.merge_cells(f"A{row}:H{row}"); s5.get_range(f"A{row}").values=[[t]]; s5.get_range(f"A{row}:H{row}").format.wrap_text=True
        if i==0: s5.get_range(f"A{row}:H{row}").format=section_fmt
        else: s5.get_range(f"A{row}:H{row}").format.row_height=70
        row+=2
    for c in "ABCDEFGH": s5.get_range(f"{c}:{c}").format.column_width=15

    for sh in [s0,s1,s2,s3,s4,s5]: sh.get_range("A1:Z200").format.vertical_alignment="center"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    SpreadsheetFile.export_xlsx(wb).save(str(args.output))
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
