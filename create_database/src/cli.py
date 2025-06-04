#!/usr/bin/env python3
# ──────────────────────────────────────────────────────────────
# src/cli.py   –   build + push du jeu de données enrichi
# ──────────────────────────────────────────────────────────────
import os
import json
import typer
from dotenv import load_dotenv
from datasets import load_dataset, Features, Sequence, Value
from huggingface_hub import HfApi
from medkit.core.text import TextDocument

# pipeline complet (GLiNER ▸ MeSH ▸ PubMed ▸ ICD-10-CM)
from create_database.src.pipeline.build_pipeline import get_doc_pipeline

from create_database.src.pubmed.fetch_mesh import mapping as pmid2mesh  
from create_database.src.pubmed.fetch_mesh import fetch_batch

# ──────────────────────────────────────────────────────────────
# build()
# ──────────────────────────────────────────────────────────────
def build(push: bool = True):
    load_dotenv()
    ds = load_dataset("rntc/edu3-clinical-fr", split="train")
    ds = ds.filter(lambda x: x["document_type"] == "Clinical case")

    if os.getenv("DEBUG10"):
        ds = ds.select(range(5))
        print("DEBUG : 5 documents seulement")

    doc_pipe = get_doc_pipeline(device="cuda")   # ← le pipeline ci-dessus

    # ------------------------------------------------------------------ #
    # mapping Medkit ➜ colonnes du dataset
    # ------------------------------------------------------------------ #
    def medkit_map(ex):
        doc = TextDocument(text=ex["article_text"],
                           metadata={"pmid": str(ex["article_id"])})
        doc.raw_segment.metadata["pmid"] = str(ex["article_id"])
        # -- run pipeline
        doc_pipe.run([doc])

        # -------------- trace ICD10 ------------------------------------
        trace: dict[str, dict] = {}
        for seg in doc.anns:
            for icd_attr in seg.attrs.get(label="ICD10CM"):
                code = icd_attr.value
                meta = trace.setdefault(code, {
                    "cui":        icd_attr.metadata["cui"],
                    "mesh_id":    icd_attr.metadata["mesh_id"],
                    "provenance": set(),
                })
                meta["provenance"].add(icd_attr.metadata["provenance"])

        # convertir l’ensemble → chaîne
        for meta in trace.values():
            p = meta["provenance"]
            meta["provenance"] = "both" if len(p) == 2 else next(iter(p))

        ex["icd10_trace"] = json.dumps(trace, ensure_ascii=False)

        # -------------- parcourir les segments -------------------------
        mesh_codes = set()
        icd_codes  = set()
        detected   = []

        for seg in doc.anns:
            if seg.label != "medical_entity":
                continue

            # GLiNER label
            gl_label_attr = seg.attrs.get(label="gliner_label")
            gl_label = gl_label_attr[0].value if gl_label_attr else None

            # codes MeSH (0..n)
            mesh_ids = [n.kb_id for n in seg.attrs.get(label="NORMALIZATION")
                        if n.kb_name == "MeSH"]
            mesh_id  = mesh_ids[0] if mesh_ids else None

            detected.append(
                {"term": seg.text, "label": gl_label, "mesh_id": mesh_id}
            )
            if mesh_id:
                mesh_codes.add(mesh_id)

            # codes ICD-10 CM (ajoutés par ICD10Mapper)
            for icd_attr in seg.attrs.get(label="ICD10CM"):
                icd_codes.add(icd_attr.value)

        ex["detected_entities"] = detected
        ex["mesh_from_gliner"]  = sorted(mesh_codes)
        ex["icd10_codes"]       = sorted(icd_codes)
        return ex

    ds = ds.map(medkit_map, desc="pipeline medkit")

    # ------------------------------------------------------------------ #
    # 3. Récupération des MeSH PubMed  +  union / inter                  #
    # ------------------------------------------------------------------ #
    pmids = [str(p) for p in ds["article_id"] if p]
    for chunk in [pmids[i:i + 100] for i in range(0, len(pmids), 100)]:
        fetch_batch(chunk)                       # remplit le cache global

    # 3-a  ajouter la colonne « pubmed_mesh »
    ds = ds.map(lambda e: {
        **e, "pubmed_mesh": pmid2mesh.get(str(e["article_id"]), [])
    })

    # 3-b  calculer union / intersection
    def add_union_inter(example):
        m_gliner = set(example["mesh_from_gliner"])
        m_pubmed = set(example["pubmed_mesh"])

        example["union_codes_mesh"] = sorted(m_gliner | m_pubmed)
        example["inter_codes_mesh"] = sorted(m_gliner & m_pubmed)
        return example

    ds = ds.map(add_union_inter, desc="union / intersection MeSH")

    # ------------------------------------------------------------------ #
    # 4. Schéma + push                                                   #
    # ------------------------------------------------------------------ #
    ds = ds.cast(Features({
        **ds.features,
        "mesh_from_gliner":  Sequence(Value("string")),
        "pubmed_mesh":       Sequence(Value("string")),
        "union_codes_mesh":  Sequence(Value("string")),
        "inter_codes_mesh":  Sequence(Value("string")),
        "icd10_codes":       Sequence(Value("string")),
    }))

    if push:
        api = HfApi(token=os.getenv("HF_TOKEN"))
        ds.push_to_hub(
            "clairedhx/edu3-clinical-fr-mesh-5",
            commit_message="GLiNER + MeSH + ICD-10-CM + trace",
            private=False,
        )

# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    typer.run(build)
