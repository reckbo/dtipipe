import logging

from plumbum import local, cli
import nibabel as nib
# from plumbum.cmd import ResampleImageBySpacing, antsApplyTransforms, ImageMath

from . import bse
from . import util
from . import TEST_DATA


log = logging.getLogger(__name__)

REPO_DIR = local.path(__file__).parent.parent.parent
NUM_PROC_ANTS = 5


def register_wmparc_to_dwi(brain, wmparc, masked_b0, output_wmparc, num_proc=NUM_PROC_ANTS,
                           antspath=None):
    with util.ants_env(antspath), local.tempdir() as tmpdir:
        output_prefix = tmpdir / 'pre'
        affine = output_prefix + '0GenericAffine.mat'
        warp = output_prefix + '1Warp.nii.gz'
        log.info('Compute warp from brain to baseline')
        r = local[REPO_DIR / 'scripts' / 'antsRegistrationSyNMI.sh'].run(['-m', brain,
                                                                          '-f', masked_b0,
                                                                          '-o', output_prefix,
                                                                          '-n', num_proc])
        log.debug(f'antsRegistrationSyNMI.sh: {r}')
        log.debug(f'Output files in {tmpdir}: {tmpdir // "*"}')
        log.info('Apply warp to wmparc to create a resampled version in DWI space')
        local['antsApplyTransforms']('-d', '3',
                                     '-i', wmparc,
                                     '-t', warp, affine,
                                     '-r', masked_b0,
                                     '-o', output_wmparc,
                                     '--interpolation', 'NearestNeighbor')
    log.info('Made {output_wmparc}')


def fs2dwi(freesurfer_recon_dir, dwi_file, dwi_mask_file, freesurfer_home, fsldir, antspath):

    freesurfer_recon_dir = local.path(freesurfer_recon_dir)
    brain_mgz = freesurfer_recon_dir / 'mri' / 'brain.mgz'
    wmparc_mgz = freesurfer_recon_dir / 'mri' / 'wmparc.mgz'

    with util.freesurfer_env(freesurfer_home, fsldir), local.tempdir() as tmpdir:

        masked_b0 = tmpdir / "masked_b0.nii.gz"
        # b0maskedbrain = tmpdir / "b0maskedbrain.nii.gz"
        brain_nii = tmpdir / "brain.nii.gz"
        wmparc_nii = tmpdir / "wmparc.nii.gz"
        wmparc_in_dwi = tmpdir / 'wmparcInDwi.nii.gz' # Sylvain wants both
        # wmparc_in_brain = tmpdir / 'wmparcInBrain.nii.gz'

        log.info("Convert brain.mgz to nifti")
        mri_vol2vol = local['mri_vol2vol']
        mri_vol2vol('--mov', brain_mgz, '--targ', brain_mgz, '--regheader',
                    '--o', brain_nii)

        log.info("Convert wmparc.mgz to nifti")
        mri_label2vol = local['mri_label2vol']
        mri_label2vol('--seg', wmparc_mgz, '--temp', brain_mgz, '--regheader', wmparc_mgz,
                      '--o', wmparc_nii)

        log.info('Extract B0 from DWI and mask it')
        bse.bse(dwi=dwi_file, dwi_mask=dwi_mask_file, output=masked_b0)

        dwi_resolution = nib.load(str(masked_b0)).header['pixdim'][1:4].round()
        brain_resolution = nib.load(str(brain_nii)).header['pixdim'][1:4].round()
        log.info(f'DWI resolution: {dwi_resolution}')
        log.info(f'FreeSurfer brain resolution: {brain_resolution}')

        for resolution in [dwi_resolution, brain_resolution]:
            if resolution.ptp():
                raise Exception(f'Resolution is not uniform among all the axes: {resolution}')

        log.info('Register wmparc to B0')
        register_wmparc_to_dwi(brain=brain_nii,
                               wmparc=wmparc_nii,
                               masked_b0=masked_b0,
                               num_proc=NUM_PROC_ANTS,
                               output_wmparc=wmparc_in_dwi,
                               antspath=antspath)

#         if (dwi_res!=brain_res).any():
#             print('DWI resolution is different from FreeSurfer brain resolution')
#             print('wmparc wil be registered to both DWI and brain resolution')
#             print('Check output files wmparcInDwi.nii.gz and wmparcInBrain.nii.gz')

#             print('Resampling B0 to brain resolution')

#             ResampleImageBySpacing('3', b0masked, b0maskedbrain, brain_res.tolist())

#             print('Registering wmparc to resampled B0')
#             registerFs2Dwi(tmpdir, 'fsbrainToResampledB0', b0maskedbrain, brain, wmparc, wmparcinbrain)


#         # copying images to outDir
#         b0masked.copy(self.parent.out)
#         wmparcindwi.copy(self.parent.out)

#         if b0maskedbrain.exists():
#             b0maskedbrain.copy(self.parent.out)
#             wmparcinbrain.copy(self.parent.out)

#         if self.parent.debug:
#             tmpdir.copy(self.parent.out, 'fs2dwi-debug-' + str(os.getpid()))


#     print('See output files in ', self.parent.out._path)


def test_fs2dwi(freesurfer_home, fsldir, antspath):
    freesurfer_recon_dir = TEST_DATA / 'edit.FS6_004_006_bv'
    dwi_file = TEST_DATA / 'dwi_eddy.nii.gz'
    dwi_mask_file = TEST_DATA / 'dwi_mask.nii.gz'
    fs2dwi(freesurfer_recon_dir=freesurfer_recon_dir,
           dwi_file=dwi_file,
           dwi_mask_file=dwi_mask_file,
           freesurfer_home=freesurfer_home,
           fsldir=fsldir,
           antspath=antspath)


# # class FsToDwi(cli.Application):
# #     """Registers Freesurfer labelmap to DWI space."""

# #     fsdir = cli.SwitchAttr(
# #         ['-f', '--freesurfer'],
# #         cli.ExistingDirectory,
# #         help='freesurfer subject directory',
# #         mandatory=True)

# #     dwi = cli.SwitchAttr(
# #         ['--dwi'],
# #         cli.ExistingFile,
# #         help='target DWI',
# #         mandatory=True)

# #     dwimask = cli.SwitchAttr(
# #         ['--dwimask'],
# #         cli.ExistingFile,
# #         help='DWI mask',
# #         mandatory=True)

# #     out = cli.SwitchAttr(
# #         ['-o', '--outDir'],
# #         help='output directory',
# #         mandatory=True)

# #     force= cli.Flag(
# #         ['--force'],
# #         help='turn on this flag to overwrite existing output',
# #         default= False,
# #         mandatory= False)

# #     debug = cli.Flag(
# #         ['-d','--debug'],
# #         help='Debug mode, saves intermediate transforms to out/fs2dwi-debug-<pid>',
# #         default= False)

# #     def main(self):

# #         if not self.nested_command:
# #             print("No command given")
# #             sys.exit(1)

# #         self.fshome = local.path(os.getenv('FREESURFER_HOME'))

# #         if not self.fshome:
# #             print('Set FREESURFER_HOME first.')
# #             sys.exit(1)

# #         print('Making output directory')
# #         self.out= local.path(self.out)
# #         if self.out.exists() and self.force:
# #             print('Deleting existing directory')
# #             self.out.delete()
# #         self.out.mkdir()


