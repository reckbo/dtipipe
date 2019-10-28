import luigi.util
from luigi import Parameter
from plumbum import local

from .BaseTask import BaseTask
from .DicomDir import DicomDir


@luigi.util.requires(DicomDir)
class DwiNifti(BaseTask):

    output_session_dir = Parameter()
    output_basename = Parameter()

    dcm2niix_bin = Parameter(default='dcm2niix')

    def output(self):
        return {suffix: local.path(self.output_session_dir, self.output_basename +
                                   '.' + suffix) for
                suffix in ['nii.gz', 'bval', 'bvec', 'json']}

    def run(self):
        local.path(self.output_session_dir).mkdir()
        dcm2niix = local[self.dcm2niix_bin]
        dcm2niix('-f', self.output_basename, '-z', 'y', '-o', self.output_session_dir, self.input())
