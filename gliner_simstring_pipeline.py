from datasets import load_dataset
from gliner import GLiNER
from medkit.core.text import TextDocument, Segment, Span 
from medkit.text.ner import SimstringMatcher, SimstringMatcherRule
import json
from pathlib import Path

# --- 1. Charger les données (cas cliniques)
dataset = load_dataset("rntc/edu3-clinical-fr", split="train")
cas_cliniques = [ex for ex in dataset if ex["document_type"] == "Clinical case"]

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


# --- 4. Pipeline : GLiNER → SimStringMatcher (via Medkit)
for i, ex in enumerate(cas_cliniques[:5]):  # ⚠️ Limité à 5 pour test
    text = ex["article_text"]
    print(f"\n=== Cas clinique #{i + 1} ===\nTexte: {text[:200]}...")

    entities = gliner_model.predict_entities(text, labels)

    for ent in entities:
        ent_text = text[ent["start"]:ent["end"]]

        # 1) document “bidon” (facultatif si vous ne l’utilisez pas ensuite)
        doc = TextDocument(text=ent_text, uid=f"ent_{i}")

        # 2) construire le Segment
        seg = Segment(
            label=ent["label"],
            spans=[Span(0, len(ent_text))],  # positions dans le (sous-)texte
            text=ent_text,
        )

        # 3) l’enregistrer dans le conteneur d’annotations
        doc.anns.add(seg)

        # 4) passer ce Segment au SimstringMatcher
        matches = matcher.run([seg])
        print(matches)
        if matches:
            mesh_ids = [
                norm.kb_id
                for m in matches
                for norm in m.attrs.get(label="normalization")
                if norm.kb_name == "MeSH"
            ]
            print(f" - {ent['label']} → «{ent_text}» → {', '.join(mesh_ids)}")
        else:
            print(f" - {ent['label']} → «{ent_text}» → —")
