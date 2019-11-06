import os
import sys
import warnings
import logging
import filecmp

import coloredlogs
import pytest
from plumbum import local, cli
import nibabel as nib
import numpy as np

from . import util
from . import TEST_DATA


log = logging.getLogger(__name__)

PRECISION = 17


np.set_printoptions(precision=PRECISION, suppress=True, floatmode='maxprec')


def matrix_string(A):
    A = str(A.tolist())
    A = A.replace(', ', ',')
    A = A.replace('],[', ') (')
    return '('+A[2:-2]+')'


def find_mf(F):
    FFT = F @ F.T
    lam, V = np.linalg.eig(FFT)
    FFTsqrt = V @ np.diag(np.sqrt(lam)) @ V.T
    R = FFTsqrt @ F

    # get rid of scaling, normalize each column
    R /= np.linalg.norm(R, axis=0)

    return R.T


def nifti2nhdr(nifti, bval, bvec, nhdr):
    """
    Convert a nifti to nrrd by creating an nhdr header.
    """

    print('Converting ', nifti)

    if nifti.endswith('.nii.gz'):
        encoding = 'gzip'
    elif nifti.endswith('.nii'):
        encoding = 'raw'
    else:
        raise ValueError('Invalid nifti file')

    img = nib.load(str(nifti))
    hdr = img.header

    if not nhdr:
        nhdr = os.path.abspath(nifti).split('.')[0] + '.nhdr'
    elif not nhdr.endswith('nhdr'):
        raise AttributeError('Output file must be nhdr')
    else:
        nhdr = os.path.abspath(nhdr)

    dim = hdr['dim'][0]
    # if bval/bvec provided but nifti is 3D, raise warning
    if dim == 3 and (bval or bvec):
        warnings.warn('nifti image is 3D, ignoring bval/bvec files')

    dtype = hdr.get_data_dtype()
    numpy_to_nrrd_dtype = {
        'int8': 'int8',
        'int16': 'short',
        'int32': 'int',
        'int64': 'longlong',
        'uint8': 'uchar',
        'uint16': 'ushort',
        'uint32': 'uint',
        'uint64': 'ulonglong',
        'float32': 'float',
        'float64': 'double'
    }

    f = open(nhdr, 'w')
    console = sys.stdout
    sys.stdout = f

    print(f'NRRD0005\n# NIFTI-->NHDR transform by Tashrif Billah\n\
# See https://github.com/pnlbwh/conversion for more info\n\
# Complete NRRD file format specification at:\n\
# http://teem.sourceforge.net/nrrd/format.html\n\
type: {numpy_to_nrrd_dtype[dtype.name]}\ndimension: {dim}\nspace: right-anterior-superior')

    sizes = hdr['dim'][1:dim + 1]
    print('sizes: {}'.format((' ').join(str(x) for x in sizes)))

    spc_dir = hdr.get_best_affine()[0:3, 0:3]

    # most important key
    print('byteskip: -1')

    endian = 'little' if dtype.byteorder == '<' else 'big'
    print(f'endian: {endian}')
    print(f'encoding: {encoding}')
    print('space units: "mm" "mm" "mm"')

    spc_orig = hdr.get_qform()[0:3, 3]
    print('space origin: ({})'.format((',').join(str(x) for x in spc_orig)))
    print(f'data file: {os.path.basename(nifti)}')

    # define oldmin and oldmax when scl_slope and scl_inter are present
    scl_slope = img.dataobj.slope
    scl_inter = img.dataobj.inter
    if scl_slope != 1.0 or scl_inter != 0:
        info = np.iinfo(dtype)
        oldmin = info.min*scl_slope+scl_inter
        oldmax = info.max*scl_slope+scl_inter
        print(f'old min: {oldmin}')
        print(f'old max: {oldmax}')

    # print description
    if img.header['descrip']:
        print('# {}'.format(np.char.decode(img.header['descrip'])))

    if dim == 4:
        print(f'space directions: {matrix_string(spc_dir.T)} none')
        print('centerings: cell cell cell ???')
        print('kinds: space space space list')

        if bval and bvec:

            mf = find_mf(spc_dir)
            print(f'measurement frame: {matrix_string(mf)}')

            bvecs = util.read_bvecs(bvec, normalize=True)
            bvals = util.read_bvals(bval)

            print('modality:=DWMRI')

            b_max = max(bvals)
            print(f'DWMRI_b-value:={b_max}')
            for ind in range(len(bvals)):
                scaled_bvec = util.bvec_scaling(bvals[ind], bvecs[ind], b_max)
                print(f'DWMRI_gradient_{ind:04}:={scaled_bvec}')

        else:
            warnings.warn('nifti image is 4D, but bval/bvec files are not provided, '
                          'assuming not a DWMRI')

    else:
        print(f'space directions: {matrix_string(spc_dir.T)}')
        print('centerings: cell cell cell')
        print('kinds: space space space')

    f.close()
    sys.stdout = console


@pytest.mark.parametrize("input_basename_nii", ["dwi_eddy.nii.gz", "dwi_mask.nii.gz"])
def test_nifti2nhdr(input_basename_nii):
    nhdr_filename = input_basename_nii[:-7] + '.nhdr'
    expected_output = TEST_DATA / 'nifti2nhdr' / nhdr_filename
    with local.tempdir() as tmpdir:
        input_nii = TEST_DATA / input_basename_nii
        output = tmpdir / nhdr_filename
        bvec = input_nii.with_suffix('.bvec', depth=2)
        bval = input_nii.with_suffix('.bval', depth=2)
        nifti2nhdr(nifti=input_nii, bval=bval, bvec=bvec, nhdr=output)
        assert filecmp.cmp(output, expected_output)


class Cli(cli.Application):

    input_nifti = cli.SwitchAttr(
        ['-i', '--input'],
        argtype=cli.ExistingFile,
        mandatory=True,
        help='Input NIFTI')

    output_nhdr = cli.SwitchAttr(
        ['-o', '--output'],
        argtype=cli.NonexistentPath,
        mandatory=True,
        help='Output nhdr file')

    log_level = cli.SwitchAttr(
        ['--log-level'],
        argtype=cli.Set("CRITICAL", "ERROR", "WARNING",
                        "INFO", "DEBUG", "NOTSET", case_sensitive=False),
        default='INFO',
        help='Python log level')

    def main(self):
        coloredlogs.install(level=self.log_level)
        bvec = self.input_nifti.with_suffix('.bvec', depth=2)
        bval = self.input_nifti.with_suffix('.bval', depth=2)
        nifti2nhdr(nifti=self.input_nifti,
                   bval=bval,
                   bvec=bvec,
                   nhdr=self.output_nhdr)
