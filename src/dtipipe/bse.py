import logging
import filecmp

import pytest
from plumbum import local, cli
import numpy as np
import nibabel as nib
import coloredlogs

from . import util
from . import TEST_DATA


log = logging.getLogger(__name__)

DEFAULT_B0_THRESHOLD = 45.0


def bse(dwi, output=None, dwi_mask=None, b0_threshold=DEFAULT_B0_THRESHOLD, extract_type=None,
        fsldir=None):
    """
    Extracts the baseline (B0) from a nifti DWI.

    Assumes the diffusion volumes are indexed by the last axis. Chooses the
    first B0 as the baseline image by default, with option to specify one.
    """

    if not dwi.endswith('.nii.gz'):
        raise Exception(f'Expected .nii.gz file, got: {dwi}')

    if not output:
        output = dwi[:-9] + '_bse.nii.gz'

    bval_file = local.path(dwi.with_suffix('.bval', depth=2))
    bvals = [float(i) for i in bval_file.read().strip().split()]
    b0_idx = np.flatnonzero(np.array(bvals) < b0_threshold)

    log.debug(f'Found B0\'s at indices: {b0_idx}')

    if len(b0_idx) == 0:
        raise Exception(f'No B0 image found. Check {bval_file}')

    with util.fsl_env(fsldir):

        fslroi = local['fslroi']

        if extract_type == 'minimum':
            log.info('Extract minimum B0')
            fslroi(dwi, output, np.argsort(bvals)[0], 1)

        elif extract_type == 'average':
            log.info('Extract average B0')
            img = nib.load(str(dwi))
            hdr = img.header
            avg_bse = np.mean(img.get_data()[:, :, :, b0_idx], axis=3)
            util.save_nifti(output, avg_bse, img.affine, hdr)

        elif extract_type == 'all':
            log.info('Extract all B0\'s')
            fslroi(dwi, output, b0_idx, len(b0_idx))  # FIXME: valid for contiguous b0's only

        else:  # default is 'first'
            log.info('Extract first B0')
            fslroi(dwi, output, b0_idx, 1)

        if dwi_mask:
            log.info(f'Mask {output} with {dwi_mask}')
            local['fslmaths'](output, '-mul', dwi_mask, output)

    log.info(f'Made {output}')


@pytest.mark.parametrize("extract_type", ['minimum', 'average', 'all', 'first'])
@pytest.mark.parametrize("dwi_mask", [None, TEST_DATA / 'dwi_mask.nii.gz'])
def test_bse(extract_type, dwi_mask, fsldir):
    mask_suffix = '_masked' if dwi_mask else ''
    with util.fsl_env(fsldir), local.tempdir() as tmpdir:
        expected_output = TEST_DATA / f'dwi_b0_{extract_type}{mask_suffix}.nii.gz'
        output = tmpdir / f'dwi_b0_{extract_type}{mask_suffix}.nii.gz'
        bse(dwi=TEST_DATA / 'dwi.nii.gz',
            output=output,
            dwi_mask=dwi_mask,
            extract_type=extract_type, fsldir=fsldir)
        if extract_type == 'average':
            assert util.compare_niftis(output, expected_output)
        else:
            assert filecmp.cmp(output, expected_output)


class Cli(cli.Application):

    __doc__ = bse.__doc__

    ALLOW_ABBREV = True

    dwi = cli.SwitchAttr(
        ['-i', '--input'],
        argtype=cli.ExistingFile,
        mandatory=True,
        help='DWI in nifti format')

    output = cli.SwitchAttr(
        ['-o', '--output'],
        argtype=cli.NonexistentPath,
        help='Extracted baseline image')

    b0_threshold = cli.SwitchAttr(
        ['-t', '--threshold'],
        argtype=float,
        default=DEFAULT_B0_THRESHOLD,
        help='threshold for b0')

    extract_type = cli.SwitchAttr(
        ['-e', '--extract_type'],
        argtype=cli.Set("all", "average", "minimum", "first", case_sensitive=False),
        help=('Extraction type: all B0\'s ("all"), average of B0\'s ("average"), '
              'minimum B0 ("minimum") or first B0 ("first")'),
        default="first",
        mandatory=False)

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
        coloredlogs.install(self.log_level)
        bse(dwi=self.dwi,
            output=self.output,
            b0_threshold=self.b0_threshold,
            extract_type=self.extract_type,
            fsldir=self.fsldir)
