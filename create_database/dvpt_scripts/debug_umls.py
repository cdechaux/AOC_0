#!/usr/bin/env python3
import os, sys, json, requests
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("UMLS_API_KEY")
if not KEY:
    sys.exit("UMLS_API_KEY manquant")
if len(sys.argv) < 2:
    sys.exit("Usage: python debug_umls_crosswalk.py <UI_MESH>")

UI = sys.argv[1]
BASE = "https://uts-ws.nlm.nih.gov/rest"
TO   = 25

# -------------------------------------------------- UI -> concepts URL
url1 = f"{BASE}/content/current/source/MSH/{UI}?apiKey={KEY}"
data1 = requests.get(url1, timeout=TO).json()
concepts_url = data1.get("result", {}).get("concepts")
if not concepts_url:
    sys.exit("❌ pas de champ 'concepts'")

concepts_url = f"{concepts_url}?apiKey={KEY}"
print("URL concepts :", concepts_url)

# -------------------------------------------------- GET concepts
data2 = requests.get(concepts_url, timeout=TO).json()
print("\n=== JSON concepts (abrégé) ===")
print(json.dumps(data2, indent=2)[:1200])

# ---------- extraction du CUI quelle que soit la structure ----------
cui = None
if isinstance(data2, list) and data2:
    cui = data2[0] if isinstance(data2[0], str) else data2[0].get("ui")
elif isinstance(data2, dict):
    # nouveau format : {"result":[{...}, {...}]}
    lst = data2.get("result") or data2.get("results") or []
    if lst:
        cui = lst[0] if isinstance(lst[0], str) else lst[0].get("ui")

if not cui or not str(cui).startswith("C"):
    sys.exit("❌ impossible d'extraire un CUI")

print("CUI :", cui)

# -------------------------------------------------- CUI -> ICD10* (toutes variantes)
url3 = f"{BASE}/crosswalk/current/id/{cui}?targetSource=ICD10&apiKey={KEY}"
data3 = requests.get(url3, timeout=TO).json()
print("\n=== JSON crosswalk (abrégé) ===")
print(json.dumps(data3, indent=2)[:1000])

print("\nrootSource   targetUi")
print("-"*25)
for rec in data3.get("result", []):
    print(f"{rec.get('rootSource',''):<10}  {rec.get('targetUi')}")
