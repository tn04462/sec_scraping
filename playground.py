from email.parser import Parser
from main.data_aggregation.polygon_basic import PolygonClient
from main.configs import cnf

from main.data_aggregation.bulk_files import update_bulk_files


from main.parser.text_parser import Parser8K
from pathlib import Path
parser = Parser8K()

# first get all 8ks
def get_all_8k(cnf):
    paths_folder = [r.glob("8-K") for r in Path(cnf.DOWNLOADER_ROOT_PATH).glob("*")]
    paths_folder = [r for r in paths_folder]
    paths_files = [[f.rglob("*.htm") for f in r] for r in paths_folder]
    paths = []
    for l in paths_files:
        for each in l:
            for r in each:
                paths.append(r)
    return paths

i = []
failures = []
paths = get_all_8k(cnf)[:2]
print(len(paths))
for p in paths:
    with open(p, "r", encoding="utf-8") as f:
        file = f.read()
        filing = parser.preprocess_filing(file)
        items = parser.parse_items(filing)
        print(items)
            
# for x in i:
#     print(x)
#     for each in x:
#         print(each)