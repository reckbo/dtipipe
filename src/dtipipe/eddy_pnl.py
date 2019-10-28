import sys
import logging
import filecmp
from os import getpid
from multiprocessing import Pool

import coloredlogs
import pytest
import numpy as np
from plumbum import local, cli

import dtipipe
from . import util
from . import bse


log = logging.getLogger(__name__)


def register(source_nii, target_nii, output, fsldir=None):
    log.info(f'Run FSL flirt affine registration: {source_nii} -> {target_nii}')
    with local.env(**util.fsl_env(fsldir)):
        local['flirt']('-interp', 'sinc',
                       '-sincwidth', '7',
                       '-sincwindow', 'blackman',
                       '-in',  source_nii,
                       '-ref', target_nii,
                       '-nosearch',
                       '-o', output,
                       '-omat', output.with_suffix('.txt', depth=2),
                       '-paddingsize', '1')


@pytest.mark.unit
def test_register(fsldir):
    with local.tempdir() as tmpdir:
        tmpdir = local.path('/tmp/tmp')
        dwi0 = dtipipe.TEST_DATA / 'dwi_split' / 'vol0000.nii.gz'
        dwi10 = dtipipe.TEST_DATA / 'dwi_split' / 'vol0010.nii.gz'
        expected_output = (dtipipe.TEST_DATA / 'dwi_10_in_0.nii.gz')
        test_output = tmpdir / 'dwi_10_in_0.nii.gz'
        register(dwi10, dwi0, test_output, fsldir=fsldir)
        assert filecmp.cmp(expected_output, test_output)


def _multiprocessing_register(source_nii):
    output = source_nii.with_suffix('.inb0.nii.gz', depth=2)
    register(source_nii=source_nii,
             target_nii='b0.nii.gz',
             output=output)
    return output


def eddy_pnl(dwi, output, nproc=20, fsldir=None, debug=False):
    """
    Eddy current correction.
    """

    dwi_file = local.path(dwi)
    bvec_file = dwi_file.with_suffix('.bvec', depth=2)
    bval_file = dwi_file.with_suffix('.bval', depth=2)
    output = local.path(output)
    output_bvec = output.with_suffix('.bvec', depth=2)
    output_bval = output.with_suffix('.bval', depth=2)
    output_transforms_tar = output[:-7] + '-xfms.tar.gz'
    output_debug = output.parent / f"eddy-debug-{getpid()}"

    with local.tempdir() as tmpdir, local.cwd(tmpdir), local.env(**util.fsl_env(fsldir)):

        fslsplit = local['fslsplit']
        fslmerge = local['fslmerge']

        log.info('Dice the DWI')
        fslsplit(dwi_file)
        vols = sorted(tmpdir // ('vol*.nii.gz'))
        log.debug(f'Split volumes: {vols}')

        log.info('Extract the B0')
        bse.bse(dwi_file, 'b0.nii.gz')

        pool = Pool(int(nproc))
        res = pool.map_async(_multiprocessing_register, vols)
        registered_vols = res.get()
        pool.close()
        pool.join()

        fslmerge('-t', 'EddyCorrect-DWI.nii.gz', registered_vols)
        transforms = sorted(tmpdir.glob('vol*.txt'))

        log.info('Extract the rotations and realign the gradients')
        bvecs = util.read_bvecs(bvec_file)
        bvecs_new = bvecs.copy()
        for i, t in enumerate(transforms):
            log.info('Apply ' + t)
            tra = np.loadtxt(t)
            # remove the translation
            aff = np.matrix(tra[0:3, 0:3])  # FIXME Use ndarray to suppress warning
            # compute the finite strain of aff to get the rotation
            rot = aff*aff.T
            # compute the square root of rot
            [el, ev] = np.linalg.eig(rot)
            eL = np.identity(3)*np.sqrt(el)
            sq = ev*eL*ev.I
            # finally the rotation is defined as
            rot = sq.I*aff
            bvecs_new[i] = np.dot(rot, bvecs[i]).tolist()[0]

        log.info(f'Copy EddyCorrect-DWI.nii.gz to {output}')
        local.path('EddyCorrect-DWI.nii.gz').copy(output)

        log.info(f'Make {output_bvec}')
        util.write_bvecs(bvecs_new, output_bvec)

        log.info(f'Make {output_bval}')
        bval_file.copy(output_bval)

        log.info(f'Make {output_transforms_tar}')
        local['tar']('cvzf', output_transforms_tar, transforms)

        if debug:
            tmpdir.copy(output_debug)


def test_eddy_pnl(fsldir):
    with local.tempdir() as tmpdir:
        tmpdir = local.path('/tmp/tmp')
        input_dwi = dtipipe.TEST_DATA / 'dwi.nii.gz'
        test_output = tmpdir / f'dwi_eddy.nii.gz'
        expected_output = dtipipe.TEST_DATA / f'dwi_eddy.nii.gz'
        eddy_pnl(input_dwi, test_output, fsldir=fsldir)
        assert filecmp.cmp(test_output, expected_output)
        for suffix in ['.bval', '.bvec']:
            assert filecmp.cmp(test_output.with_suffix(suffix, depth=2),
                               expected_output.with_suffix(suffix, depth=2))


class Cli(cli.Application):

    __doc__ = eddy_pnl.__doc__

    debug = cli.Flag('-d', help='Debug, saves registrations to eddy-debug-<pid>')
    dwi = cli.SwitchAttr('-i', cli.ExistingFile, help='DWI in nifti', mandatory= True)
    output = cli.SwitchAttr('-o', help='Prefix for eddy corrected DWI', mandatory= True)
    overwrite = cli.Flag('--force', default=False, help='Force overwrite')
    nproc = cli.SwitchAttr(
        ['-n', '--nproc'],
        help='''number of threads to use, if other processes in your computer
        becomes sluggish/you run into memory error, reduce --nproc''',
        default=20)
    fsldir = cli.SwitchAttr(['--fsldir'], default=None, help='root path of FSL', mandatory=False)

    def main(self):
        coloredlogs.install()
        self.output = local.path(self.output)
        if self.output.exists():
            if self.overwrite:
                self.output.delete()
            else:
                log.error(f"{self.output} exists, use '--force' to overwrite it")
                sys.exit(1)
        eddy_pnl(dwi=self.dwi, output=self.output, nproc=self.nproc, fsldir=self.fsldir)
