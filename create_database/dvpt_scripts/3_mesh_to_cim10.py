#!/usr/bin/env python3
# mesh_to_icd10_cm.py
# -----------------------------------------------------------
"""
Pipeline résumé
---------------
1. Charge le dataset « clairedhx/edu3-clinical-fr-mesh-2 »
2. Fusionne mesh_from_gliner ∪ pubmed_mesh, filtre les check-tags
3. Résout chaque UI MeSH unique en codes ICD-10-CM via l’API UMLS :
       UI (MeSH) ▸ CUI ▸ atoms?sabs=ICD10CM ▸ code
   • pool 6 threads
   • cache local JSON
   • sans TGT/ST (clé API seule)
4. Ajoute mesh_clean et icd10_codes, pousse le dataset « -mesh-4 »
"""

import os, json, time, pathlib, requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from datasets import load_dataset, Features, Sequence, Value
from urllib.parse import quote
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from tqdm import tqdm

# ------------------------------------------------------------------ #
# 0. Configuration                                                   #
# ------------------------------------------------------------------ #
load_dotenv()
API_KEY = os.getenv("UMLS_API_KEY")
if not API_KEY:
    raise RuntimeError("UMLS_API_KEY manquant (.env)")

DATASET_IN  = "clairedhx/edu3-clinical-fr-mesh-2"
DATASET_OUT = "clairedhx/edu3-clinical-fr-mesh-4"

CHECKTAGS   = set(json.load(
    open("create_database/data/dictionnaires/mesh_checktags.json")
))

CACHE_PATH  = pathlib.Path(
    "create_database/data/dictionnaires/umls_mesh2icd_cache.json"
)
CACHE = json.loads(CACHE_PATH.read_text()) if CACHE_PATH.exists() else {}

MAX_WORKERS = 6
TIMEOUT     = 20
BASE        = "https://uts-ws.nlm.nih.gov/rest"

# ------------------------------------------------------------------ #
# 1. Session HTTP avec Retry                                         #
# ------------------------------------------------------------------ #
def make_session() -> requests.Session:
    sess = requests.Session()
    retry_cfg = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=False,               # retry GET & POST
    )
    sess.mount("https://", HTTPAdapter(max_retries=retry_cfg))
    return sess

SESSION = make_session()

# ------------------------------------------------------------------ #
# 2. Fonctions auxiliaires UMLS                                       #
# ------------------------------------------------------------------ #
def mesh_ui_to_cui(ui_mesh: str) -> str | None:
    """
    UI MeSH → CUI (premier résultat).
    Retourne None si rien trouvé.
    """
    url = (f"{BASE}/content/current/source/MSH/{quote(ui_mesh)}"
           f"?apiKey={API_KEY}")
    data = SESSION.get(url, timeout=TIMEOUT).json()
    concepts_url = data.get("result", {}).get("concepts")
    if not concepts_url:
        return None

    data2 = SESSION.get(f"{concepts_url}&apiKey={API_KEY}", timeout=TIMEOUT).json()
    results = (data2.get("result") or {}).get("results", [])
    return results[0]["ui"] if results else None


def cui_to_icd10cm(cui: str) -> list[str]:
    """CUI → liste de codes ICD-10-CM (extraction via atoms)."""
    url = (f"{BASE}/content/2025AA/CUI/{cui}"
           f"/atoms?sabs=ICD10CM&pageSize=200&apiKey={API_KEY}")
    atoms = SESSION.get(url, timeout=TIMEOUT).json().get("result", [])
    return sorted({
        a["code"].split("/")[-1]             # …/ICD10CM/I10 → I10
        for a in atoms
        if a.get("rootSource") == "ICD10CM"
    })


def mesh_to_icd10cm(ui_mesh: str) -> list[str]:
    """Résout un UI MeSH unique vers des codes ICD-10-CM (avec cache)."""
    if ui_mesh in CACHE:
        return CACHE[ui_mesh]

    cui = mesh_ui_to_cui(ui_mesh)
    codes = cui_to_icd10cm(cui) if cui else []
    CACHE[ui_mesh] = codes
    return codes

# ------------------------------------------------------------------ #
# 3. Collecte des UI MeSH uniques                                     #
# ------------------------------------------------------------------ #
print("⇢ Chargement du dataset…")
ds = load_dataset(DATASET_IN, split="train")

all_mesh = sorted({
    m
    for ex in ds
    for m in (ex["mesh_from_gliner"] + ex["pubmed_mesh"])
    if m and m not in CHECKTAGS
})
print(f"→ {len(all_mesh)} UI MeSH uniques à mapper")

# ------------------------------------------------------------------ #
# 4. Résolution parallèle (6 threads)                                 #
# ------------------------------------------------------------------ #
print("⇢ Résolution UMLS → ICD-10-CM…")
t0 = time.time()

def worker(ui_mesh):
    return mesh_to_icd10cm(ui_mesh)

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
    for _ in tqdm(as_completed(pool.submit(worker, m) for m in all_mesh),
                  total=len(all_mesh), desc="mapping"):
        pass

print(f"✓ Mapping terminé en {time.time()-t0:.1f} s")

# ------------------------------------------------------------------ #
# 5. Ajout des colonnes au dataset                                    #
# ------------------------------------------------------------------ #
def enrich(example):
    merged = sorted({*example["mesh_from_gliner"], *example["pubmed_mesh"]})
    mesh_clean = [m for m in merged if m not in CHECKTAGS]
    icd_codes  = sorted({c for m in mesh_clean for c in CACHE.get(m, [])})
    example["mesh_clean"]  = mesh_clean
    example["icd10_codes"] = icd_codes
    return example

ds = ds.map(enrich, desc="Ajout des colonnes", num_proc=4)

ds = ds.cast(Features({
    **ds.features,
    "mesh_clean":  Sequence(Value("string")),
    "icd10_codes": Sequence(Value("string")),
}))

# ------------------------------------------------------------------ #
# 6. Sauvegarde cache + push                                          #
# ------------------------------------------------------------------ #
CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
CACHE_PATH.write_text(json.dumps(CACHE, indent=2))
print("✓ Cache mis à jour :", CACHE_PATH)

ds.push_to_hub(
    DATASET_OUT,
    commit_message="mesh_clean + icd10_codes via UMLS atoms (ICD10CM)",
    private=False,
)
print("🚀 Dataset poussé :", DATASET_OUT)
