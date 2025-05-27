#!/usr/bin/env python3
# merge_mesh_umls_api.py
import requests, time, json, pathlib
from datasets import load_dataset, Features, Sequence, Value

REPO     = "clairedhx/edu3-clinical-fr-mesh-2"
CHECKTGS = set(json.load(open("create_database/data/dictionnaires/mesh_checktags.json")))
UMLS_APIKEY = "YOUR_UMLS_APIKEY_HERE"

# ----------------------------- Auth helper ----------------------------------
def get_tgt(api_key):
    r = requests.post(
        "https://utslogin.nlm.nih.gov/cas/v1/api-key",
        data={"apikey": api_key},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    return r.headers["location"]

def get_st(tgt):
    r = requests.post(
        tgt,
        data={"service": "http://umlsks.nlm.nih.gov"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    return r.text

TGT = get_tgt(UMLS_APIKEY)

# ---------------------- UMLS cross-walk with simple cache -------------------
CACHE_PATH = pathlib.Path("umls_mesh2icd_cache.json")
CACHE = json.loads(CACHE_PATH.read_text()) if CACHE_PATH.exists() else {}

def mesh_to_icd(mesh_id):
    if mesh_id in CACHE:
        return CACHE[mesh_id]

    st = get_st(TGT)
    url = (
        f"https://uts-ws.nlm.nih.gov/rest/crosswalk/current/source/"
        f"MSH/{mesh_id}?targetSource=ICD10CM&ticket={st}"
    )
    resp = requests.get(url, timeout=15).json()
    codes = {
        d["targetId"]                      # ex. "ICD10CM:C83.10"
        for d in resp["result"]
        if d["targetId"].startswith("ICD10CM:")
    }
    clean_codes = sorted(c.split(":", 1)[1] for c in codes)  # C83.10
    CACHE[mesh_id] = clean_codes
    return clean_codes

# --------------------- Fusion + filtre + mapping dans map() -----------------
def process(example):
    merged = sorted({*example["mesh_from_gliner"], *example["pubmed_mesh"]})
    mesh_clean = [m for m in merged if m not in CHECKTGS]

    icd = sorted({c for m in mesh_clean for c in mesh_to_icd(m)})
    example["mesh_clean"]  = mesh_clean
    example["icd10_codes"] = icd
    return example

# --------------------- Charger, traiter, sauvegarder ------------------------
ds = load_dataset(REPO, split="train")
ds = ds.map(process, desc="UMLS crosswalk", batched=False)

# enregistrer le cache pour les prochains runs
CACHE_PATH.write_text(json.dumps(CACHE, indent=2))

# typage des nouvelles colonnes
ds = ds.cast(Features({
    **ds.features,
    "mesh_clean":  Sequence(Value("string")),
    "icd10_codes": Sequence(Value("string")),
}))

ds.push_to_hub("clairedhx/edu3-clinical-fr-mesh-3",
               commit_message="add mesh_clean + icd10_codes via UMLS API",
               private=False)
