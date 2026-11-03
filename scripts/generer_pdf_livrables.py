"""Convertit les livrables Markdown de docs/ en PDF (diagrammes Mermaid dessinés, charte CIAT VISION).

Prérequis (environnement Python séparé de l'application) :
    pip install markdown playwright
    (navigateur : Microsoft Edge installé, ou « playwright install chromium » puis CANAL = None)
Usage, depuis la racine du projet :
    python scripts/generer_pdf_livrables.py
Les PDF sont écrits dans docs/pdf/. Une connexion Internet est nécessaire pour dessiner les diagrammes Mermaid.
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright

RACINE = Path(__file__).resolve().parent.parent
DOCS = RACINE / "docs"
SORTIE = DOCS / "pdf"
CANAL = "msedge"
LOGO = RACINE / "frontend" / "public" / "logo" / "logo-complet.png"
MERMAID = "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"

LIVRABLES = [
    ("01_cahier_des_charges.md", "Cahier des charges"),
    ("02_architecture.md", "Architecture et diagrammes UML"),
    ("03_base_de_donnees.md", "Base de données et dictionnaire des données"),
    ("04_maquettes.md", "Maquettes des interfaces"),
    ("05_tests_et_anomalies.md", "Tests, anomalies et corrections"),
    ("06_guide_installation.md", "Guide d'installation et de déploiement"),
    ("07_guide_utilisateur.md", "Guide utilisateur"),
    ("08_rapport.md", "Rapport de projet"),
    ("09_scenario_video.md", "Scénario de la vidéo de démonstration"),
    ("journal_des_prompts.md", "Journal des prompts"),
]

CSS = """
@page { size: A4; margin: 18mm 16mm 18mm 16mm; }
* { box-sizing: border-box; }
body { font-family: "Inter", "Segoe UI", Arial, sans-serif; color: #2B211B; font-size: 10.5pt; line-height: 1.5; }
h1 { color: #362316; font-size: 20pt; border-bottom: 3px solid #CA9871; padding-bottom: 6px; margin-top: 0; }
h2 { color: #4C311F; font-size: 14pt; margin-top: 22px; break-after: avoid; }
h3 { color: #4C311F; font-size: 12pt; margin-top: 16px; break-after: avoid; }
h4 { color: #4C311F; break-after: avoid; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 12px; font-size: 9pt; break-inside: auto; }
tr { break-inside: avoid; }
th { background: #4C311F; color: #fff; text-align: left; padding: 5px 6px; }
td { border-bottom: 1px solid #E8E1DA; padding: 4px 6px; vertical-align: top; }
tr:nth-child(even) td { background: #FAF6F1; }
code { font-family: Consolas, monospace; font-size: 8.8pt; background: #F5F5F5; padding: 1px 3px; border-radius: 3px; }
pre { background: #F5F5F5; border: 1px solid #E8E1DA; border-radius: 6px; padding: 8px 10px; white-space: pre-wrap;
      font-size: 8.5pt; break-inside: avoid; }
pre code { background: none; padding: 0; }
h1 code, h2 code, h3 code { font-size: inherit; background: #FAF6F1; }
blockquote { border-left: 4px solid #CA9871; background: #FAF6F1; margin: 10px 0; padding: 6px 12px; }
img { max-width: 100%; height: auto; border: 1px solid #E8E1DA; border-radius: 4px; }
td img { max-height: 210mm; }
.mermaid { text-align: center; break-inside: avoid; margin: 10px 0; }
.couverture { height: 245mm; display: flex; flex-direction: column; justify-content: space-between; break-after: page; }
.couverture .bande { background: #4C311F; color: #fff; padding: 18px 22px; border-radius: 8px; }
.couverture .bande b { color: #CA9871; }
.couverture h1 { border: none; font-size: 28pt; margin: 0; }
.couverture .sous { font-size: 14pt; color: #6B625B; }
.couverture .bas { color: #6B625B; font-size: 10pt; }
.couverture img.logo { width: 120mm; border: none; margin: 0 auto; display: block; }
"""


def convertir(md_text: str) -> str:
    # Les blocs ```mermaid deviennent des <div class="mermaid"> dessinés par mermaid.js
    blocs: list[str] = []

    def garder(m: re.Match) -> str:
        blocs.append(m.group(1))
        return f"\n\nMERMAIDBLOC{len(blocs) - 1}\n\n"

    md_text = re.sub(r"```mermaid\n(.*?)```", garder, md_text, flags=re.S)
    html = markdown.markdown(md_text, extensions=["tables", "fenced_code", "sane_lists"])
    for i, b in enumerate(blocs):
        html = html.replace(f"<p>MERMAIDBLOC{i}</p>", f'<div class="mermaid">{b}</div>')
    return html


def page_html(titre: str, corps: str) -> str:
    couverture = f"""<section class="couverture">
      <div class="bande"><b>CIAT VISION</b> · Le pilotage intelligent de l'innovation par la donnée</div>
      <img class="logo" src="{LOGO.as_uri()}" alt="CIAT VISION">
      <div><p class="sous">Plateforme intelligente de pilotage et d'analyse décisionnelle du CIAT</p>
        <h1>{titre}</h1></div>
      <div class="bas">ISEP Amadou Trawaré de Diamniadio · Centre d'Innovation, d'Application et de Transfert<br>
        Évaluation pratique en intelligence artificielle générative · Projet 3 · document généré le
        {date.today():%d/%m/%Y}</div></section>"""
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>{titre}</title>
      <base href="{DOCS.as_uri()}/"><style>{CSS}</style>
      <script src="{MERMAID}"></script></head><body>{couverture}{corps}
      <script>window.mermaid && mermaid.initialize({{ startOnLoad: false, theme: "base", themeVariables: {{
        primaryColor: "#FAF6F1", primaryBorderColor: "#4C311F", primaryTextColor: "#2B211B", lineColor: "#6B625B",
        fontFamily: "Segoe UI, Arial" }} }});
      window.rendu = window.mermaid ? mermaid.run({{ querySelector: ".mermaid" }}).then(() => true) : Promise.resolve(false);
      </script></body></html>"""


def main() -> None:
    SORTIE.mkdir(exist_ok=True)
    with sync_playwright() as p:
        nav = p.chromium.launch(channel=CANAL) if CANAL else p.chromium.launch()
        page = nav.new_page()
        for fichier, titre in LIVRABLES:
            source = DOCS / fichier
            if not source.exists():
                print("absent :", fichier)
                continue
            tmp = DOCS / f".tmp_{source.stem}.html"
            tmp.write_text(page_html(titre, convertir(source.read_text(encoding="utf-8"))), encoding="utf-8")
            page.goto(tmp.as_uri())
            mermaid_ok = page.evaluate("window.rendu")
            page.wait_for_load_state("networkidle")
            cible = SORTIE / f"{source.stem}.pdf"
            page.pdf(path=str(cible), format="A4", print_background=True, display_header_footer=True,
                     header_template="<span></span>",
                     footer_template='<div style="font-size:8px;width:100%;text-align:center;color:#6B625B">'
                                     f'CIAT VISION · {titre} · page <span class="pageNumber"></span> / '
                                     '<span class="totalPages"></span></div>',
                     margin={"top": "16mm", "bottom": "16mm", "left": "14mm", "right": "14mm"})
            tmp.unlink()
            print(f"{cible.name}  (diagrammes : {'dessinés' if mermaid_ok else 'texte brut, Mermaid indisponible'})")
        nav.close()


if __name__ == "__main__":
    sys.exit(main())
