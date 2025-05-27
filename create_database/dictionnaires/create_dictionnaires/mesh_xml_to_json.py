#!/usr/bin/env python3
import xml.etree.ElementTree as ET, json
from pathlib import Path

INPUT_FILE  = Path("fredesc2023.xml")     # ← vérifiez le nom exact
OUTPUT_FILE = "create_database/dictionnaires/mesh_dict.json"

mesh_terms, seen = [], set()

for _, elem in ET.iterparse(INPUT_FILE, events=("end",)):
    if elem.tag != "DescriptorRecord":
        continue

    mesh_id = elem.findtext("DescriptorUI", default="").strip()
    if not mesh_id:
        elem.clear(); continue

    # ---------- libellé principal -------------------------------------------
    name_node = elem.find("DescriptorName")
    main_terms = []
    if name_node is not None:
        fr = name_node.findtext("StringFR", default="").strip()
        us = name_node.findtext("StringUS", default="").strip()
        main_terms = [t for t in (fr, us) if t]

    # ---------- synonymes ----------------------------------------------------
    syn_terms = []
    for term in elem.findall(".//TermList/Term"):
        fr = term.findtext("StringFR", default="").strip()
        us = term.findtext("StringUS", default="").strip()
        syn_terms.extend(t for t in (fr, us) if t)

    if not main_terms:
        elem.clear(); continue           # enregistrement incomplet

    term_set = set(main_terms + syn_terms)

    for term in term_set:
        key = (term.lower(), mesh_id)
        if key not in seen:
            mesh_terms.append({"term": term, "id": mesh_id})
            seen.add(key)

    elem.clear()                         # libère la mémoire

# ---------- sauvegarde JSON --------------------------------------------------
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(mesh_terms, f, ensure_ascii=False, indent=2)

print(f"✅ {len(mesh_terms)} entries written to {OUTPUT_FILE}")
