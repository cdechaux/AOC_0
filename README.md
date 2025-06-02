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
│   │       │   ├── cache-728991c250e60adf.arrow
│   │       │   ├── cache-96f994caba7bb258.arrow
│   │       │   ├── cache-a676912f7b549eb5.arrow
│   │       │   ├── cache-c7a73be7e456018e.arrow
│   │       │   ├── data-00000-of-00001.arrow
│   │       │   ├── dataset_info.json
│   │       │   └── state.json
│   │       └── edu3-clinical-fr+mesh-2
│   │           ├── data-00000-of-00001.arrow
│   │           ├── dataset_info.json
│   │           └── state.json
│   ├── dvpt_scripts
│   │   ├── 1_create_database_codesMESH_with_gliner.py
│   │   ├── 2_add_mesh_from_pubmed_to_db.py
│   │   ├── 3_mesh_to_cim10.py
│   │   ├── push_db_hub.py
│   │   └── TEST_gliner_simstring_pipeline.py
│   ├── __init__.py
│   ├── __pycache__
│   │   └── __init__.cpython-312.pyc
│   ├── src
│   │   ├── cli.py
│   │   ├── pipeline
│   │   │   ├── build_pipeline.py
│   │   │   ├── gliner_detector.py
│   │   │   ├── __init__.py
│   │   │   ├── mesh_normalizer.py
│   │   │   └── __pycache__
│   │   │       ├── build_pipeline.cpython-312.pyc
│   │   │       ├── gliner_detector.cpython-312.pyc
│   │   │       ├── __init__.cpython-312.pyc
│   │   │       └── mesh_normalizer.cpython-312.pyc
│   │   ├── pubmed
│   │   │   ├── fetch_mesh.py
│   │   │   ├── __init__.py
│   │   │   └── __pycache__
│   │   │       ├── fetch_mesh.cpython-312.pyc
│   │   │       └── __init__.cpython-312.pyc
│   │   ├── __pycache__
│   │   │   ├── cli.cpython-312.pyc
│   │   │   └── utils.cpython-312.pyc
│   │   └── utils.py
│   └── stats_desc
│       └── mesh_stats.ipynb
├── pipelines_traitement
├── README.md
└── requirements.txt
```

python -m create_database.src.cli
