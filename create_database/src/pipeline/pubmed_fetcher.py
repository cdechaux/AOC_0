# create_database/src/pipeline/pubmed_fetcher.py
# ------------------------------------------------
from medkit.core import Operation
from medkit.core.text import Segment, Span
from medkit.core.attribute import Attribute   
from medkit.core.text.entity_norm_attribute import EntityNormAttribute

# le même cache global déjà utilisé ailleurs
from create_database.src.pubmed.fetch_mesh import mapping as pmid2mesh  


class PubMedMeshFetcher(Operation):
    """
    Récupère les codes MeSH associés à un PMID (NCBI) et les renvoie
    sous forme de *segments artificiels* label « medical_entity » :
      • texte vide, span (0, 0)  → pas d’ancrage dans le document
      • attr NORMALIZATION  (kb_name='MeSH', id='Dxxxxxx')
      • attr provenance="pubmed"

    Pourquoi des segments ?  Pour que l’étape ICD10Mapper traite
    *exactement* le même type d’entrée que ceux venant du Simstring matcher.
    """

    def __init__(self, output_label: str = "pubmed_mesh"):
        super().__init__(output_label=output_label)

    # ------------------------------------------------------------------
    def run(self, segments: list[Segment]):
        if not segments:
            return []

        pmid = str(segments[0].metadata.get("pmid", ""))
        mesh_ids = pmid2mesh.get(pmid, [])
        out_segments: list[Segment] = []
        for mid in mesh_ids:
            seg = Segment(
                label="medical_entity",
                spans=[Span(0, 0)],           
                text="",
                metadata={"provenance": "pubmed"},
            )
            seg.attrs.add(
                EntityNormAttribute(          
                    kb_name="MeSH",
                    kb_id=mid,                      
                    metadata={"provenance": "pubmed"},
                )
            )
            out_segments.append(seg)
        return out_segments
