from datasets import load_dataset
from medkit.text.ner import GLiNER
from medkit.text.link import SimStringMatcher
from medkit.core.text import TextDocument
import json

# --- Étape 1 : Charger les cas cliniques depuis Hugging Face
dataset = load_dataset("rntc/edu3-clinical-fr", split="train")
cas_cliniques = [ex for ex in dataset if ex["document_type"] == "Clinical case"]

# --- Étape 2 : Initialiser GLiNER Biomed
ner = GLiNER(model="BMDKL/GLiNER-biomedical", device="cpu")  # utilise "cuda" si GPU dispo

# --- Étape 3 : Charger le dictionnaire MeSH (JSON formaté type SimString)
with open("mesh_dict.json", encoding="utf-8") as f:
    mesh_dict = json.load(f)

linker = SimStringMatcher(dict_entries=mesh_dict, threshold=0.85)
rint("ok")
# --- Étape 4 : Traitement des textes
for i, ex in enumerate(cas_cliniques[:10]):  # limite à 10 pour test
    text = ex["article_text"]
    doc = TextDocument(text=text, id=f"doc_{i}")

    # NER : extraction d'entités
    ents = ner.run([doc])
    doc.anns.ner_anns = ents

    # Linking : associer les entités à MeSH
    links = linker.run(ents)

    print(f"\n=== Cas clinique #{i + 1} ===")
    print(f"Texte : {text[:200]}...")  # aperçu
    for ent, match in zip(ents, links):
        print(f" - {ent.label} : '{ent.text}' → {match[0].data['id'] if match else '—'}")

