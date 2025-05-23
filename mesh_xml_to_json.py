import xml.etree.ElementTree as ET
import json
from pathlib import Path

INPUT_FILE  = Path("fredesc2023.xml")     # vérifiez le nom !
OUTPUT_FILE = "mesh_dict.json"

# 1) Namespace MeSH
NS = {"m": "http://www.nlm.nih.gov/mesh"}

mesh_terms = []

# 2) Parcours « streaming » + libération mémoire
for event, elem in ET.iterparse(INPUT_FILE, events=("end",)):
    # Retirer le namespace de la balise courante
    tag = elem.tag.split("}")[-1]

    if tag == "DescriptorRecord":
        mesh_id = elem.findtext("m:DescriptorUI", namespaces=NS)

        main_node = elem.find("m:DescriptorName/m:String", namespaces=NS)
        if mesh_id is None or main_node is None:
            # Certains enregistrements incomplets : on ignore
            elem.clear()
            continue

        main_term = main_node.text.strip()
        term_set = {main_term}

        # Tous les synonymes (TermList)
        for term in elem.findall(".//m:TermList/m:Term/m:String", namespaces=NS):
            if term.text:
                term_set.add(term.text.strip())

        # Ajout dans la liste finale
        for term in sorted(term_set):
            mesh_terms.append({"term": term, "id": mesh_id})

        elem.clear()          # libère la RAM

# 3) Sauvegarde JSON utf-8
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(mesh_terms, f, ensure_ascii=False, indent=2)

print(f"✅ {len(mesh_terms)} entries written to {OUTPUT_FILE}")
