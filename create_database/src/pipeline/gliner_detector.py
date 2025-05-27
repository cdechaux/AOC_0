from medkit.core import Operation
from medkit.core.text import Segment, Span
from gliner import GLiNER

class GlinerDetector(Operation):
    def __init__(self, labels, device="cpu", out_label="medical_entity"):
        super().__init__(output_label=out_label)
        self._labels = labels
        self._model = GLiNER.from_pretrained(
            "Ihor/gliner-biomed-large-v1.0", device=device
        )

    def run(self, segments):
        text = segments[0].text if segments else ""
        out = []
        for ent in self._model.predict_entities(text, self._labels):
            out.append(
                Segment(
                    label=self.output_label,
                    spans=[Span(ent["start"], ent["end"])],
                    text=text[ent["start"]:ent["end"]],
                )
            )
        return out
