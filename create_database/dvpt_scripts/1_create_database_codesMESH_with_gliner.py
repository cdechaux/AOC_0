from datasets import load_dataset, DatasetDict, Features, Sequence, Value, ClassLabel
from gliner import GLiNER
from medkit.core.text import TextDocument, Segment, Span 
from medkit.text.ner import SimstringMatcher, SimstringMatcherRule
import json
from pathlib import Path
from huggingface_hub import HfApi

# --- 1. Charger les données (cas cliniques Pubmed) -> Rian
ds = load_dataset("rntc/edu3-clinical-fr", split="train")

# 1bis. filtrer sur la colonne 'document_type'
ds = ds.filter(lambda ex: ex["document_type"] == "Clinical case")
print(len(ds), "cas cliniques conservés")  

# --- 2. Initialiser GLiNER Biomed
gliner_model = GLiNER.from_pretrained("Ihor/gliner-biomed-large-v1.0", device="cuda")
labels = ["disease", "condition", "symptom", "treatment"]

# --- 3. Charger dictionnaire MeSH JSON
with open("create_database/data/dictionnaires/mesh_dict.json", encoding="utf-8") as f:
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
                    "id": entry["id"],  
                    "kb_version": None,
                    "term": None
                }
            ]
        })
        rules.append(rule)
    else:
        print("Ignored entry:", entry)



# --- 4. Creer le matcher Simstring
matcher = SimstringMatcher(
    rules=rules,
    threshold=0.85,
    similarity="jaccard"
)



def extract_entities(example):
    """
    À partir d’un compte-rendu (`example["article_text"]`) :

    1. détection des entités biomédicales via GLiNER ;
    2. normalisation MeSH avec SimstringMatcher ;
    3. construction d’une colonne `detected_entities`
       ▸ chaque entrée = {term, label_gliner, mesh_id}.

    ---------
    Paramètre
    ---------
    example : dict
        Exemple (ligne) du Dataset HF – DOIT contenir la clé « article_text ».

    ---------
    Retour
    ---------
    example : dict
        Même dictionnaire, enrichi de la clé « detected_entities ».
    """

    text = example["article_text"]
    # Reconnaissance d'entités GLiNER 
    entities = gliner_model.predict_entities(text, labels)     #liste de dicts  ══►  [{'start': int, 'end': int, 'label': str}, …]

    # transformation en segments medkit
    segments = []
    for ent in entities:
        seg = Segment(
            label="medical_entity", # doit matcher celui des rules
            spans=[Span(0, len(text[ent["start"]:ent["end"]]))],
            text=text[ent["start"]:ent["end"]],
        )
        segments.append(seg)

    matches = matcher.run(segments)

    found = []
    for seg, ent in zip(matches, entities):          # même index → même entité
        mesh_ids = [
            n.kb_id
            for n in seg.attrs.get(label="NORMALIZATION")
            if n.kb_name == "MeSH"
        ] or [None]

        found.append(
            {
                "term":    seg.text,
                "label":   ent["label"],          # label GLiNER récupéré ici
                "mesh_id": mesh_ids[0],
            }
        )

    example["detected_entities"] = found
    return example




new_ds = ds.map(extract_entities, batched=False, desc="annotating")




# ---5) ajouter la colonne 'mesh_from_gliner' (lise des codes mesh uniques)
def uniq_mesh(example):
    # extrait tous les mesh_id non nuls, enlève les doublons
    mesh_ids = {ent["mesh_id"] for ent in example["detected_entities"] if ent["mesh_id"]}
    example["mesh_from_gliner"] = sorted(mesh_ids)          # liste triée (ou laissez-la en set)
    return example

new_ds = new_ds.map(uniq_mesh, desc="adding mesh_from_gliner")

# --- 5 bis) préciser le schéma de la nouvelle colonne (facultatif mais propre)
new_ds = new_ds.cast(
    Features(
        {**new_ds.features, "mesh_from_gliner": Sequence(Value("string"))}
    )
)

# save to disk et push to hub
new_ds.save_to_disk("create_database/data/local_databases/edu3-clinical-fr+mesh")
api = HfApi()
new_ds.push_to_hub("clairedhx/edu3-clinical-fr-mesh-1", private=True)
