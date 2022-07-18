import logging
from novafos import Novafos
import json

# Load test configuration data
with open('novafos_test.config', 'r') as f:
    config = json.load(f)

nov = Novafos(username=config['username'], password=config['password'], supplierid=config['supplierid'])

logging.basicConfig(level=logging.DEBUG)
l = logging.getLogger('urllib3')
l.setLevel(logging.ERROR)
nov.authenticate()
nov._get_customer_id()
nov._get_active_meters()
nov._get_day_data()

#nov.get_latest()