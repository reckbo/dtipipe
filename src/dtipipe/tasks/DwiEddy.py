import luigi.util
from luigi import OptionalParameter, IntParameter
from plumbum import local

from .BaseTask import BaseTask
from .DwiNifti import DwiNifti

from ..eddy_pnl import eddy_pnl


@luigi.util.requires(DwiNifti)
class DwiEddy(BaseTask):

    fsldir = OptionalParameter(default=None)
    nproc = IntParameter(significant=False, default=5)

    def output(self):
        return {suffix: local.path(self.output_session_dir,
                                   self.output_basename + '-ed.' + suffix) for
                suffix in ['nii.gz', 'bval', 'bvec']}

    def run(self):
        eddy_pnl(dwi=self.input()['nii.gz'],
                 output=self.output()['nii.gz'],
                 nproc=self.nproc,
                 fsldir=self.fsldir)
