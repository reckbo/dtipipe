import luigi.util
from luigi import OptionalParameter, FloatParameter
from plumbum import local

from .BaseTask import BaseTask
from .DwiEddy import DwiEddy

from dtipipe import bet_mask
from dtipipe import util


@luigi.util.requires(DwiEddy)
class DwiBetMask(BaseTask):

    dwi_bet_mask_threshold = FloatParameter()
    fsldir = OptionalParameter(default=None)

    def output(self):
        input_dwi = self.input()['nii.gz']
        return local.path(str(input_dwi)[:-7] + f'_betmask-{self.dwi_bet_mask_threshold}.nii.gz')

    def run(self):
        bet_mask.bet_mask(input_file=self.input()['nii.gz'],
                          output_file=self.output(),
                          bet_threshold=self.dwi_bet_mask_threshold,
                          fsldir=self.fsldir)

    def qc(self):
        with util.fsl_env(self.fsldir):
            local['fslview'](self.input()['nii.gz'], self.output())
