import logging

from plumbum import local
import pandas as pd
import luigi.util
from luigi import Parameter, IntParameter

from .. import standard_pnl
from ..BaseTask import BaseTask


OUTPUT_SUFFIXES = ['b0', 'dwi', 'e1', 'e2', 'e3', 'fa', 'tensor']

@luigi.util.requires(standard_pnl.DwiEddy)
class Dti(BaseTask):

    dtk_dir = Parameter()

    def output(self):
        output_prefix = self.output_prefix()
        result = dict(gradient_matrix=local.path(output_prefix + '.csv'))
        for output_suffix in OUTPUT_SUFFIXES:
            result[output_suffix] = local.path(output_prefix + '_' + output_suffix + '.nii.gz')
        return result

    def run(self):
        log = logging.getLogger('luigi-interface')
        self.output()['gradient_matrix'].parent.mkdir()
        self.make_gradient_matrix(self.input()['bvec'],
                                  self.input()['bval'],
                                  self.output()['gradient_matrix'])
        dti_recon = local[self.dtk_dir + '/dti_recon']
        cmd = dti_recon[self.input()['nii.gz'],
                        self.output_prefix(),
                        '-gm', self.output()['gradient_matrix'],
                        '-ot', 'nii.gz']
        log.info(f'Running: {cmd}')
        cmd()

    def output_prefix(self):
        dwi_eddy_nifti = self.input()['nii.gz']
        return str(dwi_eddy_nifti.parent / 'dtk' / dwi_eddy_nifti.name[:-7] + '_dti')

    @staticmethod
    def make_gradient_matrix(bvec, bval, output):
        bvals = local.path(bval).read().strip().split(' ')
        df = pd.read_csv(bvec, sep=' ', header=None)
        df['bval'] = bvals
        df.to_csv(output, header=False, index=False)
