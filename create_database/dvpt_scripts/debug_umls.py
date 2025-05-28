#!/usr/bin/env python3
# debug_umls_crosswalk.py
# -----------------------------------------------------------
"""
Usage
-----
    python debug_umls_crosswalk.py <UI_MESH>

Exemple :
    python debug_umls_crosswalk.py D014057
"""

import os, sys, requests, textwrap, pprint, json
from dotenv import load_dotenv

# ------------------------- Config ---------------------------------
load_dotenv()                           # charge .env
APIKEY  = os.getenv("UMLS_API_KEY")
TIMEOUT = 25

if not APIKEY:
    sys.exit("❌  UMLS_API_KEY manquant (env ou .env)")

if len(sys.argv) < 2:
    sys.exit("Usage: python debug_umls_crosswalk.py <UI_MESH>")

UI_MESH = sys.argv[1]

# ------------------------- Auth CAS -------------------------------
def get_tgt():
    r = requests.post(
        "https://utslogin.nlm.nih.gov/cas/v1/api-key",
        data={"apikey": APIKEY},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.headers["location"]

def get_st(tgt):
    r = requests.post(
        tgt,
        data={"service": "http://umlsks.nlm.nih.gov"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.text.strip()

TGT = get_tgt()
print("🔑 TGT OK")

# ------------------ Étape A : UI MeSH ➜ CUI -----------------------
st = get_st(TGT)
url_cui = (f"https://uts-ws.nlm.nih.gov/rest/content/current/source/"
           f"MSH/{UI_MESH}?ticket={st}")
print(f"\n1️⃣  UI ➜ CUI  ({url_cui})")
resp = requests.get(url_cui, timeout=TIMEOUT).json()

concepts = resp.get("result", {}).get("concepts", [])
if not concepts:
    sys.exit("❌  Aucun concept trouvé pour ce MeSH UI")

cui = concepts[0] if isinstance(concepts[0], str) else concepts[0]["ui"]
print("CUI récupéré :", cui)



# ------------------ Étape B : CUI ➜ ICD-10 ------------------------
st = get_st(TGT)
url_xw = (f"https://uts-ws.nlm.nih.gov/rest/crosswalk/current/id/"
          f"{cui}?targetSource=ICD10&ticket={st}")   # « ICD10 » = toutes variantes
print(f"\n2️⃣  CUI ➜ ICD10*  ({url_xw})")
xw = requests.get(url_xw, timeout=TIMEOUT).json()

if "result" not in xw:
    print("Réponse inattendue :")
    pprint.pp(xw)
    sys.exit()

# ------------------ Affichage synthétique -------------------------
print("\nrootSource   targetUi   →   targetName")
print("-" * 60)
for rec in xw["result"]:
    src  = rec.get("rootSource")
    code = rec.get("targetUi")
    name = rec.get("targetName", "")[:50]
    print(f"{src:<10}  {code:<10}  →  {name}")
print("-" * 60)

# ------------------ Bilan compact ---------------------------------
grouped = {}
for rec in xw["result"]:
    grouped.setdefault(rec["rootSource"], set()).add(rec["targetUi"])

print("\nRésumé :")
for src, codes in grouped.items():
    print(f"  {src} : {', '.join(sorted(codes))}")
