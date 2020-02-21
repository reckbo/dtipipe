from plumbum import local
import pandas as pd
import luigi.util

from .. import standard_pnl
from ..BaseTask import BaseTask


@luigi.util.requires(standard_pnl.DwiEddy)
class Dti(BaseTask):

    def output(self):
        dwi_eddy_nifti = self.requires()['nii.gz']
        dti_filename = dwi_eddy_nifti.name[:-7] + '_dti.nii.gz'
        gradient_matrix_filename = dwi_eddy_nifti.name[:-7] + '_dti.csv'
        return dict(nifti=dwi_eddy_nifti.parent / 'dtk' / dti_filename,
                    gradient_matrix=dwi_eddy_nifti.parent / 'dtk' / gradient_matrix_filename)

    def run(self):
        pass

    @staticmethod
    def make_gradient_matrix(bvec, bval, output):
        bvals = local.path(bval).read().strip().split(' ')
        df = pd.read_csv(bvec, sep=' ', header=None)
        df['bval'] = bvals
        df.to_csv(output, header=False, index=False)
