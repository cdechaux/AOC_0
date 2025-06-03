#!/usr/bin/env python3
# debug_mesh_icd10cm.py
"""
Usage
-----
    python debug_mesh_icd10cm.py <UI_MESH>

Exemple
-------
    python debug_mesh_icd10cm.py D006973       # Hypertension
"""

import os, sys, json, requests
from urllib.parse import quote
from dotenv import load_dotenv

# ------------------------------------------------------------------ #
# 0. Lecture clé API + argument
# ------------------------------------------------------------------ #
load_dotenv()
API_KEY = os.getenv("UMLS_API_KEY")
if not API_KEY:
    sys.exit("UMLS_API_KEY manquant (.env ou variables d’environnement)")

if len(sys.argv) < 2:
    sys.exit("Usage: python debug_mesh_icd10cm.py <UI_MESH>")

UI_MESH = sys.argv[1]
BASE    = "https://uts-ws.nlm.nih.gov/rest"
TIMEOUT = 25

# ------------------------------------------------------------------ #
# 1. UI MeSH ▸ URL 'concepts'
# ------------------------------------------------------------------ #
url1 = f"{BASE}/content/current/source/MSH/{quote(UI_MESH)}?apiKey={API_KEY}"
data1 = requests.get(url1, timeout=TIMEOUT).json()
concepts_url = data1.get("result", {}).get("concepts")
if not concepts_url:
    sys.exit("❌ champ 'concepts' introuvable dans la réponse MeSH")

concepts_url += f"&apiKey={API_KEY}"
print("→ URL concepts :", concepts_url)

# ------------------------------------------------------------------ #
# 2. concepts URL ▸ extraction du premier CUI
# ------------------------------------------------------------------ #
data2 = requests.get(concepts_url, timeout=TIMEOUT).json()

results = (data2.get("result") or {}).get("results", [])
if not results:
    sys.exit("❌ aucun résultat dans 'results'")

CUI = results[0]["ui"]
print("→ CUI détecté :", CUI)

# ------------------------------------------------------------------ #
# 3. CUI ▸ codes ICD-10-CM via *atoms*
# ------------------------------------------------------------------ #
atoms_url = (
    f"{BASE}/content/2025AA/CUI/{CUI}"
    f"/atoms?sabs=ICD10CM&pageSize=200&apiKey={API_KEY}"
)
print("→ URL atoms  :", atoms_url)

atoms = requests.get(atoms_url, timeout=TIMEOUT).json().get("result", [])
codes_icd10cm = {
    a["code"].split("/")[-1]               # …/ICD10CM/I10 → I10
    for a in atoms
    if a.get("rootSource") == "ICD10CM"
}

# ------------------------------------------------------------------ #
# 4. Affichage
# ------------------------------------------------------------------ #
print("\n===== RÉSUMÉ =====")
print(f"UI MeSH  : {UI_MESH}")
print(f"CUI      : {CUI}")
print(f"ICD-10-CM: {sorted(codes_icd10cm) or '— aucun —'}")
