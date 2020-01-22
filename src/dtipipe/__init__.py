__version__ = '0.1.0'

from plumbum import local

REPO_DIR = local.path(__file__).parent.parent.parent
TEST_DATA = REPO_DIR / 'test_data'

from . import bse
from . import eddy_pnl
from . import bet_mask
from . import apply_antsRegistrationSyNMI
from . import fs2dwi
from . import nifti2nhdr
from . import ukf
from . import ukf_tract_querier
from . import measuretracts
from . import pipeline


