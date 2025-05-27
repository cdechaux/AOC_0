import os, time, requests, xml.etree.ElementTree as ET, json, pathlib

_API = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
_KEY = os.getenv("NCBI_API_KEY")
_CACHE = pathlib.Path("create_database/data/dictionnaires/cache_pubmed.json")
mapping = json.loads(_CACHE.read_text()) if _CACHE.exists() else {}

def fetch_batch(pmids):
    ids = ",".join(pmids)
    url = f"{_API}?db=pubmed&id={ids}&retmode=xml"
    if _KEY: url += f"&api_key={_KEY}"
    xml = requests.get(url, timeout=15).text
    root = ET.fromstring(xml)
    res = {}
    for art in root.findall(".//PubmedArticle"):
        pmid = art.findtext(".//PMID").strip()
        res[pmid] = [
            d.get("UI") for d in art.findall(".//MeshHeading/DescriptorName")
            if d is not None
        ]
    mapping.update(res); _CACHE.write_text(json.dumps(mapping))
    return res
