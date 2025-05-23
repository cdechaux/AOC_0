from datasets import load_from_disk
from huggingface_hub import HfApi

local_path = "edu3-clinical-fr+mesh"
repo_id    = "clairedhx/edu3-clinical-fr-mesh"   # adaptez

# a) recharger le dataset
ds = load_from_disk(local_path)                     # split unique « train »

# b) push_to_hub (envoie le dataset et crée automatiquement la carte README)
ds.push_to_hub(repo_id, private=False)               # private=False pour public
