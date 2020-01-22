import logging
import coloredlogs

from .BaseTask import BaseTask
from .InputFreesurferRecon import InputFreesurferRecon
from .DicomDir import DicomDir
from .DwiNifti import DwiNifti
from .DwiEddy import DwiEddy
from .DwiBetMask import DwiBetMask
from .WmparcInDwi import WmparcInDwi
from .Ukf import Ukf
from .TractQuerier import TractQuerier
from .TractMeasures import TractMeasures


coloredlogs.install(level='INFO', logger=logging.getLogger(''))
