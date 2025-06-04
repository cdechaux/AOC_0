from medkit.core import Operation
from medkit.core.text import Segment, Span
from medkit.core.attribute import Attribute   
from gliner import GLiNER

class GlinerDetector(Operation):
    def __init__(self, labels, device="cuda", out_label="medical_entity"):
        super().__init__(output_label=out_label)
        self._labels = labels
        self._model = GLiNER.from_pretrained(
            "Ihor/gliner-biomed-large-v1.0", device=device
        )
        self.output_label = out_label

    def run(self, segments):
        text = segments[0].text if segments else ""
        ents = self._model.predict_entities(text, self._labels)

        # ─── DEBUG ──────────────────────────────────────────────
        print(f"[GLiNER] {len(ents)} entités – 1re phrase : {text[:80]!r}")
        # ─────────────────────────────────────────────────────────

        out = []
        for ent in ents:
            seg = Segment(
                label=self.output_label,
                spans=[Span(ent["start"], ent["end"])],
                text=text[ent["start"]:ent["end"]],
            )
            seg.attrs.add(Attribute(label="gliner_label", value=ent["label"]))
            out.append(seg)
        return out
