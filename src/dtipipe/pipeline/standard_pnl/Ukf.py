import luigi.util
from luigi import Parameter, DictParameter
from plumbum import local

from dtipipe import ukf
from ..BaseTask import BaseTask
from .DwiEddy import DwiEddy
from .DwiBetMask import DwiBetMask


@luigi.util.inherits(DwiEddy)
@luigi.util.inherits(DwiBetMask)
class Ukf(BaseTask):

    ukf_tractography_bin = Parameter()
    ukf_params = DictParameter()

    def requires(self):
        return dict(dwi_eddy=self.clone(DwiEddy),
                    dwi_mask=self.clone(DwiBetMask))

    def output(self):
        output_basename = self.input()['dwi_eddy']['nii.gz'].stem
        return local.path(self.output_session_dir) / f'{output_basename}.vtk'

    def run(self):
        ukf.ukf(dwi_file=self.input()['dwi_eddy']['nii.gz'],
                dwi_mask_file=self.input()['dwi_mask'],
                output_vtk=self.output(),
                ukf_tractography_bin=self.ukf_tractography_bin,
                **self.ukf_params)
