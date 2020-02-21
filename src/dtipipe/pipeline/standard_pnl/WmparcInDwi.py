
from luigi import FloatParameter, Parameter, OptionalParameter, IntParameter, BoolParameter
from plumbum import local, BG

from dtipipe import fs2dwi
from dtipipe import util
from ..BaseTask import BaseTask
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
    wmparc_in_dwi_make_brainres = BoolParameter(default=False,
                                                parsing=BoolParameter.EXPLICIT_PARSING)

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
        result = dict(wmparc_in_dwi=output_dir / 'wmparc_in_dwi.nii.gz',
                      brain_in_dwi=output_dir / 'brain_in_dwi.nii.gz',
                      masked_b0=output_dir / 'masked_b0.nii.gz')
        if self.wmparc_in_dwi_make_brainres:
            result['wmparc_in_dwi_brainres'] = output_dir / 'wmparc_in_dwi_brainres.nii.gz'
            result['masked_b0_brainres'] = output_dir / 'masked_b0_brainres.nii.gz'
        return result

    def run(self):
        fs2dwi.fs2dwi(freesurfer_recon_dir=self.input()['freesurfer_recon_dir'],
                      dwi_file=self.input()['dwi']['nii.gz'],
                      dwi_mask_file=self.input()['dwi_mask'],
                      output_dir=self.output_dir(),
                      make_brainres=self.wmparc_in_dwi_make_brainres,
                      freesurfer_home=self.freesurfer_home,
                      fsldir=self.fsldir,
                      antspath=self.antspath,
                      num_proc_ants=self.num_proc_ants)

    def freeview(self):
        wmparc_in_dwi = self.output()['wmparc_in_dwi']
        with util.freesurfer_env(self.freesurfer_home, self.fsldir):
            local['freeview']['-v',
                              self.output()['masked_b0'],
                              f'{wmparc_in_dwi}:colormap=lut'] & BG
