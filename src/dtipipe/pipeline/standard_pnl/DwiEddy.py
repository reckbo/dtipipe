import luigi.util
from luigi import OptionalParameter, IntParameter
from plumbum import local

from dtipipe import eddy_pnl
from .BaseTask import BaseTask
from .DwiNifti import DwiNifti


@luigi.util.requires(DwiNifti)
class DwiEddy(BaseTask):

    fsldir = OptionalParameter(default=None)
    num_proc_eddy = IntParameter(significant=False)

    def output(self):
        return {suffix: local.path(self.output_session_dir,
                                   self.output_basename + '-ed.' + suffix) for
                suffix in ['nii.gz', 'bval', 'bvec']}

    def run(self):
        eddy_pnl.eddy_pnl(dwi=self.input()['nii.gz'],
                          output=self.output()['nii.gz'],
                          num_proc=self.num_proc_eddy,
                          fsldir=self.fsldir)
