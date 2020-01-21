import logging
import filecmp

from plumbum import local, cli
import nibabel as nib
import coloredlogs

from . import util
from . import bse
from . import TEST_DATA


log = logging.getLogger(__name__)

DEFAULT_BET_THRESHOLD = 0.1


def bet_mask(input_file, output_file, bet_threshold=DEFAULT_BET_THRESHOLD, fsldir=None):
    """
    Create a mask using FSL's bet.

    Can be used on 3D volumes and 4D DWI's.
    """

    shape = nib.load(str(input_file)).shape
    input_file = local.path(input_file)
    output_file = local.path(output_file)

    with util.fsl_env(fsldir), local.tempdir() as tmpdir:
        bet = local['bet']

        if len(shape) == 3:
            log.info(f'Make BSL bet mask for 3D input image: {input_file}')
            bet(input_file, tmpdir / 'img', '-m', '-n', '-f', bet_threshold)
            log.debug(f'Output files: {tmpdir // "*"}')
            output_file.parent.mkdir()
            (tmpdir / 'img_mask.nii.gz').copy(output_file)

        elif len(shape) == 4:
            log.info(f'Make BSL bet mask for input DWI: {input_file}')
            bse.bse(input_file, tmpdir / 'bse.nii.gz', extract_type='first')
            bet(tmpdir / 'bse.nii.gz', tmpdir / 'bse', '-m', '-n', '-f', bet_threshold)
            log.debug(f'Output files: {tmpdir // "*"}')
            local.path(output_file).parent.mkdir()
            (tmpdir / 'bse_mask.nii.gz').copy(output_file)

        else:
            raise Exception(f'Expected a 3D or 4D input image, got: {shape}')

        log.info(f'Made {output_file}')


# TODO add test for 3D
def test_bet_mask(fsldir):
    with local.tempdir() as tmpdir:
        input_file = TEST_DATA / 'dwi.nii.gz'
        output_file = tmpdir / f'dwi_mask.nii.gz'
        expected_output_file = TEST_DATA / f'dwi_mask.nii.gz'
        bet_mask(input_file, output_file, fsldir=fsldir)
        assert filecmp.cmp(output_file, expected_output_file)


class Cli(cli.Application):

    input_file = cli.SwitchAttr(
        ['-i', '--input'],
        argtype=cli.ExistingFile,
        mandatory=True,
        help='input 3D/4D nifti image')

    output_file = cli.SwitchAttr(
        ['-o', '--output'],
        mandatory=True,
        help='path of output mask')

    bet_threshold = cli.SwitchAttr(
        '-f',
        argtype=float,
        default=DEFAULT_BET_THRESHOLD,
        help='threshold for fsl bet mask')

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
        bet_mask(self.input_file,
                 self.output_file,
                 bet_threshold=self.bet_threshold,
                 fsldir=self.fsldir)
