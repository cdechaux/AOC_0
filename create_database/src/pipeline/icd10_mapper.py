# src/pipeline/icd10_mapper.py
from __future__ import annotations
import os, json, pathlib, requests
from medkit.core.operation import DocOperation
from medkit.core.attribute import Attribute
from dotenv import load_dotenv

BASE   = "https://uts-ws.nlm.nih.gov/rest"
load_dotenv() 
APIKEY = os.getenv("UMLS_API_KEY")
TIMEOUT = 15
CACHE   = {}          # RAM (option : persister dans utils)

class ICD10Mapper(DocOperation):
    """
    Prend en entrée des segments contenant un attr NORMALIZATION[kb=MeSH]
    et ajoute un attr ICD10CM pour chaque code trouvé.

    L’attr ICD10CM porte :
        • value   : code (ex 'I10')
        • metadata: {cui, mesh_id, provenance}
    """

    def __init__(self, label="ICD10CM"):
        super().__init__(output_labels=[label])
        self.label = label

    # ---------- helpers API (simplifiés) ----------
    def _ui_to_cui(self, ui: str) -> str | None:
        if ui in CACHE:                 # (cui, codes) tuple
            return CACHE[ui][0]
        url = f"{BASE}/content/current/source/MSH/{ui}?apiKey={APIKEY}"
        cx  = requests.get(url, timeout=TIMEOUT).json()
        url2 = cx["result"]["concepts"] + f"&apiKey={APIKEY}"
        res  = requests.get(url2, timeout=TIMEOUT).json()
        lst  = res["result"]["results"]
        return lst[0]["ui"] if lst else None

    def _cui_to_codes(self, cui: str) -> list[str]:
        url = (f"{BASE}/content/2025AA/CUI/{cui}"
               f"/atoms?sabs=ICD10CM&pageSize=200&apiKey={APIKEY}")
        resp = requests.get(url, timeout=TIMEOUT)

        # 404, 401, ou JSON inattendu ⇒ aucune correspondance
        if resp.status_code != 200:
            return []

        data = resp.json()
        atoms = data.get("result", [])
        return sorted({
            a["code"].split("/")[-1]
            for a in atoms
            if a.get("rootSource") == "ICD10CM"
        })

    # ---------- opération principale ----------
    def run(self, segments: list):
        new_atts = []
        for seg in segments:
            for norm in seg.attrs.get(label="NORMALIZATION"):
                mesh_id = norm.kb_id
                prov     = seg.metadata.get("source")  # 'gliner' ou 'pubmed'
                if mesh_id in CACHE:
                    cui, codes = CACHE[mesh_id]
                else:
                    cui   = self._ui_to_cui(mesh_id)
                    codes = self._cui_to_codes(cui) if cui else []
                    CACHE[mesh_id] = (cui, codes)
                for code in codes:
                    attr = Attribute(
                        label=self.label,
                        value=code,
                        metadata={
                            "cui": cui,
                            "mesh_id": mesh_id,
                            "provenance": prov        # stocke la source
                        }
                    )
                    seg.attrs.add(attr)
                    new_atts.append(attr)
        return segments #tout est deja collé au segment 
