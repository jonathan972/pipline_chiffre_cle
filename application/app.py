from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .core import (
    EXPECTED_MAPS, ROOT, add_map, build_report, copy_manual_documents,
    import_assainissement_portal, open_path, refresh_ars, prepare_all_sources,
    rebuild_local_reports, source_status, import_manual_overrides,
    export_missing_values_template, year_out,
)


STATUS_LABELS = {
    "OK": "valeurs publiées", "KNOWN_ABSENCE": "absences déclarées", "NOT_APPLICABLE": "sans objet",
    "MISSING_VALUE": "valeurs requises manquantes", "NOT_PUBLISHABLE": "valeurs à valider",
    "OPTIONAL_MISSING": "éléments facultatifs absents", "MAP_MISSING": "cartes manquantes",
    "BLOCKING_ANOMALY": "anomalies bloquantes", "UNKNOWN_TOKEN": "tokens inconnus du template",
    "REFERENCE": "références externes", "NOT_CERTIFIED": "certification refusée",
}


def format_summary(summary: dict) -> str:
    lines=[f"Millésime {summary.get('year')} — mode {summary.get('mode')}",
           f"Certification : {summary.get('certification')} ({summary.get('taux_production_pct')} % de valeurs publiables)",
           f"Mise en page : {'template Word' if summary.get('template_used') else 'document généré (aucun template fourni)'}",
           f"Graphiques produits : {summary.get('charts', 0)}", ""]
    for status,n in sorted(summary.get("status_counts",{}).items(),key=lambda x:-x[1]):
        lines.append(f"  {n:>4}  {STATUS_LABELS.get(status,status)}")
    blocking=summary.get("blocking_count",0)
    lines += ["", f"Éléments bloquant la version finale : {blocking}"]
    lines += [f"  - {x}" for x in summary.get("blocking_examples",[])]
    if blocking: lines.append("Détail complet : bouton « Ouvrir le préflight ».")
    return "\n".join(lines)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Chiffres clés Eau & Assainissement — ODE Martinique")
        self.geometry("1000x720")
        self.minsize(880, 620)
        self.q: queue.Queue = queue.Queue()
        self.year = tk.IntVar(value=2024)
        self.status_var = tk.StringVar(value="Prêt")
        self._build()
        self.after(150, self._poll)
        self.refresh_status()

    def _build(self):
        header = ttk.Frame(self, padding=14); header.pack(fill="x")
        ttk.Label(header, text="Chiffres clés Eau & Assainissement", font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Label(header, text="Millésime :").pack(side="left", padx=(30, 6))
        yearbox = ttk.Combobox(header, textvariable=self.year, values=[2023, 2024, 2025, 2026], width=8, state="readonly")
        yearbox.pack(side="left"); yearbox.bind("<<ComboboxSelected>>", lambda e: self.refresh_status())
        ttk.Button(header, text="Actualiser l'état", command=self.refresh_status).pack(side="right")

        nb=ttk.Notebook(self); nb.pack(fill="both",expand=True,padx=12,pady=(0,8))
        self.tab_sources=ttk.Frame(nb,padding=12); self.tab_actions=ttk.Frame(nb,padding=12); self.tab_maps=ttk.Frame(nb,padding=12); self.tab_log=ttk.Frame(nb,padding=12)
        nb.add(self.tab_sources,text="1. Sources"); nb.add(self.tab_actions,text="2. Production"); nb.add(self.tab_maps,text="3. Cartes"); nb.add(self.tab_log,text="Journal")

        cols=("source","status","detail")
        self.tree=ttk.Treeview(self.tab_sources,columns=cols,show="headings",height=14)
        self.tree.heading("source",text="Source"); self.tree.heading("status",text="État"); self.tree.heading("detail",text="Détail")
        self.tree.column("source",width=250); self.tree.column("status",width=130,anchor="center"); self.tree.column("detail",width=520); self.tree.pack(fill="both",expand=True)
        b=ttk.Frame(self.tab_sources,padding=(0,10,0,0)); b.pack(fill="x")
        ttk.Button(b,text="Importer CSV assainissement",command=self.import_portal).pack(side="left")
        ttk.Button(b,text="Ajouter RAD / RPQS",command=self.add_docs).pack(side="left",padx=8)
        ttk.Button(b,text="Actualiser ARS / Hub'Eau",command=self.do_ars).pack(side="left")
        ttk.Button(b,text="Préparer toutes les sources",command=self.prepare_all).pack(side="left",padx=8)
        ttk.Button(b,text="Importer valeurs complémentaires",command=self.import_overrides).pack(side="left")

        intro=("La V1 produit un dossier annuel traçable. Le brouillon remplit toutes les valeurs résolues et conserve les éléments réellement manquants dans le préflight. Le mode final est bloqué tant qu'un élément obligatoire reste non résolu.")
        ttk.Label(self.tab_actions,text=intro,wraplength=850,justify="left").pack(anchor="w",pady=(0,18))
        box=ttk.LabelFrame(self.tab_actions,text="Production",padding=16); box.pack(fill="x")
        ttk.Button(box,text="Générer le BROUILLON",command=lambda:self.do_build(False)).grid(row=0,column=0,padx=8,pady=8,sticky="ew")
        ttk.Button(box,text="Générer le RAPPORT FINAL",command=lambda:self.do_build(True)).grid(row=0,column=1,padx=8,pady=8,sticky="ew")
        ttk.Button(box,text="Ouvrir le dossier annuel",command=self.open_output).grid(row=1,column=0,padx=8,pady=8,sticky="ew")
        ttk.Button(box,text="Ouvrir le préflight",command=self.open_preflight).grid(row=1,column=1,padx=8,pady=8,sticky="ew")
        ttk.Button(box,text="Exporter gabarit des valeurs manquantes",command=self.export_missing).grid(row=2,column=0,columnspan=2,padx=8,pady=8,sticky="ew")
        box.columnconfigure(0,weight=1); box.columnconfigure(1,weight=1)
        self.build_info=tk.Text(self.tab_actions,height=16,wrap="word",font=("Consolas",10)); self.build_info.pack(fill="both",expand=True,pady=(16,0))

        ttk.Label(self.tab_maps,text="Les cartes sont encore fournies manuellement jusqu'à l'audit des MXD. L'application les place au bon emplacement du rapport.",wraplength=850).pack(anchor="w",pady=(0,12))
        self.map_rows={}
        for token,label in EXPECTED_MAPS.items():
            fr=ttk.Frame(self.tab_maps); fr.pack(fill="x",pady=5)
            ttk.Label(fr,text=label,width=34).pack(side="left")
            st=ttk.Label(fr,text="Non fournie",width=22); st.pack(side="left",padx=8)
            ttk.Button(fr,text="Choisir l'image…",command=lambda t=token:self.add_map_ui(t)).pack(side="left"); self.map_rows[token]=st

        self.log=tk.Text(self.tab_log,wrap="word",font=("Consolas",10)); self.log.pack(fill="both",expand=True)
        footer=ttk.Frame(self,padding=(12,4,12,10)); footer.pack(fill="x")
        ttk.Label(footer,textvariable=self.status_var).pack(side="left"); ttk.Label(footer,text=f"Projet : {ROOT}").pack(side="right")

    def write_log(self,msg): self.q.put(("log",msg))
    def _poll(self):
        try:
            while True:
                kind,payload=self.q.get_nowait()
                if kind=="log": self.log.insert("end",payload+"\n"); self.log.see("end"); self.status_var.set(payload)
                elif kind=="done": self.status_var.set("Terminé"); self.refresh_status()
                elif kind=="build_summary": self.build_info.delete("1.0","end"); self.build_info.insert("end",payload)
                elif kind=="error": self.status_var.set("Erreur"); messagebox.showerror("Erreur",payload)
        except queue.Empty: pass
        self.after(150,self._poll)
    def task(self,fn):
        def runner():
            try: fn(); self.q.put(("done",None))
            except Exception as e: self.q.put(("error",str(e)))
        threading.Thread(target=runner,daemon=True).start()
    def refresh_status(self):
        y=self.year.get()
        for x in self.tree.get_children(): self.tree.delete(x)
        for s in source_status(y): self.tree.insert("","end",values=(s.label,s.status,s.detail))
        out=year_out(y)/"assets_manual"; from .core import ASSET_FILENAME
        for token,lab in self.map_rows.items(): lab.config(text="OK" if (out/ASSET_FILENAME[token].format(year=y)).exists() else "Non fournie")
    def import_portal(self):
        p=filedialog.askopenfilename(title="Export portail assainissement",filetypes=[("CSV","*.csv"),("Tous les fichiers","*.*")])
        if p: self.task(lambda:import_assainissement_portal(self.year.get(),Path(p),log=self.write_log))
    def add_docs(self):
        ps=filedialog.askopenfilenames(title="RAD / RPQS",filetypes=[("PDF","*.pdf"),("Tous les fichiers","*.*")])
        if not ps:return
        y=self.year.get(); copy_manual_documents(y,[Path(p) for p in ps],log=self.write_log); self.refresh_status(); self.task(lambda:rebuild_local_reports(log=self.write_log))
    def do_ars(self): self.task(lambda:refresh_ars(self.year.get(),log=self.write_log))
    def import_overrides(self):
        p=filedialog.askopenfilename(title="Valeurs complémentaires validées",filetypes=[("CSV","*.csv"),("Tous les fichiers","*.*")])
        if not p:return
        try: import_manual_overrides(self.year.get(),Path(p),log=self.write_log); self.refresh_status(); messagebox.showinfo("Valeurs complémentaires","Fichier importé dans saisie/. Seules les lignes validated=oui sont publiées ; les autres restent « à valider ». Régénère le brouillon pour les voir.")
        except Exception as e: messagebox.showerror("Import impossible",str(e))
    def export_missing(self):
        try: p=export_missing_values_template(self.year.get()); self.write_log(f"Gabarit créé : {p}"); open_path(p)
        except Exception as e: messagebox.showerror("Gabarit impossible",str(e))
    def prepare_all(self):
        y=self.year.get()
        def go(): prepare_all_sources(y,refresh_ars_online=False,log=self.write_log); self.q.put(("log",f"Sources locales {y} préparées. Utilise « Actualiser ARS » pour une collecte en ligne."))
        self.task(go)
    def do_build(self,final):
        y=self.year.get()
        def go():
            r=build_report(y,final=final,log=self.write_log); self.q.put(("log",f"DOCX : {r.docx}"))
            if r.pdf:self.q.put(("log",f"PDF : {r.pdf}"))
            self.q.put(("log",f"Préflight : {r.preflight}")); self.q.put(("build_summary",format_summary(r.summary)))
        self.task(go)
    def open_output(self): p=year_out(self.year.get()); p.mkdir(parents=True,exist_ok=True); open_path(p)
    def open_preflight(self):
        p=year_out(self.year.get())/f"preflight_report_{self.year.get()}.csv"
        if not p.exists(): messagebox.showinfo("Préflight","Génère d'abord un brouillon."); return
        open_path(p)
    def add_map_ui(self,token):
        p=filedialog.askopenfilename(title=EXPECTED_MAPS[token],filetypes=[("Images","*.png;*.jpg;*.jpeg"),("Tous les fichiers","*.*")])
        if p: add_map(self.year.get(),token,Path(p),log=self.write_log); self.refresh_status()

if __name__=="__main__": App().mainloop()
