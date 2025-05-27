import typer, os, datasets
from dotenv import load_dotenv
from huggingface_hub import HfApi
from create_database.src.pipeline.build_pipeline import get_doc_pipeline
from pubmed.fetch_mesh import fetch_batch, mapping as pmid2mesh

app = typer.Typer()

@app.command()
def build(push: bool = True):
    load_dotenv()

    # 1. HF dataset
    ds = datasets.load_dataset("rntc/edu3-clinical-fr", split="train")
    ds = ds.filter(lambda x: x["document_type"] == "Clinical case")

    # 2. Medkit pipeline
    pipe = get_doc_pipeline(device="cuda")
    def medkit_map(ex):
        doc = datasets.Features({"text": datasets.Value("string")}).encode_example(
            {"text": ex["article_text"]})
        pipe.run([doc])
        codes = {norm.kb_id for seg in doc.anns
                 for norm in seg.attrs.get(label="NORMALIZATION")}
        ex["mesh_from_gliner"] = sorted(codes)
        return ex
    ds = ds.map(medkit_map)

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
    app()
