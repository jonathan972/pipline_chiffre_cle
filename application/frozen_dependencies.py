"""Dépendances des scripts chargés dynamiquement, déclarées pour PyInstaller.

Les modules métier (pipeline/, modules/*) sont copiés à côté de l'EXE et
chargés à l'exécution : PyInstaller ne voit pas leurs imports. Il analyse en
revanche le bytecode de cette fonction, jamais appelée, et embarque donc ces
modules dans l'exécutable.
"""


def _declare() -> None:  # pragma: no cover - jamais exécutée
    import argparse, collections, hashlib, math, unicodedata, uuid  # noqa: F401,E401
    import urllib.parse, urllib.request, xml.etree.ElementTree  # noqa: F401,E401
    import docx, docx.enum.text, docx.oxml, docx.shared  # noqa: F401,E401
    import matplotlib, matplotlib.pyplot, matplotlib.backends.backend_agg  # noqa: F401,E401
    import fitz  # noqa: F401
