from medkit.core.pipeline import DocumentPipeline
from .gliner_detector import GlinerDetector
from .mesh_normalizer import MeshNormalizer
from ..utils import load_simstring_matcher   # fonction auxiliaire

def get_pipeline(device="cpu"):
    det = GlinerDetector(["disease","condition","symptom","treatment"], device=device)
    norm = MeshNormalizer(load_simstring_matcher())
    pipe = DocumentPipeline(name="gliner_mesh")
    pipe.add(det, inputs={"segments": "raw_segment"})
    pipe.add(norm, inputs={0: det})
    return pipe
