# create_database/src/pipeline/mesh_normalizer.py
# ------------------------------------------------
from medkit.core import Operation
from medkit.core.text import Segment
from medkit.text.ner import SimstringMatcher


class MeshNormalizer(Operation):
    """
    Opération Medkit qui applique un `SimstringMatcher` afin d'ajouter
    aux segments d'entrée un attribut `normalization`
    (type `EntityNormAttribute`) contenant le/des codes MeSH correspondants.

    Paramètres
    ----------
    matcher : SimstringMatcher
        Instance déjà paramétrée avec ses rules MeSH.
    output_label : str, default="normalized"
        Clé produite dans le pipeline pour identifier la sortie.
        (Concrètement, on renvoie les mêmes segments enrichis.)
    """

    def __init__(self, matcher: SimstringMatcher, output_label: str = "normalized"):
        super().__init__(output_label=output_label)
        self._matcher = matcher

    # ------------------------------------------------------------------
    # L'API Operation s'attend à ce que `run()` reçoive *une liste* pour
    # chaque input key, et retourne une liste ou None.
    # ------------------------------------------------------------------
    def run(self, segments: list[Segment]):
        """
        Ajoute les codes MeSH **et** recopie les attributs GLiNER
        (gliner_label) sur les nouveaux segments.
        """
        out = self._matcher.run(segments)           # nouveaux segments

        # copie tous les attributs du segment source vers sa sortie jumelle
        for src, dst in zip(segments, out):
            for attr in src.attrs:
                dst.attrs.add(attr.copy())

        return out   # type: ignore


# pour un import direct:  from pipeline.mesh_normalizer import MeshNormalizer
__all__ = ["MeshNormalizer"]
