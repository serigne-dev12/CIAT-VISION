"""Prépare les versions du logo officiel à partir de docs/logo/ciat_vision_logo_original.png.

- Fond blanc rendu TRANSPARENT (seulement le fond relié aux bords : les blancs intérieurs du logo sont conservés).
- Bords adoucis conservés, couleurs décontaminées (pas de liseré blanc).
- Versions par simple recadrage : aucune déformation, aucune recoloration.

Prérequis : pip install pillow numpy      Usage : python scripts/preparer_logo.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

RACINE = Path(__file__).resolve().parent.parent
ORIGINAL = RACINE / "docs" / "logo" / "ciat_vision_logo_original.png"
SEUIL_TRANSPARENT = 243  # au-dessus : fond entièrement transparent (le fond de l'original vaut 253-254)
SEUIL_OPAQUE = 200       # en dessous : pixel du logo entièrement opaque


def transparent(chemin: Path) -> Image.Image:
    rgb = np.asarray(Image.open(chemin).convert("RGB")).astype(float)
    mn = rgb.min(axis=2)
    # .copy() indispensable : fromarray partage la mémoire du tableau et floodfill ne la modifierait pas
    masque = Image.fromarray(((mn >= SEUIL_OPAQUE) * 255).astype("uint8")).copy()
    h, w = mn.shape
    for x, y in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
        if masque.getpixel((x, y)) == 255:
            ImageDraw.floodfill(masque, (x, y), 128)
    fond = np.asarray(masque) == 128
    alpha = np.ones_like(mn)
    alpha[fond] = np.clip((SEUIL_TRANSPARENT - mn[fond]) / (SEUIL_TRANSPARENT - SEUIL_OPAQUE), 0, 1)
    a = alpha[..., None]
    couleur = np.clip(np.where(a > 0, (rgb - (1 - a) * 255) / np.maximum(a, 1e-6), 0), 0, 255)
    return Image.fromarray(np.dstack([couleur, alpha * 255]).astype("uint8"), "RGBA")


def rogner(im: Image.Image, marge: int) -> Image.Image:
    al = np.asarray(im)[..., 3]
    ys, xs = np.where(al > 10)
    return im.crop((max(xs.min() - marge, 0), max(ys.min() - marge, 0),
                    min(xs.max() + marge + 1, im.width), min(ys.max() + marge + 1, im.height)))


def enregistrer(im: Image.Image, chemin: Path, largeur: int) -> None:
    if im.width > largeur:
        im = im.resize((largeur, round(im.height * largeur / im.width)), Image.LANCZOS)  # proportions conservées
    chemin.parent.mkdir(parents=True, exist_ok=True)
    im.save(chemin, optimize=True)
    print(f"{chemin.relative_to(RACINE)}  {im.size}")


def main() -> None:
    img = transparent(ORIGINAL)
    alpha = np.asarray(img)[..., 3]
    print(f"Fond transparent : {(alpha == 0).mean():.0%} des pixels ; semi-transparents (bords) : "
          f"{((alpha > 0) & (alpha < 255)).mean():.1%}")
    enregistrer(img, RACINE / "docs" / "logo" / "ciat_vision_logo_transparent.png", 4000)
    # Zones de l'original (1774 × 887) : emblème | séparateur | « CIAT VISION » ; ligne « ISEP AMADOU TRAWARÉ » dessous
    complet = rogner(img.crop((100, 100, 1670, 745)), 8)
    horizontal = rogner(img.crop((100, 100, 1670, 662)), 6)
    embleme = rogner(img.crop((100, 100, 745, 662)), 4)
    cote = max(embleme.size)
    carre = Image.new("RGBA", (cote, cote), (0, 0, 0, 0))
    carre.paste(embleme, ((cote - embleme.width) // 2, (cote - embleme.height) // 2))
    logos = RACINE / "frontend" / "public" / "logo"
    enregistrer(complet, logos / "logo-complet.png", 1200)
    enregistrer(horizontal, logos / "logo-horizontal.png", 900)
    enregistrer(carre, logos / "logo-compact.png", 256)
    enregistrer(carre.copy(), logos / "favicon.png", 64)
    enregistrer(complet.copy(), RACINE / "backend" / "app" / "assets" / "logo.png", 1000)


if __name__ == "__main__":
    main()
