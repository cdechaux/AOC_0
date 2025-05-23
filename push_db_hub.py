from datasets import load_from_disk, Features, Sequence, Value
from huggingface_hub import HfApi

local_path = "edu3-clinical-fr+mesh"
repo_id    = "clairedhx/edu3-clinical-fr-mesh"   # dépôt public

# 1) recharger le jeu sauvegardé
ds = load_from_disk(local_path)                  # split unique « train »

# 2) ajouter la colonne 'mesh_from_gliner'
def uniq_mesh(example):
    # extrait tous les mesh_id non nuls, enlève les doublons
    mesh_ids = {ent["mesh_id"] for ent in example["detected_entities"] if ent["mesh_id"]}
    example["mesh_from_gliner"] = sorted(mesh_ids)          # liste triée (ou laissez-la en set)
    return example

ds = ds.map(uniq_mesh, desc="adding mesh_from_gliner")

# 2 bis) préciser le schéma de la nouvelle colonne (facultatif mais propre)
ds = ds.cast(
    Features(
        {**ds.features, "mesh_from_gliner": Sequence(Value("string"))}
    )
)

# 3) pousser sur le Hub
ds.push_to_hub(repo_id, private=False)
