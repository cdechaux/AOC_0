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
│   │   │   └── mesh_dict.json
│   │   └── local_databases
│   │       ├── edu3-clinical-fr+mesh
│   │       └── edu3-clinical-fr+mesh-2
│   ├── dvpt_scripts
│   │   ├── 1_create_database_codesMESH_with_gliner.py
│   │   ├── 2_add_mesh_from_pubmed_to_db.py
│   │   ├── 3_mesh_to_cim10.py
│   │   ├── push_db_hub.py
│   │   └── TEST_gliner_simstring_pipeline.py
│   ├── __init__.py
│   ├── src
│   │   ├── cli.py
│   │   ├── pipeline
│   │   │   ├── build_pipeline.py
│   │   │   ├── gliner_detector.py
│   │   │   ├── __init__.py
│   │   │   ├── mesh_normalizer.py
│   │   │   └── __pycache__
│   │   ├── pubmed
│   │   │   ├── fetch_mesh.py
│   │   │   ├── __init__.py
│   │   │   └── __pycache__
│   │   └── utils.py
│   └── stats_desc
│       └── mesh_stats.ipynb
├── pipelines_traitement
├── README.md
└── requirements.txt
```

python -m create_database.src.cli
