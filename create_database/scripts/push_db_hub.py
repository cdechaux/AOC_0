from datasets import load_from_disk, Features, Sequence, Value
from huggingface_hub import HfApi

local_path = "create_database/local_databases/edu3-clinical-fr+mesh"
repo_id    = "clairedhx/edu3-clinical-fr-mesh"   # dépôt public

# 1) recharger le jeu sauvegardé
ds = load_from_disk(local_path)                  # split unique « train »


# 3) pousser sur le Hub
ds.push_to_hub(repo_id, private=False)
