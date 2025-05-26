import xml.etree.ElementTree as ET, json, pathlib

MESH_XML = pathlib.Path("fredesc2023.xml")   # MeSH complet (ou fredesc2025.xml)
checktag_ids = set()

for _, rec in ET.iterparse(MESH_XML, events=("end",)):
    if rec.tag == "DescriptorRecord" and rec.findtext("IsCheckTag") == "Y":
        checktag_ids.add(rec.findtext("DescriptorUI"))
    rec.clear()

json.dump(sorted(checktag_ids), open("mesh_checktags.json", "w"))
