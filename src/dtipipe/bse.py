import logging
import filecmp

import pytest
from plumbum import local, cli
import numpy as np
import nibabel as nib
import coloredlogs

from . import util
import dtipipe


log = logging.getLogger(__name__)


def bse(dwi, output=None, b0_threshold=45, extract_type=None, fsldir=None):
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
    idx = np.flatnonzero(np.array(bvals) < b0_threshold)

    log.debug(f'Found B0\'s at indices: {idx}')

    if len(idx) == 0:
        raise Exception(f'No B0 image found. Check {bval_file}')

    with local.env(**util.fsl_env(fsldir)):

        fslroi = local['fslroi']

        if extract_type == 'minimum':
            log.info('Extract minimum B0')
            fslroi(dwi, output, np.argsort(bvals)[0], 1)

        elif extract_type == 'average':
            log.info('Extract average B0')
            img = nib.load(str(dwi))
            hdr = img.header
            avg_bse = np.mean(img.get_data()[:, :, :, idx], axis=3)
            util.save_nifti(output, avg_bse, img.affine, hdr)

        elif extract_type == 'all':
            log.info('Extract all B0\'s')
            fslroi(dwi, output, idx, len(idx))  # FIXME: valid for contiguous b0's only

        else:  # default is 'first'
            log.info('Extract first B0')
            fslroi(dwi, output, idx, 1)

    log.info(f'Made {output}')


@pytest.mark.parametrize("extract_type", ['minimum', 'average', 'all', 'first'])
def test_bse(extract_type, fsldir):
    with local.env(util.fsl_env(fsldir)):
        with local.tempdir() as tmpdir:
            tmpdir = local.path('/tmp/tmp')
            expected_output = dtipipe.TEST_DATA / f'dwi_b0_{extract_type}.nii.gz'
            test_output = tmpdir / f'dwi_b0_{extract_type}.nii.gz'
            bse(dtipipe.TEST_DATA / 'dwi.nii.gz', test_output, extract_type=extract_type,
                fsldir=fsldir)
            if extract_type == 'average':
                assert util.compare_niftis(test_output, expected_output)
            else:
                assert filecmp.cmp(test_output, expected_output)


class Cli(cli.Application):

    __doc__ = bse.__doc__

    dwi = cli.SwitchAttr(
        ['-i', '--input'],
        cli.ExistingFile,
        help='DWI in nifti format',
        mandatory=True)

    bval_file = cli.SwitchAttr(
        '--bvals',
        cli.ExistingFile,
        help='bval file, default: dwiPrefix.bval')

    output = cli.SwitchAttr(
        ['-o', '--output'],
        help='extracted baseline image (default: inPrefix_bse.nii.gz)',
        mandatory=False)

    b0_threshold = cli.SwitchAttr(
        ['-t', '--threshold'],
        help='threshold for b0',
        mandatory=False,
        default=45.0)

    extract_type = cli.SwitchAttr(
        ['-e', '--extract_type'],
        help=('extract all B0\'s ("all"), average of B0\'s ("average"), minimum B0 ("minimum"), '
              'or first B0 ("first")'),
        default="first",
        mandatory=False)

    fsldir = cli.SwitchAttr(
        ['--fsldir'],
        help='root path of FSL',
        mandatory=False)

    def main(self):
        coloredlogs.install()
        bse(dwi=self.dwi,
            output=self.output,
            b0_threshold=self.b0_threshold,
            extract_type=self.extract_type,
            fsldir=self.fsldir)
