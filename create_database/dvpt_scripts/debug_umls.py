#!/usr/bin/env python3
# debug_umls_crosswalk.py
"""
Usage : python debug_umls_crosswalk.py <Mesh_UI>
Exemple: python debug_umls_crosswalk.py D014057
          (Tomography, X-Ray Computed)
Le script :
  1) charge .env, vérifie UMLS_API_KEY
  2) demande un TGT puis un ST
  3) appelle /crosswalk et affiche le JSON brut
  4) isole targetUi et affiche le résultat final
"""

import os, sys, json, requests, pprint, textwrap
from dotenv import load_dotenv

# ---------------- 0. Pré-requis ------------------------------------------------
load_dotenv()
APIKEY = os.getenv("UMLS_API_KEY")
if not APIKEY:
    sys.exit("❌  UMLS_API_KEY manquant dans .env ou variables d’environnement")

if len(sys.argv) < 2:
    sys.exit("Usage: python debug_umls_crosswalk.py <Mesh_UI>")

MESH_UI = sys.argv[1]

TIMEOUT = 30

# ---------------- 1. TGT -------------------------------------------------------
print("🔑 Obtention TGT…")
tgt_resp = requests.post(
    "https://utslogin.nlm.nih.gov/cas/v1/api-key",
    data={"apikey": APIKEY},
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    timeout=TIMEOUT,
)

print("Status:", tgt_resp.status_code)
if tgt_resp.status_code != 201:
    print(tgt_resp.text[:500])
    sys.exit("❌  Impossible d’obtenir un TGT")

TGT = tgt_resp.headers["location"]
print("TGT =", TGT)

# ---------------- 2. ST --------------------------------------------------------
print("\n🎫 Obtention ST…")
st_resp = requests.post(
    TGT,
    data={"service": "http://umlsks.nlm.nih.gov"},
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    timeout=TIMEOUT,
)
print("Status:", st_resp.status_code)
ST = st_resp.text.strip()
print("ST =", ST)

# ---------------- 3. Crosswalk -------------------------------------------------
url = (
    "https://uts-ws.nlm.nih.gov/rest/crosswalk/current/source/"
    f"MSH/{MESH_UI}?targetSource=ICD10CM&ticket={ST}"
)
print("\n🌐 Requête Crosswalk :")
print(url)

x_resp = requests.get(url, timeout=TIMEOUT)
print("Status:", x_resp.status_code)

try:
    data = x_resp.json()
except ValueError:
    print(textwrap.shorten(x_resp.text, 500))
    sys.exit("❌  Réponse non JSON")

print("\nJSON brut :")
pprint.pp(data, depth=3, compact=True)

# ---------------- 4. Extraction des codes -------------------------------------
codes = {
    rec.get("targetUi", "")
    for rec in data.get("result", [])
    if rec.get("targetUi")            # non vide
}

print("\nCodes ICD10CM extraits :", codes or "— aucun —")
