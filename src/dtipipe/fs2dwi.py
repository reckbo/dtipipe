import logging

import coloredlogs
import pytest
from plumbum import local, cli
import nibabel as nib

from . import bse
from .apply_antsRegistrationSyNMI import apply_antsRegistrationSyNMI
from . import util
from . import TEST_DATA
from . import REPO_DIR


log = logging.getLogger(__name__)
NUM_PROC_ANTS = 10


def fs2dwi(freesurfer_recon_dir, dwi_file, dwi_mask_file, output_dir,
           freesurfer_home, fsldir, antspath, num_proc_ants=NUM_PROC_ANTS, make_brainres=False,
           debug=False):
    """
    Registers Freesurfer labelmap to DWI space.
    """

    freesurfer_recon_dir = local.path(freesurfer_recon_dir)
    brain_mgz = freesurfer_recon_dir / 'mri' / 'brain.mgz'
    wmparc_mgz = freesurfer_recon_dir / 'mri' / 'wmparc.mgz'
    output_dir = local.path(output_dir)

    with util.freesurfer_env(freesurfer_home, fsldir), local.tempdir() as tmpdir:

        masked_b0 = tmpdir / "masked_b0.nii.gz"
        masked_b0_brainres = tmpdir / "masked_b0_brainres.nii.gz"
        brain_nii = tmpdir / "brain.nii.gz"
        wmparc_nii = tmpdir / "wmparc.nii.gz"
        wmparc_in_dwi = tmpdir / 'wmparc_in_dwi.nii.gz'
        brain_in_dwi = tmpdir / 'brain_in_dwi.nii.gz'
        wmparc_in_dwi_brainres = tmpdir / 'wmparc_in_dwi_brainres.nii.gz'

        log.info("Convert brain.mgz to nifti")
        mri_vol2vol = local['mri_vol2vol']
        mri_vol2vol('--mov', brain_mgz, '--targ', brain_mgz, '--regheader',
                    '--o', brain_nii)

        log.info("Convert wmparc.mgz to nifti")
        mri_label2vol = local['mri_label2vol']
        mri_label2vol('--seg', wmparc_mgz, '--temp', brain_mgz, '--regheader', wmparc_mgz,
                      '--o', wmparc_nii)

        log.info(f'Extract B0 from DWI and mask it ({masked_b0})')
        bse.bse(dwi=dwi_file, dwi_mask=dwi_mask_file, output=masked_b0)

        dwi_resolution = nib.load(str(masked_b0)).header['pixdim'][1:4].round()
        brain_resolution = nib.load(str(brain_nii)).header['pixdim'][1:4].round()
        log.info(f'DWI resolution: {dwi_resolution}')
        log.info(f'FreeSurfer brain resolution: {brain_resolution}')

        for resolution in [dwi_resolution, brain_resolution]:
            if resolution.ptp():
                raise Exception(f'Resolution is not uniform among all the axes: {resolution}')

        with util.ants_env(antspath), local.tempdir() as tmpdir:
            output_prefix = tmpdir / 'brain_to_b0'
            affine = output_prefix + '0GenericAffine.mat'
            warp = output_prefix + '1Warp.nii.gz'
            log.info(f'Compute warp from brain to masked B0')
            r = local[REPO_DIR / 'scripts' / 'antsRegistrationSyNMI.sh'].run(['-m', brain_nii,
                                                                              '-f', masked_b0,
                                                                              '-o', output_prefix,
                                                                              '-n', num_proc_ants])
            log.debug(f'antsRegistrationSyNMI.sh: {r}')
            log.info(f'Warp wmparc to B0 (Make "{wmparc_in_dwi}")')
            r = local['antsApplyTransforms'].run(['-d', '3',
                                                  '-i', wmparc_nii,
                                                  '-t', warp, affine,
                                                  '-r', masked_b0,
                                                  '-o', wmparc_in_dwi,
                                                  '--interpolation', 'NearestNeighbor'])
            log.debug(f'antsApplyTransforms: {r}')
            log.info(f'Warp brain to B0 (Make "{brain_in_dwi}")')
            r = local['antsApplyTransforms'].run(['-d', '3',
                                                  '-i', brain_nii,
                                                  '-t', warp, affine,
                                                  '-r', masked_b0,
                                                  '-o', brain_in_dwi,
                                                  '--interpolation', 'NearestNeighbor'])
            log.debug(f'antsApplyTransforms: {r}')

        if (dwi_resolution != brain_resolution).any() and make_brainres:
            log.info('DWI resolution is different from FreeSurfer brain resolution: '
                     f'{dwi_resolution} != {brain_resolution}')
            log.info(f'Resample B0 to brain resolution (Make "{masked_b0_brainres}")')
            with util.ants_env(antspath):
                local['ResampleImageBySpacing']('3', masked_b0,
                                                masked_b0_brainres,
                                                brain_resolution.tolist())

            print(f'Register wmparc to upsampled B0 (Make "{wmparc_in_dwi_brainres}")')
            apply_antsRegistrationSyNMI(moving_image=brain_nii,
                                        fixed_image=masked_b0_brainres,
                                        moving_image_src=wmparc_nii,
                                        output=wmparc_in_dwi_brainres,
                                        num_proc=num_proc_ants,
                                        antspath=antspath)

        output_dir.mkdir()

        masked_b0.copy(output_dir)
        wmparc_in_dwi.copy(output_dir)
        brain_in_dwi.copy(output_dir)
        if masked_b0_brainres.exists():
            masked_b0_brainres.copy(output_dir)
            wmparc_in_dwi_brainres.copy(output_dir)

        log.info(f'Made "{output_dir}"')


