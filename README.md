# AOC_0
```text
├── create_database
│   ├── data
│   │   ├── dictionnaires
│   │   │   ├── cache_pubmed.json
│   │   │   ├── create_dictionnaires
│   │   │   │   ├── create_mesh_checktags.py
│   │   │   │   └── mesh_xml_to_json.py
│   │   │   ├── mesh_checktags.json
│   │   │   ├── mesh_dict.json
│   │   │   └── umls_mesh2icd_cache.json
│   │   └── local_databases
│   │       ├── edu3-clinical-fr+mesh
│   │       └── edu3-clinical-fr+mesh-2
│   ├── dvpt_scripts
│   │   ├── 1_create_database_codesMESH_with_gliner.py
│   │   ├── 2_add_mesh_from_pubmed_to_db.py
│   │   ├── 3_mesh_to_cim10.py
│   │   └── other
│   │       ├── debug_umls.py
│   │       ├── push_db_hub.py
│   │       └── TEST_gliner_simstring_pipeline.py
│   ├── __init__.py
│   ├── __pycache__
│   ├── src
│   │   ├── cli.py
│   │   ├── pipeline
│   │   │   ├── __init__.py
│   │   │   ├── build_pipeline.py
│   │   │   ├── gliner_detector.py
│   │   │   ├── icd10_mapper.py
│   │   │   ├── mesh_normalizer.py
│   │   │   ├── pubmed_fetcher.py
│   │   │   └── __pycache__
│   │   ├── pubmed
│   │   │   ├── fetch_mesh.py
│   │   │   ├── __init__.py
│   │   │   └── __pycache__
│   │   ├── __pycache__
│   │   └── utils.py
│   └── stats_desc
│       └── mesh_stats.ipynb
├── README.md
└── requirements.txt
```


python3 -m venv aoc-env
source aoc-env/bin/activate

# ré-installer les dépendances
pip install -r requirements.txt

python -m create_database.src.cli


python -m create_database.src.cli \
  --hf-token "hf_xxx" \
  --umls-api-key "abc123" \
  --dataset-name-initial "rntc/edu3-clinical-fr"\
  --dataset-name "clairedhx/edu3-clinical-fr-mesh-5"
