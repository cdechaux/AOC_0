#!/usr/bin/env python3
# create_database/src/pipeline/icd10_mapper.py
# ──────────────────────────────────────────────────────────────
"""Ajout d’attributs ICD-10-CM sur les segments déjà normalisés MeSH.

… (docstring inchangé) …
"""

from __future__ import annotations

import json
import os
import pathlib
from collections import defaultdict
from typing import Dict, List

import requests
from medkit.core import Operation
from medkit.core.attribute import Attribute
from medkit.core.text import Segment
from urllib.parse import quote

# --------------------------------------------------------------------------- #
# 1) chemins et cache                                                         #
# --------------------------------------------------------------------------- #
_CACHE_PATH = pathlib.Path(
    "create_database/data/dictionnaires/umls_mesh2icd_cache.json"
)


class ICD10Mapper(Operation):
    """Mappe MeSH → ICD-10-CM et ajoute les attributs « ICD10CM »."""

    _BASE = "https://uts-ws.nlm.nih.gov/rest"

    # ------------------------------------------------------------------ #
    # __init__                                                           #
    # ------------------------------------------------------------------ #
    def __init__(
        self,
        cache_path: pathlib.Path | str = _CACHE_PATH,
        api_key: str | None = None,
    ):
        super().__init__(output_label=None)          # step terminal
        self._cache_path = pathlib.Path(cache_path)

        # -------- cache en mémoire --------
        if self._cache_path.is_file():
            raw_cache: Dict[str, Dict[str, list]] = json.loads(
                self._cache_path.read_text(encoding="utf-8")
            )
        else:
            raw_cache = {}
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)

        # deux vues pratiques ⬇
        # vue “codes” : list[(code, cui)]
        self._mesh2codes: Dict[str, List[tuple[str, str | None]]] = {
            ui: [(d["code"], d.get("cui")) for d in entry.get("icd10", [])]
            for ui, entry in raw_cache.items()
        }

        # vue “cui principal”
        self._mesh2cui: Dict[str, str | None] = {
            ui: (entry["icd10"][0]["cui"] if entry.get("icd10") else None)
            for ui, entry in raw_cache.items()
        }

        # stockage brut pour sauvegarde
        self._raw_cache = raw_cache

        # ---------- API UMLS ----------
        self._api_key = api_key or os.getenv("UMLS_API_KEY")
        if not self._api_key:
            raise RuntimeError("UMLS_API_KEY manquant (variable d’environnement)")
        self._session = requests.Session()

    # ------------------------------------------------------------------ #
    # 2. helpers UMLS                                                    #
    # ------------------------------------------------------------------ #
    def _mesh_ui_to_cuis(self, ui: str) -> list[str]:
        """UI MeSH → liste (éventuelle) de CUI (souvent une seule)."""
        url = f"{self._BASE}/content/current/source/MSH/{quote(ui)}?apiKey={self._api_key}"
        data = self._session.get(url, timeout=15).json()
        concepts = data.get("result", {}).get("concepts")
        if not concepts:
            return []

        data2 = self._session.get(f"{concepts}&apiKey={self._api_key}", timeout=15).json()
        return [
            res["ui"]
            for res in (data2.get("result") or {}).get("results", [])
        ]

    def _cui_to_icd10cm(self, cui: str) -> list[str]:
        url = (
            f"{self._BASE}/content/2025AA/CUI/{cui}"
            f"/atoms?sabs=ICD10CM&pageSize=200&apiKey={self._api_key}"
        )
        atoms = self._session.get(url, timeout=15).json().get("result", [])
        return sorted({
            a["code"].split("/")[-1]
            for a in atoms
            if a.get("rootSource") == "ICD10CM"
        })

    # ------------------------------------------------------------------ #
    # 3. résolution MeSH ➜ (cuis, icd10)  + mise à jour du cache         #
    # ------------------------------------------------------------------ #
    def _resolve_mesh(self, ui: str) -> list[tuple[str, str | None]]:
        """
        Retourne une liste de tuples (code_icd10, cui_source).
        Met à jour le cache :
            {ui: {"cuis": [...], "icd10": [{"code": ..., "cui": ...}, ...]}}
        """
        if ui in self._mesh2codes:
            # valeur déjà au bon format [(code, cui), ...]
            return self._mesh2codes[ui]

        cuis = self._mesh_ui_to_cuis(ui)            # ex. ['C12345', 'C67890']
        pairs: list[tuple[str, str | None]] = []

        for cui in cuis:
            for code in self._cui_to_icd10cm(cui):
                pairs.append((code, cui))

        # dé-duplication éventuelle (on garde le 1er CUI rencontré)
        seen: dict[str, str | None] = {}
        for code, cui in pairs:
            seen.setdefault(code, cui)

        result = sorted(seen.items())               # [(code, cui), ...]
        self._mesh2codes[ui] = result
        self._mesh2cui[ui]   = result[0][1] if result else None   # « principal »

        # ► sauvegarde brute
        self._raw_cache[ui] = {
            "cuis": cuis,
            "icd10": [{"code": c, "cui": cu} for c, cu in result],
        }
        self._cache_path.write_text(json.dumps(self._raw_cache, indent=2),
                                    encoding="utf-8")

        return result


    # ------------------------------------------------------------------ #
    # 4. helpers attributs                                               #
    # ------------------------------------------------------------------ #
    def _build_attrs(self, mesh_id: str) -> list[Attribute]:
        attrs: list[Attribute] = []
        for code, cui in self._resolve_mesh(mesh_id):
            attrs.append(
                Attribute(
                    label="ICD10CM",
                    value=code,
                    metadata={
                        "cui": cui,
                        "mesh_id": mesh_id,
                        # « provenance » ajouté plus loin
                    },
                )
            )
        return attrs

    def map_mesh_ids(self, mesh_ids: list[str]) -> list[Attribute]:
        out: list[Attribute] = []
        for mid in mesh_ids:
            out.extend(self._build_attrs(mid))
        return out

    # ------------------------------------------------------------------ #
    # 5. run()                                                           #
    # ------------------------------------------------------------------ #
    def run(
        self,
        mesh_segments: list[Segment],
        pubmed_segments: list[Segment] | None = None,
    ):
        pubmed_segments = pubmed_segments or []

        # ---- provenance MeSH ----
        prov_map: dict[str, set[str]] = {}
        for seg in mesh_segments:
            for norm in seg.attrs.get(label="NORMALIZATION"):
                if norm.kb_name == "MeSH":
                    prov_map.setdefault(norm.kb_id, set()).add("gliner")

        for seg in pubmed_segments:
            for norm in seg.attrs.get(label="NORMALIZATION"):
                if norm.kb_name == "MeSH":
                    prov_map.setdefault(norm.kb_id, set()).add("pubmed")

        union_mesh = list(prov_map)

        # ---- mapping MeSH → ICD-10 ----
        attrs = self.map_mesh_ids(union_mesh)

        # ---- enrichissement + attachement ----
        trace: dict[str, dict] = {}
        for attr in attrs:
            mid = attr.metadata["mesh_id"]
            provenance = prov_map[mid]
            attr.metadata["provenance"] = (
                "both" if len(provenance) == 2 else next(iter(provenance))
            )
            trace.setdefault(
                attr.value,
                {
                    "cui": attr.metadata["cui"],
                    "mesh_id": mid,
                    "provenance": attr.metadata["provenance"],
                },
            )
            # ajouter seulement aux annotations portant ce MeSH
            for ann in mesh_segments + pubmed_segments:
                for norm in ann.attrs.get(label="NORMALIZATION"):
                    if norm.kb_name == "MeSH" and norm.kb_id == mid:
                        ann.attrs.add(attr.copy())
                        break

        # ---- trace JSON au niveau (première) annotation ----
        if mesh_segments or pubmed_segments:
            ann = (mesh_segments or pubmed_segments)[0]
            ann.attrs.add(
                Attribute(
                    label="icd10_trace",
                    value=json.dumps(trace, ensure_ascii=False),
                )
            )

        return []            # step terminal
