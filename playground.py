from main.data_aggregation.polygon_basic import PolygonClient
from main.configs import cnf
poly = PolygonClient(cnf.POLYGON_API_KEY)
ov = poly.get_overview_single_ticker("CEI")
print(ov)