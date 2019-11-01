import luigi.util
from luigi import Parameter, DictParameter
from plumbum import local

from dtipipe import ukf
from .BaseTask import BaseTask
from .DwiEddy import DwiEddy
from .DwiBetMask import DwiBetMask


@luigi.util.inherits(DwiEddy)
@luigi.util.inherits(DwiBetMask)
class Ukf(BaseTask):

    ukftractography_bin = Parameter()
    ukf_params = DictParameter()

    def requires(self):
        return dict(dwi_eddy=self.clone(DwiEddy),
                    dwi_mask=self.clone(DwiBetMask))

    def output(self):
        return local.path(self.output_session_dir) / f'{self.output_basename}.vtk'

    def run(self):
        ukf.ukf(dwi_file=self.input()['dwi_eddy']['nii.gz'],
                dwi_mask_file=self.input()['dwi_mask'],
                output_vtk=self.output(),
                ukftractography_bin=self.ukftractography_bin,
                **self.ukf_params)
