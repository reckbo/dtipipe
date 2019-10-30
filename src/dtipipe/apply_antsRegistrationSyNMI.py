import logging
from timeit import default_timer as timer

import pytest
import coloredlogs
from plumbum import local, cli

from . import util
from . import TEST_DATA


log = logging.getLogger(__name__)
REPO_DIR = local.path(__file__).parent.parent.parent
NUM_PROC_ANTS = 10


def apply_antsRegistrationSyNMI(moving_image, fixed_image, output, moving_image_src=None,
                                num_proc=NUM_PROC_ANTS, antspath=None,
                                interpolation='NearestNeighbor'):
    """
    Runs antsRegistrationSyNMI.sh script to compute a transformation and then applies it
    to the target volume.
    """

    moving_image_src = moving_image if not moving_image_src else moving_image_src
    output = local.path(output)

    with util.ants_env(antspath), local.tempdir() as tmpdir:
        output_prefix = tmpdir / 'output'
        affine = output_prefix + '0GenericAffine.mat'
        warp = output_prefix + '1Warp.nii.gz'
        log.info(f'Compute warp from "{moving_image}" to "{fixed_image}"')
        start = timer()
        r = local[REPO_DIR / 'scripts' / 'antsRegistrationSyNMI.sh'].run(['-m', moving_image,
                                                                          '-f', fixed_image,
                                                                          '-o', output_prefix,
                                                                          '-n', num_proc])
        end = timer()
        log.info(f'Done (took {end - start} seconds)')
        log.debug(f'antsRegistrationSyNMI.sh: {r}')
        log.debug(f'Output files in {tmpdir}: {tmpdir // "*"}')
        log.info(f'Apply warp to "{moving_image_src}" to put in "{fixed_image}" space')
        r = local['antsApplyTransforms'].run(['-d', '3',
                                              '-i', moving_image_src,
                                              '-t', warp, affine,
                                              '-r', fixed_image,
                                              '-o', output,
                                              '--interpolation', interpolation])
        log.debug(f'antsApplyTransforms: {r}')

    if not output.exists():
        raise Exception(f'Failed to produce output: {output}')

    log.info(f'Made "{output}"')


@pytest.mark.slow
def test_apply_antsRegistrationSyNMI(antspath, num_proc_ants):
    brain = TEST_DATA / 'fs2dwi' / 'brain.nii.gz'
    wmparc = TEST_DATA / 'fs2dwi' / 'wmparc.nii.gz'
    masked_b0 = TEST_DATA / 'dwi_b0_first_masked.nii.gz'
    expected_output = TEST_DATA / 'fs2dwi' / 'wmparc_in_dwi.nii.gz'
    with local.tempdir() as tmpdir:
        output = tmpdir / 'wmparc_in_dwi.nii.gz'
        apply_antsRegistrationSyNMI(moving_image=brain,
                                    fixed_image=masked_b0,
                                    moving_image_src=wmparc,
                                    output=output,
                                    num_proc=num_proc_ants,
                                    antspath=antspath)
        assert expected_output.exists()
        # Note: antsRegistration output is not deterministic.  Supposedly
        # you can make it reproducible by setting ANTS_RANDOM_SEED=1 and
        # ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=1 but my tests still produced
        # variable output.


class Cli(cli.Application):

    __doc__ = apply_antsRegistrationSyNMI.__doc__

    ALLOW_ABBREV = True

    moving_image = cli.SwitchAttr(
        ['-m', '--moving'],
        cli.ExistingFile,
        mandatory=True,
        help='Moving image')

    fixed_image = cli.SwitchAttr(
        ['-f', '--fixed'],
        cli.ExistingFile,
        mandatory=True,
        help='Fixed image')

    output = cli.SwitchAttr(
        ['-o', '--output'],
        mandatory=True,
        help='Output image')

    moving_image_src = cli.SwitchAttr(
        ['-a', '--apply'],
        cli.ExistingFile,
        help='Image to warp (will use the moving image if omitted)')

    antspath = cli.SwitchAttr(
        ['--antspath'],
        argtype=cli.ExistingDirectory,
        help='Path to root ANTs bin/ directory')

    num_proc = cli.SwitchAttr(
        ['-n', '--num-proc'],
        argtype=int,
        default=NUM_PROC_ANTS,
        help='Number of threads')

    log_level = cli.SwitchAttr(
        ['--log-level'],
        argtype=cli.Set("CRITICAL", "ERROR", "WARNING",
                        "INFO", "DEBUG", "NOTSET", case_sensitive=False),
        default='INFO',
        help='Python log level')

    def main(self):
        coloredlogs.install(level=self.log_level)
        apply_antsRegistrationSyNMI(
            moving_image=self.moving_image,
            fixed_image=self.fixed_image,
            output=self.output,
            moving_image_src=self.moving_image_src,
            antspath=self.antspath,
            num_proc=self.num_proc)
