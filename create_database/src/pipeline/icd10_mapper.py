# create_database/src/pipeline/icd10_mapper.py
# ──────────────────────────────────────────────────────────────
"""Ajout d’attributs ICD-10-CM sur les segments déjà normalisés MeSH.

Entrée  : la liste des segments `mesh_norm` (issus de GLiNER + PubMed).
Sortie  : aucune (les attributs sont ajoutés in-place).
Trace   : un attr document‐level ``icd10_trace`` (JSON).
"""

from __future__ import annotations
import json
import pathlib
from collections import defaultdict
from typing import List, Dict

from medkit.core import Operation
from medkit.core.text import Segment
from medkit.core.attribute import Attribute   

# --------------------------------------------------------------------------- #
# 1)  chemins et cache                                                        #
# --------------------------------------------------------------------------- #
_CACHE_PATH = pathlib.Path(
    "create_database/data/dictionnaires/umls_mesh2icd_cache.json"
)  # produit par mesh_to_icd10_umls.py


class ICD10Mapper(Operation):
    """Mappe MeSH → ICD-10-CM et ajoute les attributs « ICD10CM »."""

    def __init__(self, cache_path: pathlib.Path | str = _CACHE_PATH):
        super().__init__(output_label=None)  # rien en sortie
        cache_path = pathlib.Path(cache_path)

        if not cache_path.is_file():
            raise FileNotFoundError(
                f"Fichier cache MeSH→ICD10 introuvable : {cache_path}"
            )

        cache: Dict[str, List[str]] = json.loads(cache_path.read_text())
        # ex. {"D006973": ["I10"], …}

        self._mesh2codes: dict[str, list[str]] = cache
        # si vous avez aussi un mapping MeSH→CUI, chargez-le ici
        self._mesh2cui: dict[str, str | None] = defaultdict(lambda: None)

    # ------------------------------------------------------------------ #
    # 2) helper (MeSH ⇒ liste d’Attribute ICD10CM)                       #
    # ------------------------------------------------------------------ #
    def _build_attrs(self, mesh_id: str) -> list[Attribute]:
        """Un attr `ICD10CM` par code lié au MeSH."""
        attrs: list[Attribute] = []
        cui = self._mesh2cui.get(mesh_id)          # None si non connu
        for code in self._mesh2codes.get(mesh_id, []):
            attrs.append(
                Attribute(
                    label="ICD10CM",
                    value=code,
                    metadata={
                        "cui": cui,
                        "mesh_id": mesh_id,
                        # « provenance » ajouté plus tard
                    },
                )
            )
        return attrs
    
    # ------------------------------------------------------------------
    # 2.1  helper public : liste → liste
    # ------------------------------------------------------------------
    def map_mesh_ids(self, mesh_ids: list[str]) -> list[Attribute]:
        """
        Convertit une liste de MeSH UI en une liste plate d’`Attribute`
        ICD-10-CM (un attribut par code).  S’appuie sur _build_attrs().
        """
        attrs: list[Attribute] = []
        for mid in mesh_ids:
            attrs.extend(self._build_attrs(mid))
        return attrs

    # ------------------------------------------------------------------ #
    # 3) run() — ajout in-place sur les segments                         #
    # ------------------------------------------------------------------ #
    def run(
        self,
        mesh_segments: list[Segment],            # segments issus du Simstring
        pubmed_segments: list[Segment] | None = None  # segments ajoutés par PubMedMeshFetcher
    ):
        pubmed_segments = pubmed_segments or []      # peut être None si pas de step amont

        # 1) – provenance des codes MeSH
        prov_map: dict[str, set[str]] = {}
        for seg in mesh_segments:
            for norm in seg.attrs.get(label="NORMALIZATION"):
                if norm.kb_name == "MeSH":
                    prov_map.setdefault(norm.kb_id, set()).add("gliner")

        for seg in pubmed_segments:
            for norm in seg.attrs.get(label="NORMALIZATION"):
                if norm.kb_name == "MeSH":
                    prov_map.setdefault(norm.kb_id, set()).add("pubmed")

        print(prov_map)
        union_mesh = list(prov_map)

        # 2) – mapping MeSH → ICD-10-CM
        attrs = self.map_mesh_ids(union_mesh)

        # 3) – enrichir les métadonnées + pousser sur tous les segments MeSH
        trace = {}
        for attr in attrs:
            mid = attr.metadata["mesh_id"]
            provenance = prov_map[mid]
            attr.metadata["provenance"] = (
                "both" if len(provenance) == 2 else next(iter(provenance))
            )

            trace.setdefault(attr.value, {
                "cui":       attr.metadata["cui"],
                "mesh_id":   mid,
                "provenance": attr.metadata["provenance"],
            })

            # ➜ ajouter l’attribut seulement sur les annotations portant CE MeSH
            for ann in mesh_segments + pubmed_segments:        # union des deux listes
                for norm in ann.attrs.get(label="NORMALIZATION"):
                    if norm.kb_name == "MeSH" and norm.kb_id == mid:
                        ann.attrs.add(attr.copy())
                        break  

        
        return []
