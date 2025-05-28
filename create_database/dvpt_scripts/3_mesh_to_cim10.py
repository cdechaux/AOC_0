#!/usr/bin/env python3
# mesh_to_icd10_umls.py
# -----------------------------------------------------------
"""
• Charge clairedhx/edu3-clinical-fr-mesh-2
• Fusionne MeSH (GLiNER ∪ PubMed) ▸ filtre check-tags
• Résout les codes MeSH uniques ➜ ICD-10-CM via l’API UMLS
  (pool 6 threads + retry + cache JSON)
• Ajoute mesh_clean & icd10_codes, pousse sur le Hub
"""

import os, json, time, pathlib, requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from datasets import load_dataset, Features, Sequence, Value
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from tqdm import tqdm

# ------------------------------------------------------------------ #
# 0. Configuration & .env
# ------------------------------------------------------------------ #
load_dotenv()                                 # lit .env dans le cwd
UMLS_KEY    = os.getenv("UMLS_API_KEY")
if not UMLS_KEY:
    raise RuntimeError("UMLS_API_KEY manquant dans l'environnement ou .env")

DATASET_IN  = "clairedhx/edu3-clinical-fr-mesh-2"
DATASET_OUT = "clairedhx/edu3-clinical-fr-mesh-4"

CHECKTAGS   = set(json.load(
    open("create_database/data/dictionnaires/mesh_checktags.json")
))

CACHE_PATH  = pathlib.Path(
    "create_database/data/dictionnaires/umls_mesh2icd_cache.json"
)
CACHE       = json.loads(CACHE_PATH.read_text()) if CACHE_PATH.exists() else {}

MAX_WORKERS = 6           # 6×60 req/min ≈ quota UMLS
TIMEOUT     = 30          # délai réseau confortable

# ------------------------------------------------------------------ #
# 1. Authentification CAS UMLS
# ------------------------------------------------------------------ #
def get_tgt(api_key: str) -> str:
    resp = requests.post(
        "https://utslogin.nlm.nih.gov/cas/v1/api-key",
        data={"apikey": api_key},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.headers["location"]

def get_st(tgt: str) -> str:
    resp = requests.post(
        tgt,
        data={"service": "http://umlsks.nlm.nih.gov"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.text.strip()

TGT = get_tgt(UMLS_KEY)

# ------------------------------------------------------------------ #
# 2. Session HTTP avec Retry
# ------------------------------------------------------------------ #
def make_session() -> requests.Session:
    s = requests.Session()
    retry_cfg = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=False,          # retry POST aussi
    )
    s.mount("https://", HTTPAdapter(max_retries=retry_cfg))
    return s

# ------------------------------------------------------------------ #
# 3. Fonction de résolution MeSH ➜ ICD-10-CM (thread-safe)
# ------------------------------------------------------------------ #
def mesh_to_icd(mesh_id: str, session: requests.Session, tgt: str) -> list[str]:
    if mesh_id in CACHE:
        return CACHE[mesh_id]

    try:
        st = get_st(tgt)
    except requests.exceptions.RequestException as e:
        print("❗ ST error", mesh_id, e)
        CACHE[mesh_id] = []
        return []

    url = (
        "https://uts-ws.nlm.nih.gov/rest/crosswalk/current/source/"
        f"MSH/{mesh_id}?targetSource=ICD10CM&ticket={st}"
    )
    try:
        resp_json = session.get(url, timeout=TIMEOUT).json()
    except (requests.exceptions.RequestException, ValueError) as e:
        print("❗ Crosswalk error", mesh_id, e)
        CACHE[mesh_id] = []
        return []

    codes = {
        rec.get("targetId", "")
        for rec in resp_json.get("result", [])
        if rec.get("targetId", "").startswith("ICD10CM:")
    }

    clean = sorted(c.split(":", 1)[1] for c in codes if c.startswith("ICD10CM:"))
    CACHE[mesh_id] = clean
    return clean

# ------------------------------------------------------------------ #
# 4. Charger le dataset + collecter les MeSH uniques
# ------------------------------------------------------------------ #
print("⇢ Chargement du dataset…")
ds = load_dataset(DATASET_IN, split="train")

all_mesh = sorted({
    m
    for ex in ds
    for m in (ex["mesh_from_gliner"] + ex["pubmed_mesh"])
    if m and m not in CHECKTAGS
})
print(f"→ {len(all_mesh)} codes MeSH uniques à mapper")

# ------------------------------------------------------------------ #
# 5. Résolution parallèle (pool 6 threads)
# ------------------------------------------------------------------ #
print("⇢ Résolution UMLS…")
session = make_session()
start = time.time()

def worker(mid):                          # petite fonction wrapper
    return mesh_to_icd(mid, session, TGT)

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
    futures = {pool.submit(worker, m): m for m in all_mesh}
    for i, fut in enumerate(as_completed(futures), 1):
        fut.result()                      # exceptions déjà gérées
        if i % (MAX_WORKERS * 10) == 0:   # pause douce: ~60 req/min
            time.sleep(1)

print(f"✓ Mapping terminé en {time.time()-start:.1f} s")

# ------------------------------------------------------------------ #
# 6. Appliquer le mapping au dataset
# ------------------------------------------------------------------ #
def process(example):
    merged = sorted({*example["mesh_from_gliner"], *example["pubmed_mesh"]})
    mesh_clean = [m for m in merged if m not in CHECKTAGS]
    icd_codes = sorted({c for m in mesh_clean for c in CACHE.get(m, [])})
    example["mesh_clean"]  = mesh_clean
    example["icd10_codes"] = icd_codes
    return example

ds = ds.map(process, desc="MeSH → ICD10", num_proc=4)

ds = ds.cast(
    Features({
        **ds.features,
        "mesh_clean":  Sequence(Value("string")),
        "icd10_codes": Sequence(Value("string")),
    })
)

# ------------------------------------------------------------------ #
# 7. Sauvegarde cache + push
# ------------------------------------------------------------------ #
CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
CACHE_PATH.write_text(json.dumps(CACHE, indent=2))
print("✓ Cache sauvegardé :", CACHE_PATH)

ds.push_to_hub(
    DATASET_OUT,
    commit_message="add mesh_clean + icd10_codes via UMLS API (threads)",
    private=False,
)
print("🚀 Dataset poussé sur le Hub :", DATASET_OUT)
