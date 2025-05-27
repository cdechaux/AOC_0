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
        Parameters
        ----------
        segments : list[Segment]
            Segments précédemment générés par le détecteur (label
            `medical_entity`).

        Returns
        -------
        list[Segment]
            La même liste, mais chaque segment peut se voir ajouter
            un attr `"normalization"` (kb_name="MeSH", kb_id="D...").
        """
        # Le matcher modifie les segments in-place et les renvoie.
        return self._matcher.run(segments)      # type: ignore


# pour un import direct:  from pipeline.mesh_normalizer import MeshNormalizer
__all__ = ["MeshNormalizer"]
