import logging
from plumbum import local, BG
import luigi.util
import nibabel as nib

from .BaseTask import BaseTask
from .DwiEddy import DwiEddy


@luigi.util.requires(DwiEddy)
class CaminoDti(BaseTask):

    def output(self):
        dwi = self.input()['nii.gz']
        scheme_file = dwi.with_suffix('.scheme', depth=2)
        dti_bfloat = str(dwi)[:-7] + '_dt.Bfloat'
        dti_nifti = str(dwi)[:-7] + '_dt.nii.gz'
        dti_eig = str(dwi)[:-7] + '_dt_eig.Bfloat'
        return dict(scheme=scheme_file,
                    dti_bfloat=local.path(dti_bfloat),
                    dti_nifti=local.path(dti_nifti),
                    dti_eig=local.path(dti_eig))

    def run(self):
        log = logging.getLogger('luigi-interface')
        log.info('Make scheme file')
        make_scheme_cmd = (local['fsl2scheme']['-bvecfile', self.input()['bvec'],
                                               '-bvalfile', self.input()['bval']]
                           > self.output()['scheme'])
        log.info(f'Running: {make_scheme_cmd}')
        make_scheme_cmd()
        log.info('Make DTI')
        make_dti_cmd = ((local['image2voxel']['-4dimage', self.input()['nii.gz']] |
                         local['modelfit']['-schemefile', self.output()['scheme'],
                                           '-outputdatatype', 'float'])
                        > self.output()['dti_bfloat'])
        log.info(f'Running: {make_dti_cmd}')
        make_dti_cmd()
        log.info('Convert DTI to nifti')
        make_dti_nifti_cmd = local['dt2nii']['-inputfile', self.output()['dti_bfloat'],
                                             '-inputdatatype', 'float',
                                             '-header', self.input()['nii.gz'],
                                             '-outputroot', str(self.input()['nii.gz'])[:-7] + '_']
        log.info(f'Running: {make_dti_nifti_cmd}')
        make_dti_nifti_cmd()
        log.info('Compute eigensystem of diffusion tensors')
        make_eig_cmd = ((local['dteig']['-inputmodel', 'dt',
                                        '-inputdatatype', 'float',
                                        '-outputdatatype', 'float']
                         < self.output()['dti_bfloat'])
                        > self.output()['dti_eig'])
        log.info(f'Running: {make_eig_cmd}')
        make_eig_cmd()

    def qc(self):
        dims = nib.load(str(self.input()['nii.gz'])).shape
        local['pdview']['-inputdatatype', 'float',
                        '-inputmodel', 'dteig',
                        '-inputfile', self.output()['dti_eig'],
                        '-datadims', dims[0], dims[1], dims[2]] & BG
