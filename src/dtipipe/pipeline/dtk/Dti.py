import logging

from plumbum import local
import pandas as pd
import luigi.util
from luigi import Parameter, IntParameter

from .. import standard_pnl
from ..BaseTask import BaseTask


@luigi.util.requires(standard_pnl.DwiEddy)
class Dti(BaseTask):

    dtk_dir = Parameter()

    def output(self):
        dwi_eddy_nifti = self.input()['nii.gz']
        dti_filename = dwi_eddy_nifti.name[:-7] + '_dti.nii.gz'
        gradient_matrix_filename = dwi_eddy_nifti.name[:-7] + '_dti.csv'
        return dict(nifti=dwi_eddy_nifti.parent / 'dtk' / dti_filename,
                    gradient_matrix=dwi_eddy_nifti.parent / 'dtk' / gradient_matrix_filename)

    def run(self):
        log = logging.getLogger('luigi-interface')
        self.output()['gradient_matrix'].parent.mkdir()
        self.make_gradient_matrix(self.input()['bvec'],
                                  self.input()['bval'],
                                  self.output()['gradient_matrix'])
        dti_recon = local[self.dtk_dir + '/dti_recon']
        cmd = dti_recon[self.input()['nii.gz'],
                        self.output()['nifti'].with_suffix('', depth=2),
                        '-gm', self.output()['gradient_matrix'],
                        '-ot', 'nii.gz']
        log.info(f'Running: {cmd}')
        cmd()

    @staticmethod
    def make_gradient_matrix(bvec, bval, output):
        bvals = local.path(bval).read().strip().split(' ')
        df = pd.read_csv(bvec, sep=' ', header=None)
        df['bval'] = bvals
        df.to_csv(output, header=False, index=False)
