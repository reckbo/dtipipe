
from luigi import FloatParameter, Parameter, OptionalParameter, IntParameter
from plumbum import local

from dtipipe import fs2dwi
from .BaseTask import BaseTask
from .InputFreesurferRecon import InputFreesurferRecon
from .DwiEddy import DwiEddy
from .DwiBetMask import DwiBetMask


class WmparcInDwi(BaseTask):

    # Inputs
    dicom_dir = Parameter()
    freesurfer_recon_dir = Parameter()

    # Outputs
    output_session_dir = Parameter()
    output_basename = Parameter()

    # Parameters
    dwi_bet_mask_threshold = FloatParameter()

    # Software
    dcm2niix_bin = Parameter(default='dcm2niix')
    fsldir = OptionalParameter(default=None)
    antspath = OptionalParameter(default=None)
    freesurfer_home = OptionalParameter(default=None)

    # Control
    num_proc_eddy = IntParameter(significant=False)
    num_proc_ants = IntParameter(significant=False)

    def requires(self):
        return dict(dwi=self.clone(DwiEddy),
                    dwi_mask=self.clone(DwiBetMask),
                    freesurfer_recon_dir=InputFreesurferRecon(self.freesurfer_recon_dir))

    def output_dir(self):
        return local.path(self.output_session_dir) / f'{self.output_basename}.wmparc_in_dwi'

    def output(self):
        output_dir = self.output_dir()
        return dict(wmparc_in_dwi=output_dir / 'wmparc_in_dwi.nii.gz',
                    wmparc_in_dwi_brainres=output_dir / 'wmparc_in_dwi_brainres.nii.gz',
                    masked_b0=output_dir / 'masked_b0.nii.gz',
                    masked_b0_brainres=output_dir / 'masked_b0_brainres.nii.gz')

    def run(self):
        fs2dwi.fs2dwi(freesurfer_recon_dir=self.input()['freesurfer_recon_dir'],
                      dwi_file=self.input()['dwi']['nii.gz'],
                      dwi_mask_file=self.input()['dwi_mask'],
                      output_dir=self.output_dir(),
                      freesurfer_home=self.freesurfer_home,
                      fsldir=self.fsldir,
                      antspath=self.antspath,
                      num_proc_ants=self.num_proc_ants)