@pytest.mark.slow
def test_fs2dwi(freesurfer_home, fsldir, antspath, num_proc_ants):
    freesurfer_recon_dir = TEST_DATA / 'edit.FS6_004_006_bv'
    dwi_file = TEST_DATA / 'dwi_eddy.nii.gz'
    dwi_mask_file = TEST_DATA / 'dwi_mask.nii.gz'
    with local.tempdir() as tmpdir:
        tmpdir = local.path('/tmp/fs2dwi')
        output_dir = tmpdir
        fs2dwi(freesurfer_recon_dir=freesurfer_recon_dir,
               dwi_file=dwi_file,
               dwi_mask_file=dwi_mask_file,
               output_dir=output_dir,
               make_brainres=False,
               freesurfer_home=freesurfer_home,
               fsldir=fsldir,
               antspath=antspath,
               num_proc_ants=num_proc_ants)
    assert output_dir.exists()


class Cli(cli.Application):

    __doc__ = fs2dwi.__doc__

    freesurfer_recon_dir = cli.SwitchAttr(
        ['-f', '--freesurfer-recon-dir'],
        argtype=cli.ExistingDirectory,
        mandatory=True,
        help='FreeSurfer subject recon directory')

    dwi_file = cli.SwitchAttr(
        ['--dwi'],
        argtype=cli.ExistingFile,
        mandatory=True,
        help='Target DWI')

    dwi_mask_file = cli.SwitchAttr(
        ['--dwi-mask'],
        argtype=cli.ExistingFile,
        mandatory=True,
        help='DWI mask')

    output_dir = cli.SwitchAttr(
        ['-o', '--output-dir'],
        argtype=cli.NonexistentPath,
        mandatory=True,
        help='Output directory')

    num_proc = cli.SwitchAttr(
        ['-n', '--num-proc'],
        argtype=int,
        default=NUM_PROC_ANTS,
        help='Number of threads')

    antspath = cli.SwitchAttr(
        ['--antspath'],
        argtype=cli.ExistingDirectory,
        help='Path to root ANTs bin/ directory')

    freesurfer_home = cli.SwitchAttr(
        ['--fshome', '--freesurfer-home'],
        argtype=cli.ExistingDirectory,
        help='Path to FreeSurfer installation (FREESURFER_HOME)')

    fsldir = cli.SwitchAttr(
        ['--fsldir'],
        argtype=cli.ExistingDirectory,
        help='Root path of FSL (FSL_DIR)')

    log_level = cli.SwitchAttr(
        ['--log-level'],
        argtype=cli.Set("CRITICAL", "ERROR", "WARNING",
                        "INFO", "DEBUG", "NOTSET", case_sensitive=False),
        default='INFO',
        help='Python log level')

    def main(self):
        coloredlogs.install(level=self.log_level)
        fs2dwi(freesurfer_recon_dir=self.freesurfer_recon_dir,
               dwi_file=self.dwi_file,
               dwi_mask_file=self.dwi_mask_file,
               output_dir=self.output_dir,
               freesurfer_home=self.freesurfer_home,
               fsldir=self.fsldir,
               antspath=self.antspath,
               num_proc_ants=self.num_proc)
