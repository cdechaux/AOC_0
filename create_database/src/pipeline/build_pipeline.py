from medkit.core.pipeline import Pipeline, PipelineStep
from medkit.core.doc_pipeline import DocPipeline
from .gliner_detector import GlinerDetector
from .mesh_normalizer import MeshNormalizer
from ..utils import load_simstring_matcher   
from .icd10_mapper      import ICD10Mapper
from .pubmed_fetcher import PubMedMeshFetcher


def get_pipeline(device: str = "cuda") -> Pipeline:
    det  = GlinerDetector(
        labels=["disease", "condition", "symptom", "treatment"],
        device=device,
    )
    norm = MeshNormalizer(load_simstring_matcher())
    fetch = PubMedMeshFetcher() 
    icd  = ICD10Mapper()            # modifie les mêmes segments in-place

    steps = [
        # 1) repérage d’entités gliner
        PipelineStep(det,
                     input_keys=["raw_segment"],
                     output_keys=["gliner_out"]),

        # 2) normalisation MeSH  → nouveaux segments
        PipelineStep(norm,
                     input_keys=["gliner_out"],
                     output_keys=["mesh_norm"]),

        # 3) extraction mesh de pubmed
        PipelineStep(fetch,
                     input_keys=["raw_segment"],
                     output_keys=["pubmed_mesh"]),

        # 3) ajout d’attributs ICD-10-CM sur ces mêmes segments
        PipelineStep(icd,
                     input_keys=["mesh_norm", "pubmed_mesh"],
                     output_keys=[""]),
    ]

    # 🔸  *** la clé importante ***
    return Pipeline(
        steps=steps,
        input_keys=["raw_segment"],
        output_keys=["mesh_norm","pubmed_mesh"], 
        name="gliner_mesh_icd10",
    )


def get_doc_pipeline(device: str = "cuda") -> DocPipeline:
    """
    Enveloppe le `Pipeline` ci-dessus dans un `DocPipeline` pratique :
    • on passe une liste de `TextDocument`;
    • les annotations créées sont ré-injectées dans chaque doc.
    """
    base_pipe = get_pipeline(device)
    return DocPipeline(pipeline=base_pipe)   # pas de labels_by_input_key -> segments RAW