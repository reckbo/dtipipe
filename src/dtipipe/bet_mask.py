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

    with local.env(**util.fsl_env(fsldir)), local.tempdir() as tmpdir:
        bet = local['bet']

        if len(shape) == 3:
            log.info(f'Make BSL bet mask for 3D input image: {input_file}')
            bet(input_file, 'mask', '-m', '-n', '-f', bet_threshold)
            output_file.parent.mkdir()
            (tmpdir / 'mask_mask.nii.gz').copy(output_file)

        elif len(shape) == 4:
            log.info(f'Make BSL bet mask for input DWI: {input_file}')
            tmp_bse = tmpdir / 'bse.nii.gz'
            bse.bse(input_file, tmp_bse, extract_type='first')
            bet(tmp_bse, tmpdir / 'mask', '-m', '-n', '-f', bet_threshold)
            local.path(output_file).parent.mkdir()
            (tmpdir / 'mask_mask.nii.gz').copy(output_file)

        else:
            raise Exception(f'Expected a 3D or 4D input image, got: {shape}')


def test_bet_mask(fsldir):
    with local.tempdir() as tmpdir:
        tmpdir = local.path('/tmp/tmp')  # FIXME
        input_file = TEST_DATA / 'dwi.nii.gz'
        output_file = tmpdir / f'dwi_mask.nii.gz'
        expected_output_file = TEST_DATA / f'dwi_mask.nii.gz'
        bet_mask(input_file, output_file, fsldir=fsldir)
        assert filecmp.cmp(output_file, expected_output_file)


class Cli(cli.Application):

    input_file = cli.SwitchAttr(
        ['-i', '--input'], cli.ExistingFile, help='input 3D/4D nifti image', mandatory=True)

    output_file = cli.SwitchAttr(['-o', '--output'], help='path of output mask', mandatory=True)

    bet_threshold = cli.SwitchAttr(
        '-f', help='threshold for fsl bet mask', mandatory=False, default=DEFAULT_BET_THRESHOLD)

    def main(self):
        coloredlogs.install()
        bet_mask(self.input_file, self.output_file, bet_threshold=self.bet_threshold)
