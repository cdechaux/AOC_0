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
        # 1) construire le document
        doc = TextDocument(
            text=ex["article_text"],
            metadata={"pmid": str(ex["article_id"])}
        )
        doc.raw_segment.metadata["pmid"] = str(ex["article_id"])

        # 2) exécuter le pipeline
        doc_pipe.run([doc])

        # ---------- ICD-10 trace (inchangé) ----------
        trace = {}
        for seg in doc.anns:
            for icd_attr in seg.attrs.get(label="ICD10CM"):
                code = icd_attr.value
                meta = trace.setdefault(
                    code,
                    {
                        "cui":        icd_attr.metadata["cui"],
                        "mesh_id":    icd_attr.metadata["mesh_id"],
                        "provenance": set(),
                    },
                )
                meta["provenance"].add(icd_attr.metadata["provenance"])

        for meta in trace.values():
            p = meta["provenance"]
            meta["provenance"] = "both" if len(p) == 2 else next(iter(p))
        ex["icd10_trace"] = json.dumps(trace, ensure_ascii=False)

        # ---------- parcourir les segments ----------
        gliner_mesh   = set()
        pubmed_mesh   = set()
        icd_codes     = set()
        detected      = []

        for seg in doc.anns:
            if seg.label != "medical_entity":
                continue

            if "mesh_norm" in seg.keys:       # ⇦ segments GLiNER uniquement
                # -- GLiNER label
                gl_label_attr = seg.attrs.get(label="gliner_label")
                gl_label = gl_label_attr[0].value if gl_label_attr else None

                # -- MeSH
                mesh_ids = [n.kb_id for n in seg.attrs.get(label="NORMALIZATION")
                            if n.kb_name == "MeSH"]
                mesh_id  = mesh_ids[0] if mesh_ids else None

                detected.append(
                    {"term": seg.text, "label": gl_label, "mesh_id": mesh_id}
                )
                if mesh_id:
                    gliner_mesh.add(mesh_id)

            elif "pubmed_mesh" in seg.keys:
                # MeSH provenant de PubMed (pas ajouté à detected_entities)
                for norm in seg.attrs.get(label="NORMALIZATION"):
                    if norm.kb_name == "MeSH":
                        pubmed_mesh.add(norm.kb_id)

            # -- ICD-10
            for icd_attr in seg.attrs.get(label="ICD10CM"):
                icd_codes.add(icd_attr.value)

        # ---------- colonnes dataset ----------
        ex["detected_entities"] = detected
        ex["mesh_from_gliner"]  = sorted(gliner_mesh)
        ex["pubmed_mesh"]       = sorted(pubmed_mesh)
        ex["union_mesh"]        = sorted(gliner_mesh | pubmed_mesh)
        ex["inter_mesh"]        = sorted(gliner_mesh & pubmed_mesh)
        ex["icd10_codes"]       = sorted(icd_codes)
        return ex

    ds = ds.map(medkit_map, desc="pipeline medkit")



    # ------------------------------------------------------------------ #
    # 4. Schéma + push                                                   #
    # ------------------------------------------------------------------ #
    ds = ds.cast(Features({
        **ds.features,
        "mesh_from_gliner":  Sequence(Value("string")),
        "pubmed_mesh":       Sequence(Value("string")),
        "union_mesh":  Sequence(Value("string")),
        "inter_mesh":  Sequence(Value("string")),
        "icd10_codes":       Sequence(Value("string")),
        "icd10_trace":     Value("string"),
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
