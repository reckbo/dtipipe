__version__ = '0.1.0'

from plumbum import local

TEST_DATA = local.path(__file__).parent.parent.parent / 'test_data'

from . import bse
from . import eddy_pnl
from . import bet_mask
from . import pipeline


