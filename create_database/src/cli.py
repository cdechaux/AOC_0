import typer, os, datasets
from dotenv import load_dotenv
from datasets import Features, Sequence, Value, load_dataset
from huggingface_hub import HfApi
from create_database.src.pipeline.build_pipeline import get_doc_pipeline
from create_database.src.pubmed.fetch_mesh import fetch_batch, mapping as pmid2mesh
from medkit.core.text import TextDocument

def build(push: bool = True):
    load_dotenv()

    # 1. HF dataset
    ds = datasets.load_dataset("rntc/edu3-clinical-fr", split="train")
    ds = ds.filter(lambda x: x["document_type"] == "Clinical case")

    if os.getenv("DEBUG10"):          # ex. DEBUG10=1 python -m create_database.src.cli pour tester sur les 10 premieres lignes seulement
        ds = ds.select(range(10))
        print("DEBUG mode : 10 docs")

    # 2. Medkit pipeline
    doc_pipe = get_doc_pipeline(device="cuda")
    def medkit_map(ex):
        # --- document Medkit
        doc = TextDocument(text=ex["article_text"])
        doc_pipe.run([doc])                    # exécute le pipeline

        detected = []
        for seg in doc.anns:
            if seg.label != "medical_entity":
                continue

            # label GLiNER
            gl_attr  = seg.attrs.get(label="gliner_label")
            gl_label = gl_attr[0].value if gl_attr else None

            # premier code MeSH (s'il existe)
            mesh_ids = [
                n.kb_id
                for n in seg.attrs.get(label="NORMALIZATION")
                if n.kb_name == "MeSH"
            ]
            mesh_id = mesh_ids[0] if mesh_ids else None

            detected.append({
                "term": seg.text,
                "label": gl_label,
                "mesh_id": mesh_id,
            })

        # nouvelle colonne 1 : liste détaillée
        ex["detected_entities"] = detected

        # nouvelle colonne 2 : set unique des codes
        ex["mesh_from_gliner"] = sorted({
            d["mesh_id"] for d in detected if d["mesh_id"]
        })
        return ex
    ds = ds.map(medkit_map, desc="pipeline medkit")


    # 3. PubMed MeSH
    pmids = [str(p) for p in ds["article_id"] if p]
    for chunk in [pmids[i:i+100] for i in range(0, len(pmids), 100)]:
        fetch_batch(chunk)                   # remplit pmid2mesh cache
    ds = ds.map(lambda e: {**e, "pubmed_mesh": pmid2mesh.get(str(e["article_id"]), [])})

    # 4. push
    if push:
        api = HfApi(token=os.getenv("HF_TOKEN"))
        ds.push_to_hub("clairedhx/edu3-clinical-fr-mesh-3",
                       commit_message="pipeline medkit + pubmed")

if __name__ == "__main__":
    typer.run(build)   
