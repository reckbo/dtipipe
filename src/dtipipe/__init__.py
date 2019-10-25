__version__ = '0.1.0'

from plumbum import local

from . import tasks
from . import eddy_pnl


TEST_DATA = local.path(__file__).parent.parent.parent / 'test_data'
