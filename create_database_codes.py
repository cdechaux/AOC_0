from datasets import load_dataset, DatasetDict, Features, Sequence, Value, ClassLabel
from gliner import GLiNER
from medkit.core.text import TextDocument, Segment, Span 
from medkit.text.ner import SimstringMatcher, SimstringMatcherRule
import json
from pathlib import Path
from huggingface_hub import HfApi

# --- 1. Charger les données (cas cliniques)
ds = load_dataset("rntc/edu3-clinical-fr", split="train")

# 1bis. filtrer sur la colonne 'document_type'
ds = ds.filter(lambda ex: ex["document_type"] == "Clinical case")
print(len(ds), "cas cliniques conservés")  

# --- 2. Initialiser GLiNER Biomed
gliner_model = GLiNER.from_pretrained("Ihor/gliner-biomed-large-v1.0", device="cuda")
labels = ["disease", "condition", "symptom", "treatment"]

# --- 3. Charger dictionnaire MeSH JSON
with open("mesh_dict.json", encoding="utf-8") as f:
    mesh_dict = json.load(f)

# --- 3 bis. Creer des rules à partir du dictionnaire
rules = []

for entry in mesh_dict:
    if (
        isinstance(entry, dict)
        and entry.get("term", "").strip()
        and "id" in entry
    ):
        rule = SimstringMatcherRule.from_dict({
            "term": entry["term"],
            "label": "medical_entity",
            "case_sensitive": False,
            "unicode_sensitive": False,
            "normalizations": [
                {
                    "kb_name": "MeSH",
                    "id": entry["id"],           # ✅ bien 'id'
                    "kb_version": None,
                    "term": None
                }
            ]
        })
        rules.append(rule)
    else:
        print("⚠️ Ignored entry:", entry)




matcher = SimstringMatcher(
    rules=rules,
    threshold=0.85,
    similarity="jaccard"
)



def extract_entities(example):
    text = example["article_text"]
    entities = gliner_model.predict_entities(text, labels)      # ← vos entités GLiNER

    # ------------------ transformation en segments ---------------------------
    segments = []
    for ent in entities:
        seg = Segment(
            label="medical_entity",
            spans=[Span(0, len(text[ent["start"]:ent["end"]]))],
            text=text[ent["start"]:ent["end"]],
        )
        segments.append(seg)

    matches = matcher.run(segments)

    found = []
    for m in matches:
        mesh_ids = [
            norm.kb_id
            for norm in m.attrs.get(label="NORMALIZATION")
            if norm.kb_name == "MeSH"
        ] or [None]                           # pour avoir au moins un élément
        found.append(
            {
                "term":   m.text,
                "label":  ent["label"],       # re‐utilisez le label GLiNER
                "mesh_id": mesh_ids[0],       # premier id (ou None)
            }
        )

    example["detected_entities"] = found
    return example




new_ds = ds.map(extract_entities, batched=False, desc="annotating")
new_ds.save_to_disk("edu3-clinical-fr+mesh")




# 4) ajouter la colonne 'mesh_from_gliner'
def uniq_mesh(example):
    # extrait tous les mesh_id non nuls, enlève les doublons
    mesh_ids = {ent["mesh_id"] for ent in example["detected_entities"] if ent["mesh_id"]}
    example["mesh_from_gliner"] = sorted(mesh_ids)          # liste triée (ou laissez-la en set)
    return example

new_ds = new_ds.map(uniq_mesh, desc="adding mesh_from_gliner")

# 4 bis) préciser le schéma de la nouvelle colonne (facultatif mais propre)
new_ds = new_ds.cast(
    Features(
        {**ds.features, "mesh_from_gliner": Sequence(Value("string"))}
    )
)




api = HfApi()
new_ds.push_to_hub("votre-compte/edu3-clinical-fr-mesh", private=True)
