from datasets import load_dataset, DatasetDict, Features, Sequence, Value, ClassLabel
from gliner import GLiNER
from medkit.core.text import TextDocument, Segment, Span 
from medkit.text.ner import SimstringMatcher, SimstringMatcherRule
import json
from pathlib import Path

# --- 1. Charger les données (cas cliniques)
dataset = load_dataset("rntc/edu3-clinical-fr", split="train")


def extract_entities(example):
    text = example["article_text"]
    entities = gliner_model.predict_entities(text, labels)      # ← vos entités GLiNER

    # ------------------ transformation en segments ---------------------------
    segments = []
    for ent in entities:
        seg = Segment(
            label="medical_entity",
            spans=[Span(0, len(text[ent["start"]:ent["end"]]))],
            text=text[ent["start"]:ent["end"]],
        )
        segments.append(seg)

    matches = matcher.run(segments)

    found = []
    for m in matches:
        mesh_ids = [
            norm.kb_id
            for norm in m.attrs.get(label="NORMALIZATION")
            if norm.kb_name == "MeSH"
        ] or [None]                           # pour avoir au moins un élément
        found.append(
            {
                "term":   m.text,
                "label":  ent["label"],       # re‐utilisez le label GLiNER
                "mesh_id": mesh_ids[0],       # premier id (ou None)
            }
        )

    example["detected_entities"] = found
    return example


new_ds = ds.map(extract_entities, batched=False, desc="annotating")
new_ds.save_to_disk("edu3-clinical-fr+mesh")
