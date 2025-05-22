import xml.etree.ElementTree as ET
import json

INPUT_FILE = "desc2025.xml"
OUTPUT_FILE = "mesh_dict.json"

mesh_terms = []

# Parse XML de manière efficace (streaming)
for event, elem in ET.iterparse(INPUT_FILE, events=("end",)):
    if elem.tag == "DescriptorRecord":
        mesh_id = elem.findtext("DescriptorUI")
        main_term = elem.find("DescriptorName/String").text.strip()

        # Ensemble de termes (libellé principal + synonymes)
        term_set = {main_term}

        # Aller chercher les entry terms dans TermList
        for term in elem.findall(".//ConceptList/Concept/TermList/Term/String"):
            if term.text:
                term_set.add(term.text.strip())

        # Ajouter chaque terme comme entrée indépendante
        for term in sorted(term_set):
            mesh_terms.append({
                "term": term,
                "id": mesh_id
            })

        # Libérer la mémoire
        elem.clear()

# Sauvegarde JSON
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(mesh_terms, f, ensure_ascii=False, indent=2)

print(f"✅ {len(mesh_terms)} entries written to {OUTPUT_FILE}")
