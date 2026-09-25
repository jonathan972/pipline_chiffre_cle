#!/usr/bin/env python3
from __future__ import annotations
import argparse
from application.core import build_report

def main():
    ap=argparse.ArgumentParser(description="Génère le dossier annuel Chiffres clés")
    ap.add_argument("--year",type=int,required=True)
    ap.add_argument("--mode",choices=["draft","final"],default="draft")
    a=ap.parse_args()
    result=build_report(a.year, final=(a.mode=="final"), log=print)
    print(result.docx)
    if result.pdf: print(result.pdf)
    print(result.preflight)
if __name__=="__main__": main()
