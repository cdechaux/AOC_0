# create_database/src/utils.py
# ------------------------------------------------
"""
Utilitaires partagés :
    • chargement du dictionnaire MeSH JSON
    • fabrication d’un SimstringMatcher prêt à l’emploi
"""

from pathlib import Path
import json
from medkit.text.ner import SimstringMatcher, SimstringMatcherRule


# chemin par défaut : create_database/data/mesh_dict.json
_DEFAULT_MESH_DICT = (
    Path(__file__).resolve().parents[2] / "create_database" / "data" / "dictionnaires" / "mesh_dict.json"
)


def load_mesh_dict(path: str | Path = _DEFAULT_MESH_DICT) -> list[dict]:
    """
    Charge le JSON contenant les couples {term, id}.

    Parameters
    ----------
    path : str or Path
        Emplacement du fichier mesh_dict.json.

    Returns
    -------
    list[dict]
        Liste des entrées valides.
    """
    with Path(path).expanduser().open(encoding="utf-8") as f:
        return json.load(f)


def load_simstring_matcher(
    path: str | Path = _DEFAULT_MESH_DICT,
    threshold: float = 0.85,
    similarity: str = "jaccard",
) -> SimstringMatcher:
    """
    Construit un SimstringMatcher alimenté par le dictionnaire MeSH.

    Parameters
    ----------
    path : str or Path, optional
        Fichier JSON {term, id}.  Défaut : _DEFAULT_MESH_DICT
    threshold : float
        Seuil de similarité (Simstring). 0.85 recommandé pour Jaccard.
    similarity : str
        'jaccard' ou 'cosine'.

    Returns
    -------
    SimstringMatcher
        Matcher prêt à être utilisé par l’opération MeshNormalizer.
    """
    mesh_dict = load_mesh_dict(path)

    rules = [
        SimstringMatcherRule.from_dict(
            {
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
                ],
            }
        )
        for entry in mesh_dict
        if entry.get("term") and entry.get("id")
    ]

    return SimstringMatcher(
        rules=rules,
        threshold=threshold,
        similarity=similarity,
    )


__all__ = ["load_mesh_dict", "load_simstring_matcher"]
