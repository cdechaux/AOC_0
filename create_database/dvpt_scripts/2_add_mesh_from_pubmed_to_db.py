#!/usr/bin/env python3
# coding: utf-8
"""
Enrichit edu3-clinical-fr+mesh avec les MeSH headings récupérés
depuis PubMed (eUtils) → nouvelle colonne "pubmed_mesh".
"""

from datasets import load_from_disk, Features, Sequence, Value
import os, time, requests, xml.etree.ElementTree as ET
from tqdm import tqdm

LOCAL_DS_DIR = "create_database/data/local_databases/edu3-clinical-fr+mesh"
BATCH_SIZE   = 100          # nb de PMIDs par appel EFetch (max = 200)
API_KEY      = os.getenv("NCBI_API_KEY")  # facultatif, ↑ quota à 10 req/s
SLEEP        = 0.34 if API_KEY else 0.4   # délai pour rester < 3 req/s


# 1. Dataset local
ds = load_from_disk(LOCAL_DS_DIR)


# 2. Fonction : récupérer les MeSH pour un lot de PMIDs (100)
def fetch_mesh_for_pmids(pmids):
    """
    Retourne un dict {pmid: [mesh_id, ...]}  (list vide si rien/erreur)
    """
    ids = ",".join(pmids)
    url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        "?db=pubmed"
        f"&id={ids}"
        "&retmode=xml"
    )
    if API_KEY:
        url += f"&api_key={API_KEY}"

    for _try in range(3):              # petit retry 3×
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            break
        time.sleep(1.5)
    else:
        # échec → liste vide pour tous
        return {pid: [] for pid in pmids}

    out = {}
    root = ET.fromstring(resp.text)
    for art in root.findall(".//PubmedArticle"):
        pmid = art.findtext(".//MedlineCitation/PMID").strip()
        mesh_codes = [
            mh.get("UI") for mh in art.findall(".//MeshHeadingList/MeshHeading/DescriptorName")
            if mh is not None and mh.get("UI")
        ]
        out[pmid] = sorted(set(mesh_codes))

    # pmids non revenus (embargo, rétractation, etc.)
    for pid in pmids:
        out.setdefault(pid, [])

    return out


# 3. Build mapping {pmid: [mesh...]}  avec cache en RAM
pmids_all = list({str(p) for p in ds["article_id"] if p})  # unique, str
pmid2mesh = {}

print("Téléchargement des MeSH headings depuis PubMed …")
for i in tqdm(range(0, len(pmids_all), BATCH_SIZE)):
    chunk = pmids_all[i : i + BATCH_SIZE]
    pmid2mesh.update(fetch_mesh_for_pmids(chunk))
    time.sleep(SLEEP)  # respecte le rate NCBI


# 4. Ajout de la colonne au dataset
def add_pubmed_mesh(example):
    example["pubmed_mesh"] = pmid2mesh.get(str(example["article_id"]), [])
    return example

ds = ds.map(add_pubmed_mesh, desc="Ajout colonne pubmed_mesh")

# déclare proprement le schéma (facultatif mais recommandé)
ds = ds.cast(
    Features({**ds.features, "pubmed_mesh": Sequence(Value("string"))})
)


# 5. Sauvegarde locale & push optionnel --------------------------------------

# écrase / crée le dossier local
ds.save_to_disk(LOCAL_DS_DIR+"-2")            

# push vers le Hub 
#    (suppose hugggingface-cli login déjà fait)
ds.push_to_hub("clairedhx/edu3-clinical-fr-mesh-2", commit_message="add pubmed_mesh")
print("✅ Colonne pubmed_mesh ajoutée et dataset ré-enregistré.")
