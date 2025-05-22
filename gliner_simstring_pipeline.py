from datasets import load_dataset
from gliner import GLiNER
from medkit.core.text import TextDocument
from medkit.text.ner import SimstringMatcher, SimstringMatcherRule
import json

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
    if entry["term"].strip():
        rule = SimstringMatcherRule.from_dict({
            "term": entry["term"],
            "label": "medical_entity",
            "case_sensitive": False,
            "unicode_sensitive": False,
            "normalizations": [
                {
                    "kb_name": "MeSH",
                    "kb_id": entry["id"],
                    "kb_version": None,  # Ajouté pour éviter l’erreur
                    "term": None
                }
            ]
        })
        rules.append(rule)

simstring_db_path = Path("simstring_mesh.db")
rules_db_path = Path("rules_mesh.db")

build_simstring_matcher_databases(
    simstring_db_file=simstring_db_path,
    rules_db_file=rules_db_path,
    rules=rules
)


matcher = SimstringMatcher(
    simstring_db_file=simstring_db_path,
    rules_db_file=rules_db_path,
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
        # Créer un faux document Medkit avec 1 annotation (nécessaire pour SimStringMatcher)
        doc = TextDocument(text=ent_text, id=f"ent_{i}_{ent_text}")
        ann = doc.anns.new_label(label=ent["label"], span=(0, len(ent_text)), text=ent_text)
        match = matcher.run([ann])

        print(f" - {ent['label']} → « {ent_text} » → {match[0].data['id'] if match else '—'}")
