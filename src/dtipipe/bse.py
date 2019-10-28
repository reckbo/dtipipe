import logging

import pytest
from plumbum import local
import numpy as np
import nibabel as nib

from . import util
from dtipipe import TEST_DATA


log = logging.getLogger(__name__)


def bse(dwi, output=None, b0_threshold=45, extract_type=None, fsldir=None):

    if not dwi.endswith('.nii.gz'):
        raise Exception(f'Expected .nii.gz file, got: {dwi}')

    if not output:
        output = dwi[:-9] + '_b0.nii.gz'

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


@pytest.mark.parametrize("extract_type", ['minimum', 'average', 'all', 'first'])
def test_bse(extract_type, fsldir):
    with local.env(util.fsl_env(fsldir)):
        with local.tempdir() as tmpdir:
            tmpdir = local.path('/tmp/tmp')
            test_output = tmpdir / f'dwi_b0_{extract_type}.nii.gz'
            bse(TEST_DATA / 'dwi.nii.gz', test_output, extract_type=extract_type, fsldir=fsldir)
