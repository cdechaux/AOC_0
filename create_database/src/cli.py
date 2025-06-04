#!/usr/bin/env python3
# src/cli.py
import os, typer, datasets, json
from dotenv import load_dotenv
from datasets import Features, Sequence, Value, load_dataset
from huggingface_hub import HfApi
from create_database.src.pipeline.build_pipeline import get_doc_pipeline
from create_database.src.pubmed.fetch_mesh import fetch_batch, mapping as pmid2mesh
from medkit.core.text import TextDocument

# ------------------------------------------------------------------ #
# 1. Build command                                                   #
# ------------------------------------------------------------------ #
def build(push: bool = True):
    load_dotenv()

    # 1-a  HuggingFace dataset (cas cliniques)
    ds = load_dataset("rntc/edu3-clinical-fr", split="train")
    ds = ds.filter(lambda x: x["document_type"] == "Clinical case")

    if os.getenv("DEBUG10"):
        ds = ds.select(range(5))
        print("DEBUG : 10 documents seulement")

    # ------------------------------------------------------------------ #
    # 2. Pipeline Medkit (GLiNER + MeSH + ICD-10-CM)
    # ------------------------------------------------------------------ #
    doc_pipe = get_doc_pipeline(device="cuda")   # build_pipeline renvoie déjà DocPipeline

    def medkit_map(ex):
        # -------- document Medkit + exécution pipeline --------
        doc = TextDocument(text=ex["article_text"])
        d_out = doc_pipe.run([doc])
        print("→ pipeline outputs :", d_out) # d_out["mesh_norm"] devrait contenir 12 segments
        print("len(doc.anns) :", len(doc.anns))
        for step in doc_pipe.pipeline.steps:
            print(step.operation, "→", step.output_keys) 
        detected = []          # [{term,label,mesh_id}]
        mesh_codes = set()
        icd_codes  = set()
        trace = {}             # code → {cui, mesh_id, provenance}
        print("doc.anns :", doc.anns)
        for seg in doc.anns:
            print("seg :", seg)
            if seg.label != "medical_entity":
                continue

            # ------ label GLiNER ----------------------------------------
            gl_attr  = seg.attrs.get(label="gliner_label")
            gl_label = gl_attr[0].value if gl_attr else None

            # ------ MeSH -----------------------------------------------
            mesh_ids = [
                n.kb_id for n in seg.attrs.get(label="NORMALIZATION")
                if n.kb_name == "MeSH"
            ]
            mesh_id = mesh_ids[0] if mesh_ids else None
            print("mesh_ids ;", mesh_ids)
            detected.append({
                "term": seg.text,
                "label": gl_label,
                "mesh_id": mesh_id,
            })
            if mesh_id:
                mesh_codes.add(mesh_id)

            # ------ ICD-10-CM ------------------------------------------
            for icd in seg.attrs.get(label="ICD10CM"):
                code = icd.value            # ex : 'I10'
                icd_codes.add(code)

                # fusionne provenance si plusieurs occurrences
                meta = trace.setdefault(code, {
                    "cui":        icd.metadata["cui"],
                    "mesh_id":    icd.metadata["mesh_id"],
                    "provenance": set(),   # on agrège puis stringify
                })
                meta["provenance"].add(icd.metadata["provenance"])

        # ---------- colonnes ajoutées ----------
        ex["detected_entities"] = detected
        ex["mesh_from_gliner"]  = sorted(mesh_codes)
        ex["icd10_codes"]       = sorted(icd_codes)

        # provenance → str (« gliner », « pubmed », « both »)
        for info in trace.values():
            prov = info["provenance"]
            info["provenance"] = (
                "both" if len(prov) == 2 else next(iter(prov))
            )
        ex["icd10_trace"] = json.dumps(trace, ensure_ascii=False)   # ← string
        return ex

    ds = ds.map(medkit_map, desc="pipeline medkit")

    # ------------------------------------------------------------------ #
    # 3. MeSH PubMed (colonne pubmed_mesh)                               #
    # ------------------------------------------------------------------ #
    pmids = [str(p) for p in ds["article_id"] if p]
    for chunk in [pmids[i:i+100] for i in range(0, len(pmids), 100)]:
        fetch_batch(chunk)                       # remplit le cache global
    ds = ds.map(lambda e: {
        **e, "pubmed_mesh": pmid2mesh.get(str(e["article_id"]), [])
    })

    # ------------------------------------------------------------------ #
    # 4. Déclaration du schéma + push HF                                 #
    # ------------------------------------------------------------------ #
    ds = ds.cast(Features({
        **ds.features,
        "mesh_from_gliner": Sequence(Value("string")),
        "icd10_codes":      Sequence(Value("string")),
        "pubmed_mesh":      Sequence(Value("string")),
    }))

    if push:
        api = HfApi(token=os.getenv("HF_TOKEN"))
        ds.push_to_hub(
            "clairedhx/edu3-clinical-fr-mesh-5",
            commit_message="GLiNER + MeSH + ICD-10-CM + trace",
            private=False,
        )

# -------------------------------------------------------------- #
if __name__ == "__main__":
    typer.run(build)
