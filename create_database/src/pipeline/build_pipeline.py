from medkit.core.pipeline import Pipeline, PipelineStep
from medkit.core.doc_pipeline import DocPipeline
from .gliner_detector import GlinerDetector
from .mesh_normalizer import MeshNormalizer
from ..utils import load_simstring_matcher   # charge votre SimstringMatcher


def get_pipeline(device: str = "cpu") -> Pipeline:
    """
    Construit le graphe d’opérations GLiNER ➜ Simstring/MeSH.

    Retourne un objet `Pipeline` (méta-données + steps) :
      • input_key  : "raw_segment"  (segment par défaut créé par TextDocument)
      • output_key : "normalized"   (segments enrichis avec attr MeSH)
    """
    det  = GlinerDetector(
        labels=["disease", "condition", "symptom", "treatment"],
        device=device,
    )
    norm = MeshNormalizer(load_simstring_matcher())

    steps = [
        PipelineStep(
            operation=det,
            input_keys=["raw_segment"],    # segment racine du document
            output_keys=["gliner_out"],
        ),
        PipelineStep(
            operation=norm,
            input_keys=["gliner_out"],
            output_keys=["normalized"],    # sorties finales du pipeline
        ),
    ]

    return Pipeline(
        steps=steps,
        input_keys=["raw_segment"],
        output_keys=["normalized"],
        name="gliner_mesh",
    )


def get_doc_pipeline(device: str = "cpu") -> DocPipeline:
    """
    Enveloppe le `Pipeline` ci-dessus dans un `DocPipeline` pratique :
    • on passe une liste de `TextDocument`;
    • les annotations créées sont ré-injectées dans chaque doc.
    """
    base_pipe = get_pipeline(device)
    return DocPipeline(pipeline=base_pipe)   # pas de labels_by_input_key -> segments RAW