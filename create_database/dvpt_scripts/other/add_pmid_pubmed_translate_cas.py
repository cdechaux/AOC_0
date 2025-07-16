from datasets import load_dataset, Dataset
from tqdm import tqdm

# Étape 1 : Chargement des datasets
print("🔄 Chargement des jeux de données...")
pubmed_big_all = load_dataset("rntc/pubmed-comm", split="train", streaming=True)
pubmed_big = [row for row in pubmed_big_all if row["document_type"] == "Clinical Case"]
ds = Dataset.from_list(pubmed_big)
ds.push_to_hub("clairedhx/pubmed-comm-clinical-cases")

pubmed_small = load_dataset("rntc/clinical-pubmed-translate", split="train")

# Étape 2 : Création de l’index {text -> id}
print("🔍 Indexation du petit dataset...")
target_texts = set(row["text"] for row in pubmed_small)
text_to_id = {}

for row in tqdm(ds, desc="Indexation filtrée"):
    if row["text"] in target_texts:
        text_to_id[row["text"]] = row["id"]
        if len(text_to_id) >= len(target_texts):  # Early stop
            break

# Étape 3 : Ajout des IDs correspondants au petit dataset
print("📌 Ajout des IDs correspondants...")
enriched_rows = []
for row in tqdm(pubmed_small, desc="Enrichissement"):
    match_id = text_to_id.get(row["text"])
    new_row = dict(row)
    new_row["pubmed_comm_id"] = match_id  # peut être None si non trouvé
    enriched_rows.append(new_row)

# Étape 4 : Création d’un nouveau dataset
enriched_dataset = Dataset.from_list(enriched_rows)

# Étape 5 : Push vers Hugging Face
print("🚀 Push vers le hub HF...")
enriched_dataset.push_to_hub("clairedhx/clinical-pubmed-translate-with-id")

print("✅ Fini ! Nouveau dataset en ligne.")
