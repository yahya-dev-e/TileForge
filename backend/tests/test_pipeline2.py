"""
Script de préparation du dataset de test (Étape 1 & 2 du document).

Ce script :
1. Copie les tuiles sélectionnées depuis les packs Kenney téléchargés
2. Les renomme selon une convention claire (catégorie + numéro)
3. Les redimensionne en 256x256 avec interpolation nearest-neighbor
   (pour garder les pixels nets, sans flou)
4. Les enregistre dans backend/test_data/raw/

USAGE :
1. Modifie les deux variables PLATFORMER_DIR et ROGUELIKE_DIR ci-dessous
   pour qu'elles pointent vers TES dossiers "Tiles" téléchargés.
2. Modifie OUTPUT_DIR si besoin (chemin vers ton repo backend/test_data/raw)
3. Lance : python prepare_test_data.py
"""

import os
import shutil
import cv2

# ============================================================
# 1. CONFIGURATION - À ADAPTER À TON ORDINATEUR
# ============================================================

# Chemin vers le dossier "Tiles" du pack Pixel Platformer
# Exemple Windows : r"C:\Users\TonNom\Downloads\kenney_pixel-platformer\Tiles"
PLATFORMER_DIR = r"C:\Users\TonNom\Downloads\kenney_pixel-platformer\Tiles"

# Chemin vers le dossier "Tiles" du pack Roguelike
# Exemple Windows : r"C:\Users\TonNom\Downloads\kenney_roguelike\Tiles"
ROGUELIKE_DIR = r"C:\Users\TonNom\Downloads\kenney_roguelike\Tiles"

# Dossier de sortie (dans ton repo)
OUTPUT_DIR = r"C:\chemin\vers\ton\repo\backend\test_data\raw"

# Taille finale souhaitée (256x256 recommandé par le document)
TARGET_SIZE = 256

# ============================================================
# 2. SÉLECTION DES TUILES PAR CATÉGORIE
# ============================================================
# Format : (nom_fichier_source, dossier_source, nouveau_nom)

SELECTION = [
    # --- Sol plat (5 tuiles) - test du wrapping horizontal seamless ---
    ("tile_0100.png", PLATFORMER_DIR, "ground_flat_01.png"),
    ("tile_0101.png", PLATFORMER_DIR, "ground_flat_02.png"),
    ("tile_0102.png", PLATFORMER_DIR, "ground_flat_03.png"),
    ("tile_0103.png", PLATFORMER_DIR, "ground_flat_04.png"),
    ("tile_0104.png", PLATFORMER_DIR, "ground_flat_05.png"),

    # --- Organique / irrégulier (5 tuiles) - test extraction de contours ---
    ("tile_0112.png", PLATFORMER_DIR, "organic_slope_01.png"),
    ("tile_0125.png", PLATFORMER_DIR, "organic_slope_02.png"),
    ("tile_0126.png", PLATFORMER_DIR, "organic_slope_03.png"),
    ("tile_0128.png", PLATFORMER_DIR, "organic_slope_04.png"),
    ("tile_0129.png", PLATFORMER_DIR, "organic_slope_05.png"),

    # --- Texturé / rugueux (5 tuiles) - test du normal map baker (Sobel) ---
    ("tile_0127.png", ROGUELIKE_DIR, "rough_texture_01.png"),
    ("tile_0142.png", ROGUELIKE_DIR, "rough_texture_02.png"),
    ("tile_0143.png", ROGUELIKE_DIR, "rough_texture_03.png"),
    ("tile_0158.png", ROGUELIKE_DIR, "rough_texture_04.png"),
    ("tile_0159.png", ROGUELIKE_DIR, "rough_texture_05.png"),

    # --- Flottant / à trous (2 tuiles) - test des cas limites ---
    ("tile_0028.png", PLATFORMER_DIR, "floating_debris_01.png"),
    ("tile_0067.png", PLATFORMER_DIR, "floating_debris_02.png"),
]

# ============================================================
# 3. TRAITEMENT
# ============================================================

def process_tile(src_name, src_dir, dst_name):
    src_path = os.path.join(src_dir, src_name)
    dst_path = os.path.join(OUTPUT_DIR, dst_name)

    if not os.path.isfile(src_path):
        print(f"  [MANQUANT] {src_path} introuvable, ignoré.")
        return False

    # Lecture avec canal alpha préservé (RGBA)
    img = cv2.imread(src_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"  [ERREUR] Impossible de lire {src_path}")
        return False

    # Ajoute un canal alpha si l'image n'en a pas (ex: JPEG ou PNG sans transparence)
    if img.shape[2] == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)

    # Redimensionnement nearest-neighbor pour garder les pixels nets
    resized = cv2.resize(
        img,
        (TARGET_SIZE, TARGET_SIZE),
        interpolation=cv2.INTER_NEAREST,
    )

    cv2.imwrite(dst_path, resized)
    print(f"  [OK] {src_name} -> {dst_name} ({resized.shape[1]}x{resized.shape[0]})")
    return True


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Sortie : {OUTPUT_DIR}\n")

    success, failed = 0, 0
    for src_name, src_dir, dst_name in SELECTION:
        ok = process_tile(src_name, src_dir, dst_name)
        success += ok
        failed += not ok

    print(f"\nTerminé : {success} tuile(s) traitée(s), {failed} échec(s).")
    if failed:
        print("-> Vérifie les chemins PLATFORMER_DIR / ROGUELIKE_DIR et les noms de fichiers.")


if __name__ == "__main__":
    main()
