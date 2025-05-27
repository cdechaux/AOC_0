import json, pathlib

# 41 codes – liste NLM 2025 : checktags (liste générée par chatgpt o3)
CHECK_TAG_IDS = {
    "D000328","D000367","D000379","D000544","D000544","D000818","D001921",
    "D005260","D005785","D006262","D006801","D006973","D007086","D007234",
    "D007751","D008297","D008875","D008279","D008297","D011247","D012640",
    "D013997","D014057","D014888","D015242","D015996","D016361","D016397",
    "D018078","D018709","D018737","D018738","D018768","D018772","D018784",
    "D020385","D040241","D040243","D042882","D044127","D046143","D048506"
}

json.dump(sorted(CHECK_TAG_IDS), open("create_database/data/dictionnaires/mesh_checktags.json","w"), indent=2)